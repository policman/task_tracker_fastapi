from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db

router = APIRouter(prefix="/api/v1/health", tags=["System"])


@router.get("", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}


@router.get("/db", status_code=status.HTTP_200_OK)
async def health_db_check(session: AsyncSession = Depends(get_db)):
    await session.execute(text("SELECT 1"))
    return {"status": "db_ok"}
