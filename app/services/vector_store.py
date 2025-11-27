"""
Vector store service using Pinecone with namespace isolation per tenant.
"""
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.config import get_settings
from app.services.embedding_service import get_embedding_service

settings = get_settings()


@dataclass
class SearchResult:
    """Result from a vector search."""

    id: str
    score: float
    content: str
    metadata: Dict[str, Any]


class VectorStoreService:
    """
    Pinecone vector store service with tenant namespace isolation.

    Each tenant's data is stored in a separate namespace within the same index.
    This provides logical isolation while sharing infrastructure.
    """

    def __init__(self):
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name
        self._index = None
        self._embedding_service = get_embedding_service()

    @property
    def index(self):
        """Lazy load the Pinecone index."""
        if self._index is None:
            # Create index if it doesn't exist
            if self.index_name not in self.pc.list_indexes().names():
                self.pc.create_index(
                    name=self.index_name,
                    dimension=settings.embedding_dimensions,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=settings.pinecone_environment,
                    ),
                )
            self._index = self.pc.Index(self.index_name)
        return self._index

    def _get_namespace(self, tenant_slug: str) -> str:
        """Get the namespace for a tenant."""
        return f"tenant_{tenant_slug}"

    async def upsert_documents(
        self,
        tenant_slug: str,
        documents: List[Dict[str, Any]],
    ) -> int:
        """
        Upsert documents to the tenant's namespace.

        Args:
            tenant_slug: The tenant's slug (used as namespace)
            documents: List of dicts with 'id', 'content', and optional 'metadata'

        Returns:
            Number of vectors upserted
        """
        namespace = self._get_namespace(tenant_slug)

        # Extract texts for embedding
        texts = [doc["content"] for doc in documents]

        # Generate embeddings
        embeddings = await self._embedding_service.embed_texts(texts)

        # Prepare vectors for upsert
        vectors = []
        for doc, embedding in zip(documents, embeddings):
            metadata = doc.get("metadata", {})
            metadata["content"] = doc["content"][:1000]  # Store truncated content
            metadata["tenant_slug"] = tenant_slug  # Redundant but useful for debugging

            vectors.append({
                "id": doc["id"],
                "values": embedding,
                "metadata": metadata,
            })

        # Batch upsert (Pinecone recommends batches of 100)
        batch_size = 100
        total_upserted = 0

        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            self.index.upsert(vectors=batch, namespace=namespace)
            total_upserted += len(batch)

        return total_upserted

    async def search(
        self,
        tenant_slug: str,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Search for similar documents in the tenant's namespace.

        Args:
            tenant_slug: The tenant's slug
            query: The search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filter

        Returns:
            List of SearchResult objects
        """
        namespace = self._get_namespace(tenant_slug)

        # Generate query embedding
        query_embedding = await self._embedding_service.embed_text(query)

        # Search in namespace
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=namespace,
            include_metadata=True,
            filter=filter_metadata,
        )

        # Convert to SearchResult objects
        search_results = []
        for match in results.matches:
            search_results.append(
                SearchResult(
                    id=match.id,
                    score=match.score,
                    content=match.metadata.get("content", ""),
                    metadata=match.metadata,
                )
            )

        return search_results

    async def delete_documents(
        self,
        tenant_slug: str,
        document_ids: List[str],
    ) -> int:
        """
        Delete specific documents from the tenant's namespace.

        Args:
            tenant_slug: The tenant's slug
            document_ids: List of document IDs to delete

        Returns:
            Number of documents deleted
        """
        namespace = self._get_namespace(tenant_slug)
        self.index.delete(ids=document_ids, namespace=namespace)
        return len(document_ids)

    async def delete_tenant_data(self, tenant_slug: str) -> bool:
        """
        Delete ALL data for a tenant (entire namespace).
        Use with caution!

        Args:
            tenant_slug: The tenant's slug

        Returns:
            True if successful
        """
        namespace = self._get_namespace(tenant_slug)
        self.index.delete(delete_all=True, namespace=namespace)
        return True

    async def get_namespace_stats(self, tenant_slug: str) -> Dict[str, Any]:
        """
        Get statistics for a tenant's namespace.

        Args:
            tenant_slug: The tenant's slug

        Returns:
            Dict with namespace statistics
        """
        namespace = self._get_namespace(tenant_slug)
        stats = self.index.describe_index_stats()

        namespace_stats = stats.namespaces.get(namespace, {})
        return {
            "namespace": namespace,
            "vector_count": namespace_stats.get("vector_count", 0),
            "total_index_vectors": stats.total_vector_count,
        }


# Singleton instance
_vector_store: VectorStoreService | None = None


def get_vector_store() -> VectorStoreService:
    """Get the singleton vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store
