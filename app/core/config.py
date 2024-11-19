import os 
from typing import Any, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database settings
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    
    # Redis settings
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_POOL_SIZE: int = 10
    REDIS_POOL_TIMEOUT: int = 5
    
    # App settings
    DEBUG: Optional[bool] = False
    SECRET_KEY: str
    TOKEN_EXPIRE_DAYS: Optional[int] = 30

    API_V1_STR: str = "/api/v1"
    CLERK_API_URL: str = "https://api.clerk.dev/v1"
    CLERK_SECRET_KEY: Optional[str] = None

    @property
    def DATABASE_URL(self) -> str:
        if os.getenv("TESTING"):
            return "mysql+aiomysql://root:root@localhost:3306/test_db?charset=utf8mb4"
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    @property
    def REDIS_URL(self) -> str:
        if os.getenv("TESTING"):
            return "redis://localhost:6379/9"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('APP_ENV', 'local')}",
        case_sensitive=True
    )


settings = Settings()
