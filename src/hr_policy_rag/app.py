"""Single-process FastAPI application for the v2 quality foundation."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status

from hr_policy_rag.api_models import ComponentResponse, LiveResponse, ReadyResponse, VersionResponse
from hr_policy_rag.config import Settings, get_settings
from hr_policy_rag.observability import configure_logging, request_id_middleware
from hr_policy_rag.readiness import ReadinessRegistry

_logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    readiness = ReadinessRegistry()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        configure_logging(runtime_settings)
        readiness.set(name="application", ready=True, code="READY")
        _logger.info("application initialized", extra={"event": "application_started"})
        yield
        _logger.info("application stopped", extra={"event": "application_stopped"})

    application = FastAPI(
        title="HR Policy RAG",
        description="Version-aware HR policy retrieval with evidence-linked answers.",
        version=runtime_settings.app_version,
        lifespan=lifespan,
    )
    application.middleware("http")(request_id_middleware(runtime_settings))

    async def live() -> LiveResponse:
        return LiveResponse(status="alive")

    async def ready(response: Response) -> ReadyResponse:
        snapshot = readiness.snapshot()
        is_ready = readiness.ready
        if not is_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyResponse(
            status="ready" if is_ready else "not_ready",
            components={
                name: ComponentResponse(ready=component.ready, code=component.code, detail=component.detail)
                for name, component in snapshot.items()
            },
        )

    async def version() -> VersionResponse:
        return VersionResponse(
            service=runtime_settings.service_name,
            environment=runtime_settings.environment,
            app_version=runtime_settings.app_version,
            git_sha=runtime_settings.git_sha,
            build_id=runtime_settings.build_id,
            corpus_generation=runtime_settings.corpus_generation,
            index_generation=runtime_settings.index_generation,
        )

    async def root(request: Request) -> dict[str, str]:
        return {"service": runtime_settings.service_name, "docs": str(request.url_for("swagger_ui_html"))}

    application.add_api_route("/live", live, methods=["GET"], response_model=LiveResponse)
    application.add_api_route("/ready", ready, methods=["GET"], response_model=ReadyResponse)
    application.add_api_route("/version", version, methods=["GET"], response_model=VersionResponse)
    application.add_api_route("/", root, methods=["GET"], include_in_schema=False)

    application.state.settings = runtime_settings
    application.state.readiness = readiness
    return application


app = create_app()
