from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal
from api.v1.workflow.schemas import (
    CreateRecipeRequest,
    ExecuteRecipeRequest,
    MessageResponse,
    RecipeResponse,
    UpdateRecipeRequest,
    WorkflowJobDetailResponse,
    WorkflowJobResponse,
)
from api.v1.workflow.service import (
    create_recipe,
    delete_recipe,
    execute_recipe,
    get_recipe,
    get_workflow_job,
    list_recipes,
    list_workflow_jobs,
    update_recipe,
)
from models.auth import UserModel

router = APIRouter(tags=["workflow"], prefix="/workflow")


@router.get("/recipes", response_model=list[RecipeResponse])
async def list_recipes_endpoint(
    template_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[RecipeResponse]:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    recipes, total = await list_recipes(
        session, current_user.tenant_id, limit, offset, template_only
    )
    return [
        RecipeResponse(
            id=str(r.id),
            name=r.name,
            description=r.description,
            steps=r.steps,
            is_template=r.is_template,
            is_active=r.is_active,
            version=r.version,
            created_by=str(r.created_by) if r.created_by else None,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in recipes
    ]


@router.post("/recipes", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe_endpoint(
    body: CreateRecipeRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> RecipeResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    steps = [s.model_dump() for s in body.steps]
    recipe = await create_recipe(
        session,
        current_user.tenant_id,
        body.name,
        steps,
        body.description,
        body.is_template,
        current_user.id,
    )
    return RecipeResponse(
        id=str(recipe.id),
        name=recipe.name,
        description=recipe.description,
        steps=recipe.steps,
        is_template=recipe.is_template,
        is_active=recipe.is_active,
        version=recipe.version,
        created_by=str(recipe.created_by) if recipe.created_by else None,
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
    )


@router.get("/recipes/{recipe_id}", response_model=RecipeResponse)
async def get_recipe_endpoint(
    recipe_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> RecipeResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    recipe = await get_recipe(session, recipe_id, current_user.tenant_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return RecipeResponse(
        id=str(recipe.id),
        name=recipe.name,
        description=recipe.description,
        steps=recipe.steps,
        is_template=recipe.is_template,
        is_active=recipe.is_active,
        version=recipe.version,
        created_by=str(recipe.created_by) if recipe.created_by else None,
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
    )


@router.patch("/recipes/{recipe_id}", response_model=RecipeResponse)
async def update_recipe_endpoint(
    recipe_id: uuid.UUID,
    body: UpdateRecipeRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> RecipeResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    recipe = await get_recipe(session, recipe_id, current_user.tenant_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    updates = body.model_dump(exclude_unset=True)
    if "steps" in updates and updates["steps"] is not None:
        updates["steps"] = [s.model_dump() if hasattr(s, "model_dump") else s for s in updates["steps"]]
    recipe = await update_recipe(session, recipe, updates)
    return RecipeResponse(
        id=str(recipe.id),
        name=recipe.name,
        description=recipe.description,
        steps=recipe.steps,
        is_template=recipe.is_template,
        is_active=recipe.is_active,
        version=recipe.version,
        created_by=str(recipe.created_by) if recipe.created_by else None,
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
    )


@router.delete("/recipes/{recipe_id}", response_model=MessageResponse)
async def delete_recipe_endpoint(
    recipe_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    recipe = await get_recipe(session, recipe_id, current_user.tenant_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    await delete_recipe(session, recipe)
    return MessageResponse(message="Recipe deleted successfully")


@router.post("/recipes/{recipe_id}/execute", response_model=WorkflowJobResponse)
async def execute_recipe_endpoint(
    recipe_id: uuid.UUID,
    body: ExecuteRecipeRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> WorkflowJobResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    recipe = await get_recipe(session, recipe_id, current_user.tenant_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    job = await execute_recipe(session, recipe, uuid.UUID(body.dataset_id), current_user.id)
    return WorkflowJobResponse(
        id=str(job.id),
        recipe_id=str(job.recipe_id),
        dataset_id=str(job.dataset_id) if job.dataset_id else None,
        name=job.name,
        status=job.status,
        created_by=str(job.created_by) if job.created_by else None,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.get("/jobs", response_model=list[WorkflowJobResponse])
async def list_workflow_jobs_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[WorkflowJobResponse]:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    jobs = await list_workflow_jobs(session, current_user.tenant_id, limit, offset)
    return [
        WorkflowJobResponse(
            id=str(j.id),
            recipe_id=str(j.recipe_id),
            dataset_id=str(j.dataset_id) if j.dataset_id else None,
            name=j.name,
            status=j.status,
            created_by=str(j.created_by) if j.created_by else None,
            created_at=j.created_at,
            completed_at=j.completed_at,
        )
        for j in jobs
    ]


@router.get("/jobs/{job_id}", response_model=WorkflowJobDetailResponse)
async def get_workflow_job_endpoint(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> WorkflowJobDetailResponse:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    job = await get_workflow_job(session, job_id, current_user.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Workflow job not found")
    steps = []
    if job.logs:
        steps = [
            {
                "step_index": log.step_index,
                "step_name": log.step_name,
                "status": log.status,
                "input": log.input,
                "output": log.output,
                "started_at": log.started_at,
                "completed_at": log.completed_at,
                "error_message": log.error_message,
                "duration_ms": log.duration_ms,
            }
            for log in job.logs
        ]
    return WorkflowJobDetailResponse(
        id=str(job.id),
        recipe_id=str(job.recipe_id),
        dataset_id=str(job.dataset_id) if job.dataset_id else None,
        name=job.name,
        status=job.status,
        config_overrides=job.config_overrides,
        created_by=str(job.created_by) if job.created_by else None,
        created_at=job.created_at,
        completed_at=job.completed_at,
        steps=steps,
    )
