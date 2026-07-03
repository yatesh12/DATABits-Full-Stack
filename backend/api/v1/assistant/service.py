from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from groq import AsyncGroq
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings

settings = get_settings()


def _get_groq_client() -> AsyncGroq | None:
    if settings.GROQ_API_KEY:
        return AsyncGroq(api_key=settings.GROQ_API_KEY)
    return None


async def chat_with_ai(
    message: str,
    conversation_id: str | None = None,
    dataset_id: str | None = None,
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    client = _get_groq_client()
    if client is None:
        return {
            "reply": "AI assistant is not configured. Please set GROQ_API_KEY.",
            "conversation_id": conversation_id or str(uuid.uuid4()),
            "sources": None,
        }

    messages = [{"role": "user", "content": message}]
    if dataset_id:
        messages.insert(
            0,
            {
                "role": "system",
                "content": "You are a data analysis assistant. Help the user analyze their dataset.",
            },
        )

    try:
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )
        reply = response.choices[0].message.content or ""
    except Exception as e:
        reply = f"AI service error: {str(e)}"

    return {
        "reply": reply,
        "conversation_id": conversation_id or str(uuid.uuid4()),
        "sources": None,
    }


async def query_dataset_nl(
    query: str,
    dataset_id: str,
    max_results: int = 10,
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    client = _get_groq_client()
    if client is None:
        return {
            "answer": "AI assistant is not configured.",
            "sql_query": None,
            "results": None,
            "execution_time_ms": None,
        }

    system_prompt = (
        f"You are a data analyst. The user has a dataset with ID {dataset_id}. "
        f"Generate a response based on the query. If applicable, provide an SQL-like explanation."
    )

    try:
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            temperature=0.3,
            max_tokens=2048,
        )
        answer = response.choices[0].message.content or ""
    except Exception as e:
        answer = f"AI service error: {str(e)}"

    return {
        "answer": answer,
        "sql_query": None,
        "results": None,
        "execution_time_ms": None,
    }


async def suggest_preprocessing_steps(
    dataset_id: str,
    goal: str | None = None,
    constraints: list[str] | None = None,
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    client = _get_groq_client()
    if client is None:
        return {
            "steps": [
                {"type": "missing_values", "config": {"strategy": "drop"}},
                {"type": "normalize", "config": {"method": "minmax"}},
            ],
            "explanation": "Default preprocessing steps suggested.",
        }

    prompt = f"Suggest data preprocessing steps for dataset {dataset_id}."
    if goal:
        prompt += f" Goal: {goal}"
    if constraints:
        prompt += f" Constraints: {', '.join(constraints)}"

    try:
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2048,
        )
        explanation = response.choices[0].message.content or ""
    except Exception as e:
        explanation = f"Error: {str(e)}"

    return {
        "steps": [],
        "explanation": explanation,
    }


async def analyze_dataset(
    dataset_id: str,
    questions: list[str],
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    client = _get_groq_client()
    if client is None:
        return {
            "insights": [{"question": q, "answer": "AI not configured"} for q in questions],
            "summary": "AI assistant is not configured.",
        }

    insights = []
    for question in questions:
        try:
            response = await client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": f"Analyze dataset {dataset_id} and answer the question concisely.",
                    },
                    {"role": "user", "content": question},
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            answer = response.choices[0].message.content or ""
        except Exception as e:
            answer = f"Error: {str(e)}"
        insights.append({"question": question, "answer": answer})

    summary = f"Analysis completed for {len(questions)} questions."
    return {"insights": insights, "summary": summary}
