from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi import FastAPI

from hr_policy_rag.app import create_app
from hr_policy_rag.config import Settings


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _settings(**overrides: str) -> Settings:
    return Settings.model_validate({"environment": "test", **overrides})


@asynccontextmanager
async def _client(app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.anyio
async def test_liveness_is_process_only() -> None:
    async with _client(create_app(_settings())) as client:
        response = await client.get("/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.anyio
async def test_readiness_reports_required_components() -> None:
    async with _client(create_app(_settings())) as client:
        response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "components": {"application": {"ready": True, "code": "READY", "detail": None}},
    }


@pytest.mark.anyio
async def test_readiness_failure_is_not_liveness_failure() -> None:
    app = create_app(_settings())
    async with _client(app) as client:
        app.state.readiness.set(name="retrieval", ready=False, code="RETRIEVAL_UNAVAILABLE")
        ready_response = await client.get("/ready")
        live_response = await client.get("/live")
    assert ready_response.status_code == 503
    assert ready_response.json()["components"]["retrieval"]["code"] == "RETRIEVAL_UNAVAILABLE"
    assert live_response.status_code == 200


@pytest.mark.anyio
async def test_version_is_machine_readable() -> None:
    settings = _settings(
        git_sha="abc123",
        build_id="build-7",
        corpus_generation="corpus-2",
        index_generation="index-2",
    )
    async with _client(create_app(settings)) as client:
        response = await client.get("/version")
    assert response.status_code == 200
    assert response.json() == {
        "service": "hr-policy-rag",
        "environment": "test",
        "app_version": "0.1.0",
        "git_sha": "abc123",
        "build_id": "build-7",
        "corpus_generation": "corpus-2",
        "index_generation": "index-2",
    }


@pytest.mark.anyio
async def test_root_links_to_generated_api_documentation() -> None:
    async with _client(create_app(_settings())) as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"service": "hr-policy-rag", "docs": "http://test/docs"}


@pytest.mark.anyio
async def test_request_id_is_returned_and_untrusted_value_is_replaced() -> None:
    settings = _settings()
    async with _client(create_app(settings)) as client:
        accepted = await client.get("/live", headers={settings.request_id_header: "review-123"})
        replaced = await client.get("/live", headers={settings.request_id_header: "not valid because spaces"})
    assert accepted.headers[settings.request_id_header] == "review-123"
    assert replaced.headers[settings.request_id_header] != "not valid because spaces"
