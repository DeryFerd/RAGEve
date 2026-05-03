"""
Redis caching service for RAG results.

Provides multi-level caching:
- Query embeddings (avoid re-embedding)
- Search results (Qdrant hits before reranking)
- Final answers (for identical questions)
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from backend.config_loader import get_settings
from backend.services.redis_client import get_redis_client

_log = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching for RAG operations."""

    def __init__(self) -> None:
        self._enabled = False
        self._redis = None
        self._embedding_ttl = 86400 * 7  # 7 days
        self._search_ttl = 3600  # 1 hour
        self._answer_ttl = 1800  # 30 minutes

    async def initialize(self) -> None:
        """Initialize cache connection."""
        try:
            self._redis = await get_redis_client()
            if await self._redis.ping():
                self._enabled = True
                settings = get_settings()
                # Read TTLs from config if available
                self._embedding_ttl = getattr(
                    settings, "cache_embedding_ttl", self._embedding_ttl
                )
                self._search_ttl = getattr(
                    settings, "cache_search_ttl", self._search_ttl
                )
                self._answer_ttl = getattr(
                    settings, "cache_answer_ttl", self._answer_ttl
                )
                _log.info("Cache service initialized (Redis-backed)")
            else:
                _log.warning("Redis not available - caching disabled")
        except Exception as e:
            _log.warning("Cache service disabled due to Redis error: %s", e)
            self._enabled = False

    def _hash_key(self, *parts: Any) -> str:
        """Create deterministic hash key from parts."""
        combined = "|".join(str(p) for p in parts)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _embedding_key(self, model: str, text: str) -> str:
        h = self._hash_key(model, text)
        return f"rag:embed:{model}:{h}"

    def _search_key(
        self,
        collection: str,
        embedding_model: str,
        top_k: int,
        score_threshold: float,
        use_hybrid: bool,
        query_hash: str,
    ) -> str:
        h = self._hash_key(
            collection, embedding_model, top_k, score_threshold, use_hybrid, query_hash
        )
        return f"rag:search:{collection}:{h}"

    def _answer_key(
        self,
        collection: str,
        chat_model: str,
        system_prompt: str,
        question: str,
        temperature: float,
        top_k: int,
        use_reranker: bool,
        use_hybrid: bool,
    ) -> str:
        h = self._hash_key(
            collection,
            chat_model,
            round(temperature, 2),
            top_k,
            use_reranker,
            use_hybrid,
            self._hash_key(system_prompt),
            question.strip().lower(),
        )
        return f"rag:answer:{collection}:{h}"

    async def get_embedding(self, model: str, text: str) -> list[float] | None:
        """Get cached embedding vector."""
        if not self._enabled or not self._redis:
            return None
        try:
            key = self._embedding_key(model, text)
            data = await self._redis.get(key)
            if data:
                if isinstance(data, str):
                    return json.loads(data)
                return data
        except Exception as e:
            _log.warning("Cache get embedding error: %s", e)
        return None

    async def set_embedding(
        self, model: str, text: str, embedding: list[float]
    ) -> None:
        """Cache embedding vector."""
        if not self._enabled or not self._redis:
            return
        try:
            key = self._embedding_key(model, text)
            await self._redis.set(key, json.dumps(embedding), ttl=self._embedding_ttl)
        except Exception as e:
            _log.warning("Cache set embedding error: %s", e)

    async def get_search_results(
        self,
        collection: str,
        embedding_model: str,
        top_k: int,
        score_threshold: float,
        use_hybrid: bool,
        query_hash: str,
    ) -> list[dict] | None:
        """Get cached search results (chunks from Qdrant)."""
        if not self._enabled or not self._redis:
            return None
        try:
            key = self._search_key(
                collection,
                embedding_model,
                top_k,
                score_threshold,
                use_hybrid,
                query_hash,
            )
            data = await self._redis.get(key)
            if data:
                if isinstance(data, str):
                    return json.loads(data)
                return data
        except Exception as e:
            _log.warning("Cache get search error: %s", e)
        return None

    async def set_search_results(
        self,
        collection: str,
        embedding_model: str,
        top_k: int,
        score_threshold: float,
        use_hybrid: bool,
        query_hash: str,
        results: list[dict],
    ) -> None:
        """Cache search results."""
        if not self._enabled or not self._redis:
            return
        try:
            key = self._search_key(
                collection,
                embedding_model,
                top_k,
                score_threshold,
                use_hybrid,
                query_hash,
            )
            await self._redis.set(key, json.dumps(results), ttl=self._search_ttl)
        except Exception as e:
            _log.warning("Cache set search error: %s", e)

    async def get_answer(
        self,
        collection: str,
        chat_model: str,
        system_prompt: str,
        question: str,
        temperature: float,
        top_k: int,
        use_reranker: bool,
        use_hybrid: bool,
    ) -> dict | None:
        """Get cached RAG answer."""
        if not self._enabled or not self._redis:
            return None
        try:
            key = self._answer_key(
                collection,
                chat_model,
                system_prompt,
                question,
                temperature,
                top_k,
                use_reranker,
                use_hybrid,
            )
            data = await self._redis.get(key)
            if data:
                if isinstance(data, str):
                    return json.loads(data)
                return data
        except Exception as e:
            _log.warning("Cache get answer error: %s", e)
        return None

    async def set_answer(
        self,
        collection: str,
        chat_model: str,
        system_prompt: str,
        question: str,
        temperature: float,
        top_k: int,
        use_reranker: bool,
        use_hybrid: bool,
        answer: dict,
    ) -> None:
        """Cache RAG answer."""
        if not self._enabled or not self._redis:
            return
        try:
            key = self._answer_key(
                collection,
                chat_model,
                system_prompt,
                question,
                temperature,
                top_k,
                use_reranker,
                use_hybrid,
            )
            await self._redis.set(key, json.dumps(answer), ttl=self._answer_ttl)
        except Exception as e:
            _log.warning("Cache set answer error: %s", e)

    async def invalidate_collection(self, collection: str) -> int:
        """Invalidate all cached data for a knowledge base (collection)."""
        if not self._enabled or not self._redis:
            return 0
        try:
            pattern = f"rag:*:{collection}:*"
            return await self._redis.clear_pattern(pattern)
        except Exception as e:
            _log.warning("Cache invalidate error: %s", e)
            return 0


# Singleton instance
_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
    """Get or create cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


async def init_cache() -> None:
    """Initialize cache service (call on startup)."""
    service = get_cache_service()
    await service.initialize()


async def close_cache() -> None:
    """Close cache service (call on shutdown)."""
    global _cache_service
    if _cache_service:
        _cache_service = None  # Redis singleton managed separately
