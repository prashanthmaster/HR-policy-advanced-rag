FROM ghcr.io/astral-sh/uv:0.11.33 AS uv

FROM python:3.12.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --locked --no-install-project
RUN uv sync --locked

USER 65532:65532

EXPOSE 8080

CMD ["uvicorn", "hr_policy_rag.app:app", "--host", "0.0.0.0", "--port", "8080"]
