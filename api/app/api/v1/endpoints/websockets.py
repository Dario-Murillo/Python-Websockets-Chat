import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError

from app.api.deps import get_current_user_ws, ws_session
from app.crud import crud_room
from app.schemas.websocket import JoinFrame, client_frame
from app.services.connection_manager import manager
from app.utils.time import utcnow

# Application close code for a slug no room answers to. 1008 already means "the
# token was rejected", and the frontend has to tell the two apart.
WS_ROOM_NOT_FOUND = 4004

# The token rides in `Sec-WebSocket-Protocol` as `bearer, <jwt>`. Every accept
# has to echo this back, or the browser fails the connection on a subprotocol
# mismatch -- including the accept that exists only to report WS_ROOM_NOT_FOUND.
WS_BEARER_SUBPROTOCOL = "bearer"


def bearer_token(websocket: WebSocket) -> str | None:
    """The access token offered on the handshake, or None if it is not there.

    A browser cannot set request headers on a WebSocket handshake, but it can
    offer subprotocols, and those travel as a header. Putting the token there
    instead of in the query string keeps it out of uvicorn's access log and out
    of every proxy trail in front of it.
    """
    # The header is one comma-separated list, and not every ASGI server strips
    # the space after the comma when it splits it -- a token arriving as
    # " eyJhbG..." fails to verify for no visible reason.
    subprotocols = [
        offered.strip() for offered in websocket.scope.get("subprotocols", [])
    ]

    if len(subprotocols) != 2 or subprotocols[0] != WS_BEARER_SUBPROTOCOL:
        return None

    return subprotocols[1]


router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{room_slug}")
async def websocket_endpoint(websocket: WebSocket, room_slug: str):
    token = bearer_token(websocket)

    if token is None:
        # Refused before any database work: an unauthenticated peer should not
        # cost a pooled connection either.
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # The handshake is the only part of a socket's life that reads the database.
    # Declaring `DbSession` here instead would hold a pooled connection for as
    # long as the user stays connected, doing nothing.
    async with ws_session() as db:
        user = await get_current_user_ws(token, db)

        if user is None:
            # Turned away before the handshake completes, so an unauthenticated
            # peer never holds an open socket. uvicorn answers this with HTTP
            # 403 and the browser reports a plain connection failure.
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Rooms are addressed by slug and have to exist first. Without this
        # check any string in the path spins up an ad-hoc room inside the
        # connection registry, so a typo silently becomes a private channel.
        room = await crud_room.get_by_slug(db, room_slug)

        # Identity always comes from the verified token, never from the payload,
        # so a client cannot broadcast under someone else's name. Read while the
        # session is still open: afterwards the instance is detached.
        username = user.username

    if room is None:
        # Accepted first on purpose. A close code sent before the handshake
        # completes never reaches a browser -- uvicorn turns it into HTTP 403
        # and the client only ever sees 1006, indistinguishable from the server
        # being down. The token is already verified here, so opening the socket
        # just to name the reason gives nothing away.
        await websocket.accept(subprotocol=WS_BEARER_SUBPROTOCOL)
        await websocket.close(code=WS_ROOM_NOT_FOUND)
        return

    await manager.connect(websocket, room_slug, subprotocol=WS_BEARER_SUBPROTOCOL)

    try:
        while True:
            raw_data = await websocket.receive_text()

            try:
                frame = client_frame.validate_json(raw_data)
            except ValidationError:
                # Everything the protocol does not define is dropped while the
                # connection stays open: malformed JSON, valid JSON that is not
                # an object, an unknown `type`, a message that is empty or over
                # MAX_MESSAGE_LENGTH. This used to escape the handler entirely,
                # skipping the cleanup below and leaving a registered socket
                # nobody was reading.
                continue

            if isinstance(frame, JoinFrame):
                await manager.broadcast(
                    json.dumps(
                        {
                            "type": "join",
                            "username": username,
                            "room_slug": room_slug,
                            "timestamp": utcnow().isoformat(),
                        }
                    ),
                    room_slug,
                )
                continue

            await manager.broadcast(
                json.dumps(
                    {
                        "type": "message",
                        "username": username,
                        "message": frame.message,
                        "room_slug": room_slug,
                        "timestamp": utcnow().isoformat(),
                    }
                ),
                room_slug,
            )

    except WebSocketDisconnect:
        pass
    finally:
        # In a `finally` rather than in the handler above: any way out of that
        # loop has to unregister the socket, or the room keeps broadcasting into
        # a connection that is no longer there.
        manager.disconnect(websocket, room_slug)
        await manager.broadcast(
            json.dumps(
                {
                    "event": "disconnect",
                    "username": username,
                    "room_slug": room_slug,
                    "timestamp": utcnow().isoformat(),
                }
            ),
            room_slug,
        )
