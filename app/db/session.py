"""
Database Session Management

Two session management approaches:
1. Basic async session (currently used)
2. Scoped session (alternative option)

For more information:
- https://docs.sqlalchemy.org/en/20/orm/contextual.html#asyncio-scoped-session
- https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-asyncio-scoped-session
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession 
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True
)

# Approach 1: Basic async session factory (currently used)
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Approach 2: Scoped session factory (alternative option)
# AsyncScopedSession = async_scoped_session(
#     sessionmaker(
#         engine,
#         class_=AsyncSession,
#         expire_on_commit=False
#     ),
#     scopefunc=current_task
# )


# Dependency function for Approach 1 (currently used)
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Dependency function for Approach 2 (if using scoped session)
# async def get_scoped_db():
#     session = AsyncScopedSession()
#     try:
#         yield session
#     finally:
#         await AsyncScopedSession.remove()
