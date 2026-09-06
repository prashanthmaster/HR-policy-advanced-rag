from __future__ import annotations

from collections.abc import Mapping

from hr_policy_rag.ports import GuardrailBoundary, GuardrailVerdict, Telemetry


class MemoryTelemetry:
    def __init__(self) -> None:
        self.events: list[tuple[str, Mapping[str, str | int | float | bool | None]]] = []

    def event(self, *, name: str, attributes: Mapping[str, str | int | float | bool | None]) -> None:
        self.events.append((name, attributes))


def test_port_contracts_are_provider_neutral_and_runtime_checkable() -> None:
    telemetry = MemoryTelemetry()
    assert isinstance(telemetry, Telemetry)

    telemetry.event(name="candidate_validated", attributes={"point_count": 72})
    assert telemetry.events == [("candidate_validated", {"point_count": 72})]
    assert GuardrailBoundary.INPUT.value == "INPUT"
    assert GuardrailVerdict.UNAVAILABLE.value == "UNAVAILABLE"
