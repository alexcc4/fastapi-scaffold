from app.models import AuthUser, User
from tests.factories import AuthUserFactory, UserFactory


def test_user_factory_builds_unsaved_model() -> None:
    user = UserFactory.build()
    auth_user = AuthUserFactory.build(user_id=42)

    assert isinstance(user, User)
    assert isinstance(auth_user, AuthUser)
    assert user.session_version == 1
    assert auth_user.user_id == 42
