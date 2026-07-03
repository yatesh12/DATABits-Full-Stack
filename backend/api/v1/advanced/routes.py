from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal
from api.v1.advanced.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CatalogItemResponse,
    EvaluateRequest,
    EvaluateResponse,
    SampleRequest,
    SampleResponse,
    TransformRequest,
    TransformResponse,
    ValidateRequest,
    ValidateResponse,
)
from api.v1.advanced.service import (
    advanced_analytics,
    advanced_sampling,
    advanced_validation,
    custom_transform,
    evaluate_model,
    get_data_catalog,
)
from models.auth import UserModel

router = APIRouter(tags=["advanced"], prefix="/advanced")


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_model_endpoint(
    body: EvaluateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> EvaluateResponse:
    try:
        result = await evaluate_model(
            session,
            body.dataset_id,
            body.model_type,
            body.target_column,
            body.test_size,
            body.features,
            body.hyperparameters,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return EvaluateResponse(**result)


@router.get("/catalog", response_model=list[CatalogItemResponse])
async def get_data_catalog_endpoint(
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[CatalogItemResponse]:
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="No tenant associated")
    catalog = await get_data_catalog(session, current_user.tenant_id)
    return [CatalogItemResponse(**item) for item in catalog]


@router.post("/sample", response_model=SampleResponse)
async def advanced_sample(
    body: SampleRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> SampleResponse:
    try:
        result = await advanced_sampling(
            session, body.dataset_id, body.method, body.size, body.seed, body.strata_column
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SampleResponse(**result)


@router.post("/validate", response_model=ValidateResponse)
async def advanced_validate(
    body: ValidateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> ValidateResponse:
    try:
        result = await advanced_validation(session, body.dataset_id, body.rules, body.strict)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ValidateResponse(**result)


@router.post("/transform", response_model=TransformResponse)
async def custom_transform_endpoint(
    body: TransformRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> TransformResponse:
    try:
        result = await custom_transform(session, body.dataset_id, body.operations, body.create_version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return TransformResponse(**result)


@router.post("/analyze", response_model=AnalyzeResponse)
async def advanced_analyze(
    body: AnalyzeRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> AnalyzeResponse:
    try:
        result = await advanced_analytics(session, body.dataset_id, body.analysis_type, body.config)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return AnalyzeResponse(**result)
