import os
from typing import Optional 

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    
    DEBUG: Optional[bool] = True
    SECRET_KEY: str = "your_secret_key"
    
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    REDIS_DB: Optional[int] = None

    JWT_SECRET_KEY: str = "your_secret_key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 30  

    @property
    def DATABASE_URL(self) -> str:
        if os.getenv("TESTING"):
            return "mysql+aiomysql://root:root@localhost:3306/test_db?charset=utf8mb4"
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('APP_ENV', 'local')}",
        case_sensitive=True,
        extra='ignore'
    )


settings = Settings() 