# Amagi — Claude Context File

Real-time multi-room chat application. Python/FastAPI backend, Next.js + TypeScript + Tailwind frontend. 

## Project Structure

The backend follows a layered FastAPI layout rooted at `api/`. The frontend is a Next.js app in `web/`, served independently.

```
Amagi/
├── CLAUDE.md
├── README.md
├── LICENSE
├── .gitignore
├── api/                          # FastAPI project root
│   ├── .env                      # Local environment variables (never committed)
│   ├── .env.example
│   ├── pyproject.toml            # Dependencies and package metadata
│   ├── Dockerfile
│   ├── docker-compose.yml        # Postgres + API for local orchestration
│   ├── alembic.ini
│   ├── alembic/                  # Migration scripts
│   │   ├── env.py                # Async-compatible Alembic config
│   │   └── versions/
│   ├── app/                      # Main application package
│   │   ├── main.py               # FastAPI init, CORS, lifespan, router mount
│   │   ├── api/                  # API layer (requests/responses)
│   │   │   ├── deps.py           # get_db, get_current_user, get_current_user_ws
│   │   │   └── v1/
│   │   │       ├── api.py        # Combines all v1 routers
│   │   │       └── endpoints/
│   │   │           ├── users.py       # register, token, me
│   │   │           ├── rooms.py       # stubs, pending DB wiring
│   │   │           └── websockets.py  # WebSocket route handler
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic Settings from .env
│   │   │   ├── database.py       # Engine, AsyncSessionLocal, Base
│   │   │   └── security.py       # Password hashing, JWT create/verify
│   │   ├── crud/                 # Reusable DB operations
│   │   │   ├── crud_user.py
│   │   │   └── crud_room.py
│   │   ├── models/               # SQLAlchemy ORM models, one per table
│   │   │   ├── user.py
│   │   │   ├── room.py
│   │   │   ├── room_member.py
│   │   │   └── message.py
│   │   ├── schemas/              # Pydantic validation schemas
│   │   │   ├── user.py
│   │   │   ├── room.py
│   │   │   ├── message.py
│   │   │   └── token.py
│   │   ├── services/             # Business logic and stateful integrations
│   │   │   └── connection_manager.py  # In-memory WebSocket registry
│   │   └── utils/
│   │       └── time.py           # utcnow() — default for every created_at
│   └── tests/
│       ├── conftest.py           # Test DB + AsyncClient fixtures
│       ├── api/                  # Endpoint integration tests
│       └── services/             # Unit tests for business logic
└── web/
    ├── package.json              # pnpm is the package manager for this app
    ├── next.config.ts
    ├── tsconfig.json             # `@/*` resolves from the web/ root
    ├── .env.example
    ├── app/
    │   ├── layout.tsx            # Fonts (DM Mono, Bebas Neue) and metadata
    │   ├── globals.css           # Tailwind v4 import + @theme design tokens
    │   ├── page.tsx              # splash → auth → room list
    │   └── room/[slug]/page.tsx  # One room's chat, addressable by URL
    ├── components/
    │   ├── splash.tsx            # Painted until the stored session is read
    │   ├── auth-screen.tsx
    │   ├── rooms-screen.tsx
    │   ├── chat-screen.tsx
    │   └── wordmark.tsx
    ├── hooks/
    │   ├── use-auth.ts           # Session, login, register, logout
    │   ├── use-rooms.ts          # Room list: loading, error, retry
    │   └── use-chat-socket.ts    # Room socket lifecycle, messages, roster
    └── lib/
        ├── config.ts             # API_BASE / WS_BASE
        ├── rooms.ts              # fetchRooms() against GET /rooms
        ├── session-store.ts      # localStorage session as an external store
        ├── errors.ts             # Flattens FastAPI `detail` into one line
        └── types.ts
```

**Layering rule:** endpoints validate and delegate; they never build queries. Database access lives in `crud/`, stateful logic in `services/`, and anything an endpoint needs injected comes from `api/deps.py`.

## Running the Project

**Backend:**
```bash
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1        # PowerShell
pip install -e ".[dev]"
uvicorn app.main:app --reload
# runs on http://localhost:8000
# API docs at http://localhost:8000/docs
```

**Frontend** — pnpm, not npm:
```bash
cd web
pnpm install
pnpm dev                          # http://localhost:3000
pnpm lint                         # ESLint, including the React Compiler rules
pnpm build
```

**Tests:**
```bash
cd api
pytest
```

**Database migrations** — run from `api/`, since `alembic.ini` sets `prepend_sys_path = .` so the `app` package resolves:
```bash
cd api
alembic revision --autogenerate -m "description"
alembic upgrade head
```

**Docker:**
```bash
cd api
docker compose up --build     # brings up Postgres + the API on :8000
```

The API image runs `alembic upgrade head` before uvicorn, so the container is
never up against a schema-less database; a failed migration takes the container
down rather than leaving a broken API listening. This is safe as a startup step
only because the app is single-instance by design (`ConnectionManager` is
in-memory) — with replicas, two containers would race the same upgrade and it
would have to become a one-shot job instead.

## Environment Variables

File: `api/.env`

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/amagi
SECRET_KEY=your-secret-key-here
```

`SECRET_KEY` signs every JWT and has no fallback anywhere: `config.py` declares
it as a required field, and `docker-compose.yml` uses the `${SECRET_KEY:?...}`
form so the API container fails to start instead of booting with a placeholder
key. Compose interpolates it from `api/.env`, which is the same file the local
uvicorn run uses.

`app/core/config.py` loads these via Pydantic Settings. `DATABASE_URL` must use the `postgresql+asyncpg://` driver prefix for async SQLAlchemy to work. Settings are validated at import time, so a missing variable fails the process at startup rather than at first request.

Allowed CORS origins live in `settings.cors_origins` and default to port 3000 on `localhost`, `127.0.0.1`, and `[::1]`. The browser matches origins exactly, so the host used to open the frontend must be one of them.

## API Versioning

Every route is mounted under `settings.api_v1_prefix` (`/api/v1`), including the WebSocket endpoint. `API_BASE` and `WS_BASE` in `web/lib/config.ts` already include the prefix; override them with `NEXT_PUBLIC_API_BASE` / `NEXT_PUBLIC_WS_BASE` (see `web/.env.example`).

## Auth Flow

- Passwords hashed with **Argon2** via `pwdlib`
- Tokens are **JWT** signed with `SECRET_KEY`, containing `sub` (user ID) and `exp`
- REST endpoints use the `CurrentUser` annotated dependency from `app/api/deps.py`, which reads from the `Authorization: Bearer` header via `oauth2_scheme`
- WebSocket endpoints can't use the Authorization header, so the token is offered as a subprotocol — `new WebSocket(url, ["bearer", token])` — and read from `Sec-WebSocket-Protocol` by `bearer_token(websocket)`, then verified via `get_current_user_ws(token, db)`. It is deliberately *not* a query param: uvicorn writes the full URL into its access log, and so does every proxy in front of it.
- Token expiry is controlled by `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 30)
- **Revocation without a denylist.** Every token carries a `ver` claim and every user row a `token_version`; `_user_from_token` compares them, and `POST /users/logout` bumps the row. The user is already loaded there to be returned, so the check costs no extra query, and it survives a restart in a way an in-memory denylist would not. The trade-off is deliberate: it revokes *every* token for that account, so logging out on one device logs out all of them. A socket that was already open is unaffected — authentication happens at the handshake and is never re-checked.
- **`POST /users/token` is rate limited**, per client address and per username, by the in-memory `login_limiter` (`login_max_attempts` / `login_window_seconds`). The check runs before the password is verified, so a refused attempt costs no Argon2 work — which is the point as much as the brute-force ceiling is. `request.client` is the immediate peer, so behind a proxy every user collapses into one key until uvicorn runs with `--proxy-headers`.

## WebSocket Protocol

**Connection URL:** `ws://localhost:8000/api/v1/ws/{room_slug}`, with the token offered as a subprotocol:

```js
new WebSocket(`${WS_BASE}/ws/${roomSlug}`, ["bearer", token]);
```

**Every `accept()` has to echo the subprotocol back** (`accept(subprotocol="bearer")`) or the browser fails the connection on a mismatch — including the accept that exists only to report `4004`. Note also that the header is one comma-separated list and not every ASGI server strips the space after the comma, so `bearer_token()` strips each offered value before comparing.

**Client → Server messages (JSON):**
```json
{ "type": "join", "username": "ghost_99" }
{ "type": "message", "message": "hello" }
```

**Server → Client broadcasts (JSON):**
```json
{ "type": "join", "username": "ghost_99", "room_slug": "general", "timestamp": "..." }
{ "type": "message", "username": "ghost_99", "message": "hello", "room_slug": "general", "timestamp": "..." }
{ "event": "disconnect", "username": "ghost_99", "room_slug": "general", "timestamp": "..." }
```

Username in all server messages comes from the verified JWT, not from client payload — clients cannot spoof identity. The room is likewise taken from the path, never from the payload, so a client-supplied room field would be decoration: `room_slug` travels server → client only.

**`room_slug`, not `room_id`.** Everything outside the database addresses a room by its slug. `room_id` is reserved for the integer foreign keys in `messages` and `room_members` that point at `rooms.id`.

**Malformed input is ignored.** A frame that is not valid JSON, or that is valid JSON but not an object, is skipped and the connection stays open — it used to raise straight out of the handler, skipping cleanup and leaving a registered socket nobody was reading. The handler's cleanup lives in a `finally`, so every exit from the receive loop unregisters the socket; `ConnectionManager.disconnect` is idempotent because a broadcast drops dead sockets itself, and the owning handler then asks for a removal that already happened.

**Close codes.** A rejected token is refused before the handshake completes, so an unauthenticated peer never holds an open socket; uvicorn turns that into an HTTP 403 and the browser only sees a failed connection. An unknown room slug is different: the socket is accepted first and *then* closed with the application code `4004`, because a code sent before the handshake completes never reaches the browser. Any check that needs to report a reason to the client has to accept first.

**Testing sockets.** `tests/api/test_websockets.py` drives the route in-process with `httpx-ws`. Note that its ASGI transport surfaces a pre-accept close as a real close code, which a browser does not — so a test passing there is not proof the client can see the code. Verify anything close-code-shaped against a real uvicorn.

## Database Schema

```
users         → id, username (unique), hashed_password, created_at
rooms         → id, name (unique), created_at
room_members  → user_id (FK), room_id (FK) — composite PK
messages      → id, text, created_at, user_id (FK), room_id (FK)
```

## Key Architectural Decisions

**Async throughout** — `create_async_engine` + `asyncpg` driver. Never use `psycopg2` or sync SQLAlchemy here, it blocks the event loop.

**A WebSocket handshake does not use `get_db`** — a WebSocket handler that declares `DbSession` holds that pooled connection for as long as the socket stays open, so idle chatters exhaust the pool. `app/api/deps.py` exposes `ws_session()`, an `async with` scoped to the handshake: the endpoint authenticates the token and resolves the room inside it, and the session is closed before the receive loop starts.

**The request transaction belongs to `get_db`** — CRUD functions call `flush()` to obtain generated ids but never `commit()`. The `get_db` dependency commits once when the request succeeds and rolls back on any exception.

**Alembic owns schema** — never use `Base.metadata.create_all()` alongside Alembic in application code. Migrations are run manually before starting the server locally; under Docker the API container runs them itself at startup. The test suite is the one exception: it builds a throwaway SQLite database straight from the metadata, because the migrations carry Postgres-specific types.

**ConnectionManager is in-memory** — works for a single process. Horizontal scaling requires replacing it with Redis Pub/Sub (planned milestone).

**Rooms come from the database** — seeded by migration and served by `GET /rooms`, which requires a session. They are addressed by `slug` everywhere outside the database (`rooms.id` is only what the foreign keys point at), so the WebSocket path, `web/lib/types.ts` and the remount key all carry the slug. The API is deliberately read-only for rooms: users have no permission to create or delete them, so no write endpoints are exposed.

**Two client-side routes.** `app/page.tsx` switches between splash, auth and the room list; `app/room/[slug]/page.tsx` is one room's chat. Both are Client Components — the session lives in `localStorage`, so no guard can run on the server and the room route redirects to `/` from an effect once `ready` is true. The only client-side fetch is `useRooms`, which keeps its three outcomes in a single tagged state value so the effect never writes state synchronously (the React Compiler lint rules reject that); the room route reuses it and picks its room out of the list rather than calling `GET /rooms/{slug}`.

**A dynamic page is reused when only its param changes** — `/room/general` → `/room/tech` does *not* remount it (that is what `template.tsx` is for). `useChatSocket` accumulates messages and members and never clears them, so the remount has to be forced explicitly: `ChatScreen` is rendered with `key={slug}`. Removing that key silently carries the previous room's messages into the next one.

**An unknown slug never opens a socket.** The room route resolves the slug against the fetched list and renders a notice instead of the chat when it matches nothing — showing a working-looking chat UI for a room that does not exist reads as a bug. A failed room fetch is a separate notice: "the API is down" and "no such room" are different problems and saying the wrong one sends the user hunting in the wrong place. `notFound()` is not an option here, it is documented for Server Components, Server Functions and Route Handlers only, and this check is necessarily client-side.

The server's `4004` close code still exists and is still the authority — it covers any client that skips the list, and the browser now just rarely reaches it.

## Tailwind Conventions

**Always write the canonical class, never an arbitrary value that has one.** If a utility can be expressed on Tailwind's scale, it must be: `min-h-10.5` rather than `min-h-[42px]`, `w-57.5` rather than `w-[230px]`, `size-1.75` rather than `size-[7px]`. This is the `tailwindcss(suggestCanonicalClasses)` rule the editor surfaces, and it should never have anything left to report. A spacing unit is `0.25rem`, so divide the pixel value by 4; fractional multipliers such as `4.5` or `57.5` are valid and compile to exact rules. Arbitrary values remain only where no canonical equivalent exists — one-off font sizes (`text-[15px]`), letter spacing in px (`tracking-[2px]`), shadows, gradients, and `grid-cols-[...]` templates.

**The root font size must stay at the browser default.** The scale is rem-based, so `p-4` is 16px only while `html` measures 16px. `globals.css` therefore applies the design's 13px base to `body`, not to `html`: setting it on the root shrinks every spacing, sizing, and font-size utility by 18.75% and makes the canonical class names lie about the pixels they produce.

## Known Gaps

- **Messages are never persisted.** The WebSocket handler broadcasts and forgets; the `messages` table is unused.
- **Own messages are recognised by username.** `useChatSocket` drops a broadcast whose `username` matches the session, so the same account open in two tabs never sees its own messages arrive in the other one. A per-message correlation id would replace the comparison.
- **Usernames are case-sensitive accounts.** `Ghost_99` and `ghost_99` are two different rows in `users`, and neither login nor registration normalises or trims. The session now stores the name exactly as typed, which is what login proves is correct, but the two-accounts hazard is untouched.
- **No presence roster.** `members` in the frontend is only filled from live `join` events, so joining an already-populated room shows an empty member list.

## What's Pending

- Redis Pub/Sub to replace in-memory ConnectionManager
- Nginx reverse proxy with WebSocket upgrade headers
- Message history on room join (load last N messages from DB)
