from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_local_environment_files_cannot_enter_git_or_docker_context() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()

    for patterns in (gitignore, dockerignore):
        assert ".env" in patterns
        assert "*.env" in patterns


def test_environment_template_contains_only_a_non_secret_placeholder() -> None:
    template = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "OPENAI_API_KEY=replace_with_a_new_project_key" in template
    assert "sk-" not in template
