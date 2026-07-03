from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.auth import UserModel

# TODO: Create TicketModel, TicketReplyModel, FaqModel in models


async def list_tickets(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    category: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    # TODO: Query TicketModel
    return [], 0


async def create_ticket(
    session: AsyncSession,
    user_id: uuid.UUID,
    subject: str,
    description: str,
    category: str,
    priority: str,
) -> dict[str, Any]:
    from datetime import datetime, timezone

    # TODO: Create TicketModel
    return {
        "id": 0,
        "subject": subject,
        "description": description,
        "category": category,
        "priority": priority,
        "status": "open",
        "created_by": str(user_id),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


async def get_ticket(
    session: AsyncSession, ticket_id: int, user_id: uuid.UUID
) -> dict[str, Any] | None:
    # TODO: Query TicketModel
    return None


async def reply_to_ticket(
    session: AsyncSession,
    ticket_id: int,
    user_id: uuid.UUID,
    message: str,
    is_staff: bool = False,
) -> dict[str, Any]:
    from datetime import datetime, timezone

    # TODO: Create TicketReplyModel
    return {
        "id": 0,
        "message": message,
        "is_staff": is_staff,
        "created_by": str(user_id),
        "created_at": datetime.now(timezone.utc),
    }


async def close_ticket(
    session: AsyncSession, ticket_id: int, user_id: uuid.UUID
) -> bool:
    # TODO: Update TicketModel status
    return True


async def list_faq(session: AsyncSession) -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "question": "How do I upload a dataset?",
            "answer": "Navigate to the Upload section and select your file. Supported formats include CSV, Excel, JSON, Parquet, and more.",
            "category": "general",
            "order": 1,
        },
        {
            "id": 2,
            "question": "What is the maximum file size?",
            "answer": "The maximum file size is 100 MB for free plans and up to 1 GB for enterprise plans.",
            "category": "general",
            "order": 2,
        },
        {
            "id": 3,
            "question": "How does data preprocessing work?",
            "answer": "DATABits provides tools for handling missing values, normalizing data, encoding categories, removing outliers, and more. You can apply these through the dataset interface or create automated workflows.",
            "category": "features",
            "order": 3,
        },
    ]


async def search_docs(
    query: str, limit: int = 10
) -> list[dict[str, Any]]:
    # TODO: Integrate with documentation search backend
    return [
        {
            "id": "doc-1",
            "title": "Getting Started",
            "excerpt": "Learn how to get started with DATABits...",
            "url": "/docs/getting-started",
            "score": 0.95,
        },
        {
            "id": "doc-2",
            "title": "Data Upload Guide",
            "excerpt": "Detailed guide on uploading datasets...",
            "url": "/docs/upload-guide",
            "score": 0.85,
        },
    ]
