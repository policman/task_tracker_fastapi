from typing import Generic, TypeVar

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, obj_id: int) -> ModelType | None:
        return await self.session.scalar(
            select(self.model).where(self.model.id == obj_id)
        )

    async def create(self, data: dict) -> ModelType:
        obj = self.model(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update(self, obj: ModelType, data: dict) -> ModelType:
        for key, value in data.items():
            setattr(obj, key, value)
        await self.session.flush()
        return obj
