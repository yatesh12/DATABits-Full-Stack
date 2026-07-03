from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal
from api.v1.support.schemas import (
    CreateTicketRequest,
    DocSearchResponse,
    FaqResponse,
    MessageResponse,
    TicketReplyRequest,
    TicketReplyResponse,
    TicketResponse,
)
from api.v1.support.service import (
    close_ticket,
    create_ticket,
    get_ticket,
    list_faq,
    list_tickets,
    reply_to_ticket,
    search_docs,
)
from models.auth import UserModel

router = APIRouter(tags=["support"], prefix="/support")


@router.get("/tickets", response_model=list[TicketResponse])
async def list_tickets_endpoint(
    status: str | None = Query(None),
    category: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> list[TicketResponse]:
    tickets, total = await list_tickets(
        session, current_user.id, limit, offset, status, category
    )
    return [TicketResponse(**t) for t in tickets]


@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket_endpoint(
    body: CreateTicketRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> TicketResponse:
    ticket = await create_ticket(
        session,
        current_user.id,
        body.subject,
        body.description,
        body.category,
        body.priority,
    )
    return TicketResponse(**ticket)


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket_endpoint(
    ticket_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> TicketResponse:
    ticket = await get_ticket(session, ticket_id, current_user.id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketResponse(**ticket)


@router.post("/tickets/{ticket_id}/reply", response_model=TicketReplyResponse)
async def reply_to_ticket_endpoint(
    ticket_id: int,
    body: TicketReplyRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> TicketReplyResponse:
    ticket = await get_ticket(session, ticket_id, current_user.id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    reply = await reply_to_ticket(
        session, ticket_id, current_user.id, body.message, is_staff=False
    )
    return TicketReplyResponse(**reply)


@router.post("/tickets/{ticket_id}/close", response_model=MessageResponse)
async def close_ticket_endpoint(
    ticket_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> MessageResponse:
    ticket = await get_ticket(session, ticket_id, current_user.id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    success = await close_ticket(session, ticket_id, current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to close ticket")
    return MessageResponse(message="Ticket closed successfully")


@router.get("/faq", response_model=list[FaqResponse])
async def get_faq(
    session: AsyncSession = Depends(get_db),
) -> list[FaqResponse]:
    faqs = await list_faq(session)
    return [FaqResponse(**f) for f in faqs]


@router.get("/docs", response_model=list[DocSearchResponse])
async def search_documentation(
    query: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(10, ge=1, le=50),
) -> list[DocSearchResponse]:
    results = await search_docs(query, limit)
    return [DocSearchResponse(**r) for r in results]
