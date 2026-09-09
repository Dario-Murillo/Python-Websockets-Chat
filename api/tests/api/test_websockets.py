"""Covers the WebSocket route: who gets in, what the server says they are, and
which sockets a broadcast reaches."""
import asyncio
import json
from contextlib import asynccontextmanager

import pytest
from httpx_ws import WebSocketDisconnect, aconnect_ws

from app.api.v1.endpoints.websockets import (
    WS_BEARER_SUBPROTOCOL,
    WS_ROOM_NOT_FOUND,
)
from app.core.database import engine
from app.schemas.websocket import MAX_MESSAGE_LENGTH

WS_POLICY_VIOLATION = 1008

# Every test here needs the rooms in place but none of them reads the fixture's
# value, so it is requested by name rather than taken as an unused argument.
pytestmark = pytest.mark.usefixtures("seeded_rooms")


@asynccontextmanager
async def open_socket(
    ws_client, slug: str, token: str | None = None, *, query: str = ""
):
    """Opens a room socket, client and all, inside the caller's own task.

    The token is offered as a subprotocol, the way the browser client does it,
    so it never reaches the URL.
    """
    subprotocols = [WS_BEARER_SUBPROTOCOL, token] if token is not None else None
    async with ws_client() as client:
        async with aconnect_ws(
            f"http://test/api/v1/ws/{slug}{query}", client, subprotocols=subprotocols
        ) as ws:
            yield ws


def _find(error: BaseException, kind: type) -> BaseException | None:
    if isinstance(error, kind):
        return error
    if isinstance(error, BaseExceptionGroup):
        for inner in error.exceptions:
            found = _find(inner, kind)
            if found is not None:
                return found
    return None


async def rejected_close_code(
    ws_client, slug: str, token: str | None = None, *, query: str = ""
) -> int:
    """The code the server turned the handshake away with.

    The failure travels out through the transport's anyio task group, so it can
    arrive wrapped in an ExceptionGroup rather than on its own.
    """
    try:
        async with open_socket(ws_client, slug, token, query=query):
            pass
    except BaseException as raised:
        disconnect = _find(raised, WebSocketDisconnect)
        if disconnect is None:
            raise
        return disconnect.code

    raise AssertionError("the socket was accepted, not rejected")


async def disconnect_code(ws) -> int:
    """Reads until the server closes, and reports the code it closed with."""
    try:
        await ws.receive_text(timeout=2)
    except WebSocketDisconnect as closed:
        return closed.code

    raise AssertionError("the server did not close the socket")


async def join(ws, username: str = "whoever") -> dict:
    """Sends the join frame and returns the broadcast it produces."""
    await ws.send_text(json.dumps({"type": "join", "username": username}))
    return json.loads(await ws.receive_text(timeout=2))


async def test_an_invalid_token_is_turned_away(ws_client):
    code = await rejected_close_code(ws_client, "general", "not-a-jwt")

    assert code == WS_POLICY_VIOLATION


async def test_a_missing_token_is_turned_away(ws_client):
    code = await rejected_close_code(ws_client, "general")

    assert code == WS_POLICY_VIOLATION


async def test_a_token_in_the_query_string_no_longer_authenticates(
    ws_client, make_token
):
    """The old mechanism, which leaked the token into every access log, must not
    quietly keep working alongside the new one."""
    token = await make_token("ghost_99")

    code = await rejected_close_code(ws_client, "general", query=f"?token={token}")

    assert code == WS_POLICY_VIOLATION


async def test_an_unknown_room_is_reported_with_its_own_close_code(
    ws_client, token
):
    """The client has to tell "no such room" from "the token was rejected", and
    the close code is the only channel it has for that."""
    async with open_socket(ws_client, "not-a-room", token) as ws:
        # Reaching this line means the handshake completed. That is deliberate:
        # a code sent before the socket is accepted never reaches a browser.
        code = await disconnect_code(ws)

    assert code == WS_ROOM_NOT_FOUND


async def test_the_broadcast_username_comes_from_the_token(
    ws_client, token
):
    """A client claiming to be someone else must still be announced as itself."""
    async with open_socket(ws_client, "general", token) as ws:
        frame = await join(ws, username="administrator")

    assert frame["type"] == "join"
    assert frame["username"] == "ghost_99"
    assert frame["room_slug"] == "general"


async def test_a_message_reaches_the_other_client_in_the_room(
    ws_client, make_token
):
    author = await make_token("ghost_99")
    listener = await make_token("kira")

    async with open_socket(ws_client, "general", author) as sender:
        await join(sender)

        async with open_socket(ws_client, "general", listener) as receiver:
            await join(receiver)

            await sender.send_text(json.dumps({"type": "message", "message": "hola"}))
            frame = json.loads(await receiver.receive_text(timeout=2))

    assert frame["type"] == "message"
    assert frame["username"] == "ghost_99"
    assert frame["message"] == "hola"


async def test_a_message_does_not_leak_into_another_room(
    ws_client, make_token
):
    author = await make_token("ghost_99")
    outsider = await make_token("kira")

    async with open_socket(ws_client, "general", author) as sender:
        await join(sender)

        async with open_socket(ws_client, "tech", outsider) as elsewhere:
            await join(elsewhere)

            await sender.send_text(json.dumps({"type": "message", "message": "hola"}))

            with pytest.raises(TimeoutError):
                await asyncio.wait_for(elsewhere.receive_text(), timeout=0.5)


async def test_an_idle_socket_holds_no_pooled_connection(
    ws_client, token
):
    """A handler that declared `DbSession` kept one pooled connection per open
    socket, so the pool ran out long before the process did."""
    async with open_socket(ws_client, "general", token) as ws:
        await join(ws)

        assert engine.pool.checkedout() == 0


async def test_a_malformed_frame_does_not_kill_the_connection(ws_client, make_token):
    """Non-JSON input used to raise straight out of the handler, skipping the
    cleanup and leaving a registered socket nobody was reading."""
    author = await make_token("ghost_99")
    listener = await make_token("kira")

    async with open_socket(ws_client, "general", author) as sender:
        await join(sender)

        async with open_socket(ws_client, "general", listener) as receiver:
            await join(receiver)

            await sender.send_text("this is not json at all")
            await sender.send_text(json.dumps("valid json, but not an object"))

            # The socket is still live and still routing.
            await sender.send_text(json.dumps({"type": "message", "message": "hola"}))
            frame = json.loads(await receiver.receive_text(timeout=2))

    assert frame["type"] == "message"
    assert frame["message"] == "hola"


async def test_leaving_the_room_is_announced_to_the_others(ws_client, make_token):
    """The cleanup lives in a `finally`, so every way out of the loop reaches
    it, not just a clean disconnect."""
    leaver = await make_token("ghost_99")
    stayer = await make_token("kira")

    async with open_socket(ws_client, "general", stayer) as receiver:
        await join(receiver)

        async with open_socket(ws_client, "general", leaver) as leaving:
            await join(leaving)

        # Drain the join the leaver produced, then read its departure.
        await receiver.receive_text(timeout=2)
        frame = json.loads(await receiver.receive_text(timeout=2))

    assert frame["event"] == "disconnect"
    assert frame["username"] == "ghost_99"


async def test_the_server_sends_no_plain_text_echo(ws_client, token):
    """The handler used to reply `You wrote: {...}` in plain text to the sender,
    which the client could do nothing with but silently drop."""
    async with open_socket(ws_client, "general", token) as ws:
        await join(ws)
        await ws.send_text(json.dumps({"type": "message", "message": "hola"}))

        # The very next frame is the broadcast, with nothing in front of it.
        frame = json.loads(await ws.receive_text(timeout=2))

    assert frame["type"] == "message"
    assert frame["message"] == "hola"


async def next_broadcast(ws) -> dict:
    """Sends a known-good message and returns the frame it produces.

    Anything the server had wrongly accepted before it would arrive first, so
    this is how a test asserts that a bad frame produced *nothing*.
    """
    await ws.send_text(json.dumps({"type": "message", "message": "canary"}))
    return json.loads(await ws.receive_text(timeout=2))


async def test_an_overlong_message_is_dropped(ws_client, token):
    async with open_socket(ws_client, "general", token) as ws:
        await join(ws)

        await ws.send_text(
            json.dumps({"type": "message", "message": "x" * (MAX_MESSAGE_LENGTH + 1)})
        )
        frame = await next_broadcast(ws)

    assert frame["message"] == "canary"


async def test_a_message_at_the_limit_is_accepted(ws_client, token):
    async with open_socket(ws_client, "general", token) as ws:
        await join(ws)

        await ws.send_text(
            json.dumps({"type": "message", "message": "x" * MAX_MESSAGE_LENGTH})
        )
        frame = json.loads(await ws.receive_text(timeout=2))

    assert len(frame["message"]) == MAX_MESSAGE_LENGTH


async def test_an_empty_or_blank_message_is_dropped(ws_client, token):
    async with open_socket(ws_client, "general", token) as ws:
        await join(ws)

        await ws.send_text(json.dumps({"type": "message", "message": ""}))
        await ws.send_text(json.dumps({"type": "message", "message": "   "}))
        frame = await next_broadcast(ws)

    assert frame["message"] == "canary"


async def test_a_message_that_is_not_a_string_is_dropped(ws_client, token):
    """`data.get("message")` used to hand a number or an object straight to
    every socket in the room."""
    async with open_socket(ws_client, "general", token) as ws:
        await join(ws)

        await ws.send_text(json.dumps({"type": "message", "message": 42}))
        await ws.send_text(json.dumps({"type": "message", "message": {"a": ["b"]}}))
        frame = await next_broadcast(ws)

    assert frame["message"] == "canary"


async def test_an_unknown_frame_type_is_dropped(ws_client, token):
    """Anything that was not `join` used to fall through to the message branch."""
    async with open_socket(ws_client, "general", token) as ws:
        await join(ws)

        await ws.send_text(json.dumps({"type": "promote", "role": "admin"}))
        frame = await next_broadcast(ws)

    assert frame["type"] == "message"
    assert frame["message"] == "canary"


async def test_surrounding_whitespace_is_stripped(ws_client, token):
    async with open_socket(ws_client, "general", token) as ws:
        await join(ws)

        await ws.send_text(json.dumps({"type": "message", "message": "  hola  "}))
        frame = json.loads(await ws.receive_text(timeout=2))

    assert frame["message"] == "hola"
