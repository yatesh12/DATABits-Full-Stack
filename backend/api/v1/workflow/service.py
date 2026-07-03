from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.workflow import WorkflowJobModel, WorkflowRecipeModel


async def list_recipes(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    template_only: bool = False,
) -> tuple[list[WorkflowRecipeModel], int]:
    query = select(WorkflowRecipeModel).where(
        WorkflowRecipeModel.tenant_id == tenant_id,
        WorkflowRecipeModel.is_active == True,
    )
    count_query = select(func.count(WorkflowRecipeModel.id)).where(
        WorkflowRecipeModel.tenant_id == tenant_id,
        WorkflowRecipeModel.is_active == True,
    )
    if template_only:
        query = query.where(WorkflowRecipeModel.is_template == True)
        count_query = count_query.where(WorkflowRecipeModel.is_template == True)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(WorkflowRecipeModel.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all()), total


async def get_recipe(
    session: AsyncSession, recipe_id: uuid.UUID, tenant_id: uuid.UUID
) -> WorkflowRecipeModel | None:
    result = await session.execute(
        select(WorkflowRecipeModel).where(
            WorkflowRecipeModel.id == recipe_id,
            WorkflowRecipeModel.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def create_recipe(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
    steps: list[dict[str, Any]],
    description: str | None = None,
    is_template: bool = False,
    created_by: uuid.UUID | None = None,
) -> WorkflowRecipeModel:
    recipe = WorkflowRecipeModel(
        tenant_id=tenant_id,
        name=name,
        description=description,
        steps=steps,
        is_template=is_template,
        created_by=created_by,
    )
    session.add(recipe)
    await session.flush()
    return recipe


async def update_recipe(
    session: AsyncSession,
    recipe: WorkflowRecipeModel,
    updates: dict[str, Any],
) -> WorkflowRecipeModel:
    for key, value in updates.items():
        if value is not None:
            setattr(recipe, key, value)
    recipe.version += 1
    recipe.updated_at = datetime.now(timezone.utc)
    session.add(recipe)
    await session.flush()
    return recipe


async def delete_recipe(
    session: AsyncSession, recipe: WorkflowRecipeModel
) -> None:
    recipe.is_active = False
    session.add(recipe)
    await session.flush()


async def execute_recipe(
    session: AsyncSession,
    recipe: WorkflowRecipeModel,
    dataset_id: uuid.UUID,
    user_id: uuid.UUID,
) -> WorkflowJobModel:
    job = WorkflowJobModel(
        tenant_id=recipe.tenant_id,
        recipe_id=recipe.id,
        dataset_id=dataset_id,
        name=f"Run: {recipe.name}",
        status="pending",
        created_by=user_id,
    )
    session.add(job)
    await session.flush()
    return job


async def list_workflow_jobs(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[WorkflowJobModel]:
    result = await session.execute(
        select(WorkflowJobModel)
        .where(WorkflowJobModel.tenant_id == tenant_id)
        .order_by(WorkflowJobModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_workflow_job(
    session: AsyncSession, job_id: uuid.UUID, tenant_id: uuid.UUID
) -> WorkflowJobModel | None:
    result = await session.execute(
        select(WorkflowJobModel)
        .options(selectinload(WorkflowJobModel.logs), selectinload(WorkflowJobModel.recipe))
        .where(WorkflowJobModel.id == job_id, WorkflowJobModel.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()
