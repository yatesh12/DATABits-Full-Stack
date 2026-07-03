from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_principal
from api.v1.events.schemas import (
    CreateEventRequest,
    EventResponse,
    RegisterEventResponse,
)
from api.v1.events.service import create_event, get_event, list_events, register_for_event
from models.auth import UserModel

router = APIRouter(tags=["events"], prefix="/events")


@router.get("", response_model=list[EventResponse])
async def list_events_endpoint(
    event_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> list[EventResponse]:
    events, total = await list_events(session, None, limit, offset, event_type)
    return [EventResponse(**e) for e in events]


@router.get("/{event_id}", response_model=EventResponse)
async def get_event_endpoint(
    event_id: int,
    session: AsyncSession = Depends(get_db),
) -> EventResponse:
    event = await get_event(session, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse(**event)


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event_endpoint(
    body: CreateEventRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> EventResponse:
    event = await create_event(
        session,
        title=body.title,
        description=body.description,
        event_type=body.event_type,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        location=body.location,
        max_attendees=body.max_attendees,
        metadata=body.metadata,
        created_by=current_user.id,
    )
    return EventResponse(**event)


@router.post("/{event_id}/register", response_model=RegisterEventResponse)
async def register_for_event_endpoint(
    event_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_principal),
) -> RegisterEventResponse:
    result = await register_for_event(session, event_id, current_user.id)
    return RegisterEventResponse(**result)
