"""Public operational API contracts for the v2 walking skeleton."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LiveResponse(StrictModel):
    status: str


class ComponentResponse(StrictModel):
    ready: bool
    code: str
    detail: str | None = None


class ReadyResponse(StrictModel):
    status: str
    components: dict[str, ComponentResponse]


class VersionResponse(StrictModel):
    service: str
    environment: str
    app_version: str
    git_sha: str
    build_id: str
    corpus_generation: str
    index_generation: str
