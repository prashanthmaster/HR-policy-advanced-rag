from __future__ import annotations

import pytest
from pydantic import ValidationError

from hr_policy_rag.config import Settings


def test_settings_are_immutable() -> None:
    settings = Settings.model_validate({})
    with pytest.raises(ValidationError):
        settings.environment = "production"  # type: ignore[misc]


def test_invalid_environment_fails_closed() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"environment": "prod"})


def test_request_id_limit_is_bounded() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"max_request_id_length": 10})
