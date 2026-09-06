"""Explicit component readiness state.

Liveness answers whether the process is running. Readiness answers whether the
required dependencies for serving a trustworthy response are usable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ComponentState:
    ready: bool
    code: str
    detail: str | None = None


def _empty_component_map() -> dict[str, ComponentState]:
    return {}


@dataclass(slots=True)
class ReadinessRegistry:
    _components: dict[str, ComponentState] = field(default_factory=_empty_component_map)

    def set(self, name: str, *, ready: bool, code: str, detail: str | None = None) -> None:
        self._components[name] = ComponentState(ready=ready, code=code, detail=detail)

    @property
    def ready(self) -> bool:
        return bool(self._components) and all(component.ready for component in self._components.values())

    def snapshot(self) -> dict[str, ComponentState]:
        return dict(self._components)
