"""
Generic query endpoint for RAG-based assistant queries.
Works with any message structure - the assistant's prompt defines the behavior.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.deps import get_db, get_current_tenant
from app.models.tenant import Tenant, Assistant
from app.schemas.evaluation import QueryRequest, QueryResponse, QueryError
from app.services.rag_service import get_rag_service

router = APIRouter()


async def get_assistant_for_request(
    request: QueryRequest,
    tenant: Tenant,
    db: AsyncSession,
) -> Assistant | None:
    """Get the assistant for a query request."""
    if request.assistant_id:
        stmt = select(Assistant).where(
            Assistant.id == request.assistant_id,
            Assistant.tenant_id == tenant.id,
            Assistant.is_active == True,
        )
        result = await db.execute(stmt)
        assistant = result.scalar_one_or_none()
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assistant with ID '{request.assistant_id}' not found or inactive",
            )
        return assistant

    if request.assistant_slug:
        stmt = select(Assistant).where(
            Assistant.slug == request.assistant_slug,
            Assistant.tenant_id == tenant.id,
            Assistant.is_active == True,
        )
        result = await db.execute(stmt)
        assistant = result.scalar_one_or_none()
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assistant with slug '{request.assistant_slug}' not found or inactive",
            )
        return assistant

    return None


@router.post(
    "/query",
    response_model=QueryResponse,
    responses={
        400: {"model": QueryError},
        401: {"description": "Invalid API key"},
        500: {"model": QueryError},
    },
)
async def query_assistant(
    request: QueryRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a query to an assistant with RAG context.

    This is a generic endpoint that works with any message structure:
    - The message can be a string or structured JSON
    - The assistant's prompt defines how to process and respond
    - Optionally pass instructions to customize the response format

    This endpoint:
    1. Checks cache for identical previous queries (consistency)
    2. Retrieves relevant context from tenant's knowledge base
    3. Uses the assistant's prompts (or defaults) for processing
    4. Uses Claude with temperature=0 (deterministic)
    5. Caches the result for future identical requests

    The query is tenant-isolated:
    - Uses only the tenant's knowledge base
    - Applies assistant's custom prompts
    - Results are cached per tenant + assistant
    """
    # Get assistant if specified
    assistant = await get_assistant_for_request(request, tenant, db)

    rag_service = get_rag_service()

    try:
        result = await rag_service.query(
            tenant=tenant,
            message=request.message,
            instructions=request.instructions,
            search_query=request.search_query,
            top_k=request.top_k,
            assistant=assistant,
        )

        return QueryResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}",
        )


@router.post("/query/search")
async def search_knowledge_base(
    query: str,
    top_k: int = 5,
    tenant: Tenant = Depends(get_current_tenant),
):
    """
    Search the knowledge base without LLM processing.
    Useful for debugging and verifying knowledge base content.
    """
    rag_service = get_rag_service()

    result = await rag_service.search_knowledge(
        tenant=tenant,
        query=query,
        top_k=top_k,
    )

    return result


@router.post("/query/batch")
async def batch_query(
    requests: list[QueryRequest],
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Process multiple queries in a single request.
    Results are processed sequentially to avoid rate limits.

    Note: For large batches, consider implementing a queue-based system.
    """
    if len(requests) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 queries per batch request",
        )

    rag_service = get_rag_service()
    results = []

    for i, request in enumerate(requests):
        try:
            # Get assistant for each request (may be different)
            assistant = await get_assistant_for_request(request, tenant, db)

            result = await rag_service.query(
                tenant=tenant,
                message=request.message,
                instructions=request.instructions,
                search_query=request.search_query,
                top_k=request.top_k,
                assistant=assistant,
            )
            results.append({
                "index": i,
                "status": "success",
                "result": result,
            })
        except Exception as e:
            results.append({
                "index": i,
                "status": "error",
                "error": str(e),
            })

    return {
        "total": len(requests),
        "successful": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "error"]),
        "results": results,
    }


@router.get("/assistants")
async def list_tenant_assistants(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    List all available assistants for the current tenant.
    Useful for clients to discover available assistants.
    """
    stmt = select(Assistant).where(
        Assistant.tenant_id == tenant.id,
        Assistant.is_active == True,
    )
    result = await db.execute(stmt)
    assistants = result.scalars().all()

    return {
        "assistants": [
            {
                "id": str(a.id),
                "slug": a.slug,
                "name": a.name,
                "description": a.description,
            }
            for a in assistants
        ],
        "total": len(assistants),
    }
