import factory

from app.models import AuthUser, User
from app.models.base import get_local_now
from app.services.auth import DUMMY_CREDENTIAL


class BaseModelFactory(factory.Factory):
    class Meta:
        abstract = True

    created_at = factory.LazyFunction(get_local_now)
    updated_at = factory.LazyFunction(get_local_now)


class UserFactory(BaseModelFactory):
    class Meta:
        model = User

    name = factory.Faker("name")
    disabled_at = None
    session_version = 1


class AuthUserFactory(BaseModelFactory):
    class Meta:
        model = AuthUser

    user_id = 1
    auth_id = factory.Sequence(lambda number: f"internal.user{number}")
    credential = DUMMY_CREDENTIAL
