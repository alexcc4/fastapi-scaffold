import pytest
from alembic import command
from alembic.config import Config

from app.core.config import Settings


@pytest.mark.integration
def test_alembic_upgrade_head(
    safe_integration_settings: Settings,
    migrated_database: None,
) -> None:
    assert safe_integration_settings.APP_ENV == "test"
    command.check(Config("alembic.ini"))
