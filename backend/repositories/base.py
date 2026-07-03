from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from sqlalchemy import select, func, delete, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self._session = session
        self._model = model

    async def get(self, id: Any) -> Optional[T]:
        stmt = select(self._model).where(self._model.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> list[T]:
        stmt = select(self._model)

        if filters:
            conditions = [
                getattr(self._model, key) == value
                for key, value in filters.items()
                if hasattr(self._model, key)
            ]
            if conditions:
                stmt = stmt.where(and_(*conditions))

        if order_by and hasattr(self._model, order_by):
            order_col = getattr(self._model, order_by)
            stmt = stmt.order_by(order_col.desc() if descending else order_col)

        stmt = stmt.offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: dict[str, Any]) -> T:
        instance = self._model(**data)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update(self, id: Any, data: dict[str, Any]) -> Optional[T]:
        stmt = (
            update(self._model)
            .where(self._model.id == id)
            .values(**data)
            .returning(self._model)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none()

    async def delete(self, id: Any) -> bool:
        stmt = delete(self._model).where(self._model.id == id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0

    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        stmt = select(func.count(self._model.id))

        if filters:
            conditions = [
                getattr(self._model, key) == value
                for key, value in filters.items()
                if hasattr(self._model, key)
            ]
            if conditions:
                stmt = stmt.where(and_(*conditions))

        result = await self._session.execute(stmt)
        return result.scalar_one()
