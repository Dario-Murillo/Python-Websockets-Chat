FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Copy the package before installing: the build backend needs `app/` present.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

COPY alembic.ini ./
COPY alembic ./alembic

EXPOSE 8000

# Migrate before serving. Without this the container comes up against a database
# with no tables and the first request dies on a missing relation. `exec` hands
# uvicorn PID 1 so it still receives stop signals, and a failed migration takes
# the container down instead of leaving a broken API listening.
#
# Safe as a startup step because this app runs as a single instance anyway --
# ConnectionManager is in-memory. Running replicas would need a one-shot
# migration job instead, so that two containers cannot race the same upgrade.
#
# `--ws-max-size` caps a frame at 64 KiB, down from uvicorn's 16 MiB default. The
# schema already rejects an overlong message, but only after the whole frame has
# been received and parsed; this refuses it at the transport, before it costs
# anything. A 500-character message is under 2 KB even in multibyte UTF-8.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --ws-max-size 65536"]
