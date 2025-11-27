"""
RAG (Retrieval Augmented Generation) service.
Generic service that works with any type of query - not specific to evaluations.
"""
import time
import json
import hashlib
from uuid import uuid4
from typing import Any, Optional

from app.models.tenant import Tenant, Assistant
from app.services.vector_store import get_vector_store
from app.services.llm_service import get_llm_service
from app.services.cache_service import get_cache_service


class RAGService:
    """
    Main RAG service that orchestrates:
    1. Cache lookup
    2. Context retrieval from Pinecone
    3. LLM query with Claude
    4. Result caching
    """

    def __init__(self):
        self.vector_store = get_vector_store()
        self.llm_service = get_llm_service()
        self.cache_service = get_cache_service()

    async def query(
        self,
        tenant: Tenant,
        message: Any,
        instructions: Optional[str] = None,
        search_query: Optional[str] = None,
        top_k: int = 5,
        assistant: Optional[Assistant] = None,
    ) -> dict:
        """
        Process a query with RAG.

        Args:
            tenant: The tenant making the request
            message: The message/query (string or structured data)
            instructions: Additional instructions for the LLM
            search_query: Custom query for knowledge base search
            top_k: Number of chunks to retrieve
            assistant: The assistant to use (optional)

        Returns:
            Query result with response and metadata
        """
        start_time = time.time()
        query_id = str(uuid4())

        # Build cache key
        message_str = json.dumps(message, sort_keys=True) if isinstance(message, (dict, list)) else str(message)
        assistant_id = str(assistant.id) if assistant else "default"
        cache_suffix = f":{assistant_id}"

        # Create cache key from message hash
        content_hash = hashlib.sha256(message_str.encode()).hexdigest()[:32]

        # Check cache
        cached = await self.cache_service.get_cached_result(
            tenant_id=str(tenant.id),
            content_hash=content_hash,
            cache_key_suffix=cache_suffix,
        )

        if cached:
            cached["cached"] = True
            cached["query_id"] = query_id
            cached["processing_time_ms"] = int((time.time() - start_time) * 1000)
            return cached

        # Determine search query for knowledge base
        if search_query:
            kb_query = search_query
        elif isinstance(message, str):
            kb_query = message[:500]  # Use first 500 chars
        else:
            # For structured data, try to extract meaningful text
            kb_query = self._extract_search_text(message)

        # Retrieve context from knowledge base
        rag_chunks = await self.vector_store.search(
            tenant_slug=tenant.slug,
            query=kb_query,
            top_k=top_k,
        )

        # Get system prompt from assistant
        system_prompt = assistant.system_prompt if assistant else None

        # Combine assistant's instructions with request instructions
        final_instructions = instructions
        if assistant and assistant.evaluation_prompt:
            # evaluation_prompt is used as additional instructions template
            if instructions:
                final_instructions = f"{assistant.evaluation_prompt}\n\n{instructions}"
            else:
                final_instructions = assistant.evaluation_prompt

        # Call LLM
        llm_result = await self.llm_service.query(
            message=message,
            rag_chunks=rag_chunks,
            instructions=final_instructions,
            system_prompt=system_prompt,
            model=assistant.model if assistant else None,
            temperature=assistant.temperature if assistant else None,
        )

        # Build result
        result = {
            "query_id": query_id,
            "tenant_id": str(tenant.id),
            "assistant_id": str(assistant.id) if assistant else None,
            "assistant_name": assistant.name if assistant else None,
            "response": llm_result["response"],
            "knowledge_chunks_used": len(rag_chunks),
            "chunks_ids": [chunk.id for chunk in rag_chunks],
            "cached": False,
            "processing_time_ms": int((time.time() - start_time) * 1000),
        }

        # Cache result
        await self.cache_service.cache_result(
            tenant_id=str(tenant.id),
            content_hash=content_hash,
            result=result,
            cache_key_suffix=cache_suffix,
        )

        return result

    def _extract_search_text(self, data: Any, max_length: int = 500) -> str:
        """Extract text from structured data for knowledge base search."""
        if isinstance(data, str):
            return data[:max_length]

        text_parts = []

        if isinstance(data, dict):
            # Look for common text fields
            for key in ["query", "question", "text", "content", "message", "search"]:
                if key in data and isinstance(data[key], str):
                    text_parts.append(data[key])

            # Also check nested structures like questions array
            if "questions" in data and isinstance(data["questions"], list):
                for q in data["questions"][:3]:  # First 3 questions
                    if isinstance(q, dict):
                        if "question" in q:
                            text_parts.append(q["question"])

        elif isinstance(data, list):
            for item in data[:3]:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict) and "question" in item:
                    text_parts.append(item["question"])

        result = " ".join(text_parts)
        return result[:max_length] if result else "general query"

    async def search_knowledge(
        self,
        tenant: Tenant,
        query: str,
        top_k: int = 5,
    ) -> dict:
        """
        Search knowledge base without LLM processing.
        Useful for debugging or previewing context.

        Args:
            tenant: The tenant
            query: Search query
            top_k: Number of results

        Returns:
            Dict with search results
        """
        chunks = await self.vector_store.search(
            tenant_slug=tenant.slug,
            query=query,
            top_k=top_k,
        )

        return {
            "query": query,
            "tenant_slug": tenant.slug,
            "results": [
                {
                    "id": chunk.id,
                    "content": chunk.content,
                    "score": chunk.score,
                    "metadata": chunk.metadata,
                }
                for chunk in chunks
            ],
            "total": len(chunks),
        }


# Singleton instance
_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    """Get the singleton RAG service instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
