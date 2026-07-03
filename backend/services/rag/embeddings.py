from __future__ import annotations

import uuid
from typing import Any, Optional

from core.config import get_settings

settings = get_settings()


class EmbeddingService:
    def __init__(self) -> None:
        self._embedding_model = None
        self._qdrant_client = None

    async def _get_embedder(self):
        if self._embedding_model is None:
            from fastembed import TextEmbedding
            self._embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        return self._embedding_model

    async def _get_qdrant(self):
        if self._qdrant_client is None:
            from qdrant_client import QdrantClient
            self._qdrant_client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                timeout=30,
            )
        return self._qdrant_client

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        embedder = await self._get_embedder()
        embeddings = list(embedder.embed(texts))
        return [e.tolist() for e in embeddings]

    async def store_embeddings(
        self,
        collection: str,
        vectors: list[list[float]],
        metadata: list[dict[str, Any]],
        ids: Optional[list[str]] = None,
    ) -> list[str]:
        from qdrant_client import models as qdrant_models

        client = await self._get_qdrant()
        point_ids = ids or [str(uuid.uuid4()) for _ in vectors]

        points = [
            qdrant_models.PointStruct(
                id=point_ids[i],
                vector=vectors[i],
                payload=metadata[i] if i < len(metadata) else {},
            )
            for i in range(len(vectors))
        ]

        client.upsert(collection_name=collection, points=points)
        return point_ids

    async def search_similar(
        self,
        collection: str,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        embedder = await self._get_embedder()
        client = await self._get_qdrant()

        query_vector = next(embedder.embed([query])).tolist()
        results = client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
        )

        return [
            {
                "id": r.id,
                "score": r.score,
                "payload": r.payload,
            }
            for r in results
        ]

    async def delete_embeddings(self, collection: str, ids: list[str]) -> None:
        client = await self._get_qdrant()
        client.delete(
            collection_name=collection,
            points_selector=ids,
        )
