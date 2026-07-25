from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db


DbSession = Annotated[AsyncSession, Depends(get_db, scope="function")]
