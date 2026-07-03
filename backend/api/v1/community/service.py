from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.auth import UserModel
from models.data_platform import DatasetModel
from models.workflow import WorkflowRecipeModel


async def list_community_recipes(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    search: str | None = None,
) -> tuple[list[WorkflowRecipeModel], int]:
    query = select(WorkflowRecipeModel).where(
        WorkflowRecipeModel.is_template == True,
        WorkflowRecipeModel.is_active == True,
    )
    count_query = select(func.count(WorkflowRecipeModel.id)).where(
        WorkflowRecipeModel.is_template == True,
        WorkflowRecipeModel.is_active == True,
    )

    if search:
        search_filter = WorkflowRecipeModel.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(WorkflowRecipeModel.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all()), total


async def like_recipe(
    session: AsyncSession, recipe_id: uuid.UUID, user_id: uuid.UUID
) -> dict[str, Any]:
    # TODO: Implement like persistence
    return {"liked": True, "like_count": 0}


async def list_public_datasets(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    search: str | None = None,
) -> tuple[list[DatasetModel], int]:
    query = select(DatasetModel).where(DatasetModel.status == "published")
    count_query = select(func.count(DatasetModel.id)).where(DatasetModel.status == "published")

    if search:
        search_filter = DatasetModel.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(DatasetModel.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all()), total


async def get_community_stats(session: AsyncSession) -> dict[str, Any]:
    recipe_count = await session.execute(
        select(func.count(WorkflowRecipeModel.id)).where(
            WorkflowRecipeModel.is_template == True,
            WorkflowRecipeModel.is_active == True,
        )
    )
    dataset_count = await session.execute(
        select(func.count(DatasetModel.id)).where(DatasetModel.status == "published")
    )
    user_count = await session.execute(select(func.count(UserModel.id)))
    total_recipes = recipe_count.scalar() or 0
    total_datasets = dataset_count.scalar() or 0
    total_users = user_count.scalar() or 0

    return {
        "total_recipes": total_recipes,
        "total_datasets": total_datasets,
        "total_users": total_users,
        "total_likes": 0,
        "active_this_week": 0,
    }
