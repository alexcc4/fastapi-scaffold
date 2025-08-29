import random

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.base import get_utc_now
from app.models.user import User, AuthUser
from app.core.auth import pwd_context


class BaseFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = None 
    
    id = factory.Sequence(lambda n: n + 1)
    created_at = factory.LazyFunction(lambda: get_utc_now())
    updated_at = factory.LazyFunction(lambda: get_utc_now())


class UserFactory(BaseFactory):
    class Meta:
        model = User
        sqlalchemy_session = None

    name = factory.Faker('user_name')
    avatar_url = factory.Faker('image_url')
    status = 1
    is_verified = 1
    deleted_at = None


class AuthUserFactory(BaseFactory):
    class Meta:
        model = AuthUser
        sqlalchemy_session = None

    user_id = factory.LazyFunction(lambda: random.randint(1, 20000))
    auth_id = factory.Faker('user_name')
    auth_type = 1 
    credential = factory.LazyFunction(lambda: pwd_context.hash("test123"))
    auth_data = None
    last_login_at = factory.LazyFunction(lambda: get_utc_now())