/**
 * Both bases already include the `/api/v1` prefix every route is mounted under,
 * including the WebSocket endpoint.
 */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

export const WS_BASE =
  process.env.NEXT_PUBLIC_WS_BASE ?? "ws://localhost:8000/api/v1";

/**
 * Must match MAX_MESSAGE_LENGTH in `api/app/schemas/websocket.py`. The server
 * drops anything longer, so capping the input is what keeps that from happening
 * silently: the user is stopped while typing rather than watching a message
 * appear on their own screen and reach nobody.
 */
export const MAX_MESSAGE_LENGTH = 500;
