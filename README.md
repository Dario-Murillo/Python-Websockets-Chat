# Python-Websockets-Chat

A realtime chat web app built with FastAPI, WebSockets, and a lightweight browser frontend.

## Overview

This project provides a simple chat application backend with user registration, JWT authentication, and WebSocket-powered room chat support. The API is implemented in Python using FastAPI and async SQLAlchemy, while the frontend is a plain HTML/JavaScript client located in the `web/` folder.

## Features

- User registration and login
- JWT access tokens for API and WebSocket authentication
- WebSocket room connections
- Room-based message broadcasts
- Async database access with SQLAlchemy and PostgreSQL/SQLite-compatible async URL support
- Alembic migrations for database schema management

## Tech Stack

- Python 3.11+ (recommended)
- FastAPI
- SQLAlchemy asyncio
- asyncpg / any async database driver supported by SQLAlchemy
- Alembic
- Pydantic
- JWT authentication
- Plain HTML/CSS/JavaScript frontend

## Repository Structure

- `api/` - backend application
  - `main.py` - FastAPI application entrypoint
  - `routers/` - API and WebSocket route definitions
  - `database.py` - async database engine and session management
  - `auth.py` - password hashing, token creation, and user verification
  - `config.py` - environment settings loader
  - `models.py` - SQLAlchemy ORM models
  - `schemas.py` - request/response Pydantic schemas
  - `requirements.txt` - Python dependencies
  - `alembic/` - DB migration configuration and versions
- `web/` - frontend client files
  - `index.html`
  - `app.js`
  - `style.css`

## Prerequisites

- Python 3.11 or newer
- Git (optional)
- A database supported by SQLAlchemy async connections
- `pip` package manager

## Backend Setup

1. Open a terminal and navigate to the project root:

```powershell
cd "e:\Programación\Python\Python-Websockets-Chat\api"
```

2. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Create a `.env` file in `api/` with the required environment variables:

```text
DATABASE_URL=sqlite+aiosqlite:///./chat.db
SECRET_KEY=your-secret-key
```

> If you prefer PostgreSQL, set `DATABASE_URL` to a valid Postgres async URL like:
> `postgresql+asyncpg://user:password@localhost:5432/chatdb`

5. Apply database migrations:

```powershell
alembic upgrade head
```

## Running the Backend

Start the FastAPI app with Uvicorn:

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

## Frontend Usage

The frontend client is located in `web/index.html`. You can open this file directly in your browser or serve it from a static web server.

If you want a quick local server, use Python from the project root:

```powershell
cd "e:\Programación\Python\Python-Websockets-Chat\web"
python -m http.server 3000
```

Then open `http://localhost:3000` in your browser.

## API Endpoints

- `POST /users/register` - Register a new user
- `POST /users/token` - Log in and receive a JWT access token
- `GET /users/me` - Retrieve the current authenticated user
- `GET /rooms/` - Get rooms (currently placeholder)
- `POST /rooms/` - Create a room (currently placeholder)
- `GET /rooms/{room_id}` - Get room details (currently placeholder)
- `DELETE /rooms/{room_id}` - Delete a room (currently placeholder)

## WebSocket Usage

The WebSocket endpoint is:

```text
ws://localhost:8000/ws/{room_id}?token={JWT_TOKEN}
```

Replace `{room_id}` with the room identifier and `{JWT_TOKEN}` with a valid JWT obtained from `/users/token`.

The frontend should send a join event after connecting and then send message payloads as JSON.

## Example Auth Flow

1. Register a user:

```http
POST /users/register
Content-Type: application/json

{
  "username": "alice",
  "password": "password123"
}
```

2. Log in for a token:

```http
POST /users/token
Content-Type: application/x-www-form-urlencoded

username=alice&password=password123
```

3. Use the returned `access_token` for WebSocket auth:

```text
ws://localhost:8000/ws/room1?token=eyJhbGciOiJI...
```

## Notes

- `rooms` endpoints are currently defined as placeholders and may need further implementation.
- Database URL and secret key are loaded from `.env`.
- CORS is configured for `http://localhost:3000` and `http://[::1]:3000`.

## License

This project is provided as-is for learning and experimentation.

