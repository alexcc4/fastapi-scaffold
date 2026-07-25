from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import app.cli as cli_module
from app.services.auth import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    SessionInspection,
)


runner = CliRunner()


def test_create_user_hides_password(monkeypatch) -> None:
    async def fake_create_internal_user(*_args, **_kwargs):
        return SimpleNamespace(id=7)

    async def fake_run(operation):
        return await operation(None)

    monkeypatch.setattr(
        cli_module,
        "create_internal_user",
        fake_create_internal_user,
    )
    monkeypatch.setattr(cli_module, "_run_with_database", fake_run)

    secret = "test-password-123"
    result = runner.invoke(
        cli_module.cli,
        ["create-user", "scaffold.admin", "--name", "Admin"],
        input=f"{secret}\n{secret}\n",
    )

    assert result.exit_code == 0
    assert "Created user id=7" in result.output
    assert secret not in result.output


def test_inspect_session_hides_token(monkeypatch) -> None:
    async def fake_run(operation):
        return SessionInspection(
            fingerprint="abc123def456",
            exists=True,
            user_id=7,
            session_version=2,
            database_version=2,
            ttl_seconds=300,
            created_at="2026-07-25T10:00:00",
        )

    monkeypatch.setattr(
        cli_module,
        "_run_with_database_and_redis",
        fake_run,
    )

    token = "sess_never-print-this-token"
    result = runner.invoke(
        cli_module.cli,
        ["inspect-session"],
        input=f"{token}\n",
    )

    assert result.exit_code == 0
    assert "session_fp=abc123def456" in result.output
    assert token not in result.output


def test_cli_exposes_all_account_commands() -> None:
    result = runner.invoke(cli_module.cli, ["--help"])

    assert result.exit_code == 0
    for command in (
        "create-user",
        "reset-password",
        "disable-user",
        "enable-user",
        "inspect-session",
    ):
        assert command in result.output


@pytest.mark.parametrize(
    ("command", "service_name", "expected"),
    [
        ("reset-password", "reset_internal_password", "Reset password"),
        ("disable-user", "disable_internal_user", "Disabled user"),
        ("enable-user", "enable_internal_user", "Enabled user"),
    ],
)
def test_account_commands_succeed(
    monkeypatch,
    command: str,
    service_name: str,
    expected: str,
) -> None:
    async def fake_service(*_args, **_kwargs):
        return SimpleNamespace(id=8)

    async def fake_run(operation):
        return await operation(None)

    monkeypatch.setattr(cli_module, service_name, fake_service)
    monkeypatch.setattr(cli_module, "_run_with_database", fake_run)
    input_text = (
        "test-password-123\ntest-password-123\n"
        if command == "reset-password"
        else None
    )

    result = runner.invoke(
        cli_module.cli,
        [command, "scaffold.admin"],
        input=input_text,
    )

    assert result.exit_code == 0
    assert expected in result.output


@pytest.mark.parametrize(
    ("command", "service_name"),
    [
        ("reset-password", "reset_internal_password"),
        ("disable-user", "disable_internal_user"),
        ("enable-user", "enable_internal_user"),
    ],
)
def test_account_commands_return_nonzero_for_unknown_user(
    monkeypatch,
    command: str,
    service_name: str,
) -> None:
    async def fake_service(*_args, **_kwargs):
        raise AccountNotFoundError("account was not found")

    async def fake_run(operation):
        return await operation(None)

    monkeypatch.setattr(cli_module, service_name, fake_service)
    monkeypatch.setattr(cli_module, "_run_with_database", fake_run)
    input_text = (
        "test-password-123\ntest-password-123\n"
        if command == "reset-password"
        else None
    )

    result = runner.invoke(
        cli_module.cli,
        [command, "missing.user"],
        input=input_text,
    )

    assert result.exit_code == 1
    assert "account was not found" in result.output


def test_create_user_returns_nonzero_for_duplicate(monkeypatch) -> None:
    async def fake_create(*_args, **_kwargs):
        raise AccountAlreadyExistsError("account already exists")

    async def fake_run(operation):
        return await operation(None)

    monkeypatch.setattr(cli_module, "create_internal_user", fake_create)
    monkeypatch.setattr(cli_module, "_run_with_database", fake_run)

    result = runner.invoke(
        cli_module.cli,
        ["create-user", "scaffold.admin", "--name", "Admin"],
        input="test-password-123\ntest-password-123\n",
    )

    assert result.exit_code == 1
    assert "account already exists" in result.output


def test_inspect_session_reports_missing_token(monkeypatch) -> None:
    async def fake_run(operation):
        return SessionInspection(
            fingerprint="abc123def456",
            exists=False,
        )

    monkeypatch.setattr(
        cli_module,
        "_run_with_database_and_redis",
        fake_run,
    )

    result = runner.invoke(
        cli_module.cli,
        ["inspect-session"],
        input="sess_missing-token\n",
    )

    assert result.exit_code == 0
    assert "session_fp=abc123def456" in result.output
    assert "exists=false" in result.output
    assert "sess_missing-token" not in result.output
