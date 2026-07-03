from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal
from api.v1.assistant.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    ConversationCreateRequest,
    ConversationResponse,
    MessageResponse,
    QueryRequest,
    QueryResponse,
    SuggestRequest,
    SuggestResponse,
)
from api.v1.assistant.service import (
    analyze_dataset,
    chat_with_ai,
    query_dataset_nl,
    suggest_preprocessing_steps,
)
from models.auth import UserModel

router = APIRouter(tags=["assistant"], prefix="/assistant")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    current_user: UserModel = Depends(get_principal),
) -> ChatResponse:
    result = await chat_with_ai(
        message=body.message,
        conversation_id=body.conversation_id,
        dataset_id=body.dataset_id,
        user_id=current_user.id,
    )
    return ChatResponse(**result)


@router.post("/query", response_model=QueryResponse)
async def query_dataset(
    body: QueryRequest,
    current_user: UserModel = Depends(get_principal),
) -> QueryResponse:
    result = await query_dataset_nl(
        query=body.query,
        dataset_id=body.dataset_id,
        max_results=body.max_results,
        user_id=current_user.id,
    )
    return QueryResponse(**result)


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_steps(
    body: SuggestRequest,
    current_user: UserModel = Depends(get_principal),
) -> SuggestResponse:
    result = await suggest_preprocessing_steps(
        dataset_id=body.dataset_id,
        goal=body.goal,
        constraints=body.constraints,
        user_id=current_user.id,
    )
    return SuggestResponse(**result)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    body: AnalyzeRequest,
    current_user: UserModel = Depends(get_principal),
) -> AnalyzeResponse:
    result = await analyze_dataset(
        dataset_id=body.dataset_id,
        questions=body.questions,
        user_id=current_user.id,
    )
    return AnalyzeResponse(**result)


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[ConversationResponse]:
    # TODO: Implement conversation persistence
    return []


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    body: ConversationCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> ConversationResponse:
    # TODO: Implement conversation persistence
    return ConversationResponse(
        id="placeholder",
        title=body.title,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        message_count=0,
    )


@router.get("/conversations/{conversation_id}", response_model=list[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[MessageResponse]:
    # TODO: Implement conversation persistence
    return []
