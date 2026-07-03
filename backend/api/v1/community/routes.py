from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal
from api.v1.community.schemas import (
    CommunityDatasetResponse,
    CommunityRecipeResponse,
    CommunityStatsResponse,
    LikeResponse,
)
from api.v1.community.service import (
    get_community_stats,
    like_recipe,
    list_community_recipes,
    list_public_datasets,
)
from models.auth import UserModel

router = APIRouter(tags=["community"], prefix="/community")


@router.get("/recipes", response_model=list[CommunityRecipeResponse])
async def list_community_recipes_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
) -> list[CommunityRecipeResponse]:
    recipes, total = await list_community_recipes(session, limit, offset, search)
    return [
        CommunityRecipeResponse(
            id=str(r.id),
            name=r.name,
            description=r.description,
            steps=r.steps,
            version=r.version,
            like_count=0,
            created_by=str(r.created_by) if r.created_by else None,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in recipes
    ]


@router.post("/recipes/{recipe_id}/like", response_model=LikeResponse)
async def like_recipe_endpoint(
    recipe_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> LikeResponse:
    result = await like_recipe(session, recipe_id, current_user.id)
    return LikeResponse(**result)


@router.get("/datasets", response_model=list[CommunityDatasetResponse])
async def list_public_datasets_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
) -> list[CommunityDatasetResponse]:
    datasets, total = await list_public_datasets(session, limit, offset, search)
    return [
        CommunityDatasetResponse(
            id=str(d.id),
            name=d.name,
            description=None,
            row_count=d.row_count,
            column_count=d.column_count,
            file_size=d.file_size,
            tags=[],
            download_count=0,
            created_by=str(d.user_id) if d.user_id else None,
            created_at=d.created_at,
        )
        for d in datasets
    ]


@router.get("/stats", response_model=CommunityStatsResponse)
async def community_stats(
    session: AsyncSession = Depends(get_db),
) -> CommunityStatsResponse:
    stats = await get_community_stats(session)
    return CommunityStatsResponse(**stats)
