from __future__ import annotations

from typing import Any, Optional

from core.config import get_settings
from services.rag.embeddings import EmbeddingService

settings = get_settings()

SYSTEM_PROMPT = """You are DATABits AI, a helpful data analysis assistant. You help users understand and work with their datasets.
You provide clear, concise answers based on the provided context. If you don't know the answer, say so.
Always cite your sources from the provided context when possible."""

CONTEXT_TEMPLATE = """
Relevant context from the user's datasets:
{context}

Conversation history:
{history}

User query: {query}

Provide a helpful response based on the context above. If the context does not contain enough information to answer, acknowledge that and suggest what the user could do to get the information they need.
"""


class RagPipeline:
    def __init__(self) -> None:
        self._embedding_service = EmbeddingService()
        self._groq_client: Optional[Any] = None

    def _get_client(self):
        if self._groq_client is None:
            from groq import Groq
            self._groq_client = Groq(api_key=settings.GROQ_API_KEY)
        return self._groq_client

    async def _build_context(
        self,
        query: str,
        collection: str = "",
        top_k: int = 5,
    ) -> str:
        if not collection:
            return ""

        results = await self._embedding_service.search_similar(
            collection=collection,
            query=query,
            top_k=top_k,
        )

        if not results:
            return ""

        context_parts = []
        for i, r in enumerate(results, 1):
            payload = r.get("payload", {})
            text = payload.get("text", payload.get("content", ""))
            source = payload.get("source", payload.get("filename", "unknown"))
            if text:
                context_parts.append(f"[{i}] From {source}:\n{text}")

        return "\n\n".join(context_parts) if context_parts else ""

    async def answer_query(
        self,
        query: str,
        context: Optional[str] = None,
        conversation_history: Optional[list[dict[str, str]]] = None,
        collection: str = "",
    ) -> dict[str, Any]:
        client = self._get_client()

        if context is None:
            context = await self._build_context(query, collection=collection)

        history_str = ""
        if conversation_history:
            history_parts = []
            for msg in conversation_history[-10:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_parts.append(f"{role}: {content}")
            history_str = "\n".join(history_parts)

        prompt = CONTEXT_TEMPLATE.format(
            context=context or "No specific context available.",
            history=history_str or "No previous conversation.",
            query=query,
        )

        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=2048,
        )

        answer = completion.choices[0].message.content if completion.choices else ""

        return {
            "query": query,
            "answer": answer,
            "context_used": bool(context),
            "model": settings.GROQ_MODEL,
            "usage": {
                "prompt_tokens": completion.usage.prompt_tokens if completion.usage else None,
                "completion_tokens": completion.usage.completion_tokens if completion.usage else None,
                "total_tokens": completion.usage.total_tokens if completion.usage else None,
            } if completion.usage else None,
        }
