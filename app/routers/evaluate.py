"""
Generic query endpoint for RAG-based assistant queries.
Works with any message structure - the assistant's prompt defines the behavior.
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID

from app.deps import get_db, get_current_tenant
from app.models.tenant import Tenant, Assistant, QueryLog
from app.schemas.evaluation import QueryRequest, QueryResponse, QueryError
from app.services.rag_service import get_rag_service

router = APIRouter()


def _truncate(text: str, max_length: int = 500) -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


async def _save_query_log(
    db: AsyncSession,
    tenant: Tenant,
    assistant: Optional[Assistant],
    request: QueryRequest,
    result: dict,
    status: str = "success",
    error_message: Optional[str] = None,
):
    """Save a query log entry."""
    # Serialize message
    if isinstance(request.message, (dict, list)):
        message_str = json.dumps(request.message, ensure_ascii=False)
    else:
        message_str = str(request.message)

    # Serialize response
    response = result.get("response", "")
    if isinstance(response, (dict, list)):
        response_str = json.dumps(response, ensure_ascii=False)
    else:
        response_str = str(response)

    log = QueryLog(
        tenant_id=tenant.id,
        assistant_id=assistant.id if assistant else None,
        query_id=result.get("query_id", ""),
        message_preview=_truncate(message_str),
        message_full=message_str,
        search_query=request.search_query,
        top_k=request.top_k,
        response_preview=_truncate(response_str),
        response_full=response_str,
        knowledge_chunks_used=result.get("knowledge_chunks_used", 0),
        cached=result.get("cached", False),
        processing_time_ms=result.get("processing_time_ms", 0),
        status=status,
        error_message=error_message,
    )

    db.add(log)
    await db.commit()


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

        # Save log (don't fail if logging fails)
        try:
            await _save_query_log(db, tenant, assistant, request, result)
        except Exception:
            pass  # Logging failure shouldn't break the response

        return QueryResponse(**result)

    except Exception as e:
        # Try to log the error
        try:
            await _save_query_log(
                db, tenant, assistant, request,
                {"query_id": "error"},
                status="error",
                error_message=str(e)
            )
        except Exception:
            pass

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


@router.get("/logs")
async def list_query_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    assistant_id: Optional[UUID] = Query(default=None),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    List query logs for the current tenant.

    Logs include request/response previews and metadata.
    Use query_id to get full details of a specific log.
    """
    # Build query
    stmt = select(QueryLog).where(QueryLog.tenant_id == tenant.id)

    if status_filter:
        stmt = stmt.where(QueryLog.status == status_filter)

    if assistant_id:
        stmt = stmt.where(QueryLog.assistant_id == assistant_id)

    # Order by newest first
    stmt = stmt.order_by(QueryLog.created_at.desc())

    # Count total
    count_stmt = select(QueryLog).where(QueryLog.tenant_id == tenant.id)
    if status_filter:
        count_stmt = count_stmt.where(QueryLog.status == status_filter)
    if assistant_id:
        count_stmt = count_stmt.where(QueryLog.assistant_id == assistant_id)

    count_result = await db.execute(count_stmt)
    total = len(count_result.scalars().all())

    # Apply pagination
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id": str(log.id),
                "query_id": log.query_id,
                "assistant_id": str(log.assistant_id) if log.assistant_id else None,
                "message_preview": log.message_preview,
                "response_preview": log.response_preview,
                "knowledge_chunks_used": log.knowledge_chunks_used,
                "cached": log.cached,
                "processing_time_ms": log.processing_time_ms,
                "status": log.status,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/logs/{query_id}")
async def get_query_log_detail(
    query_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Get full details of a specific query log.

    Includes complete message and response (not truncated).
    """
    stmt = select(QueryLog).where(
        QueryLog.tenant_id == tenant.id,
        QueryLog.query_id == query_id,
    )
    result = await db.execute(stmt)
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log with query_id '{query_id}' not found",
        )

    # Parse JSON fields if possible
    try:
        message = json.loads(log.message_full) if log.message_full else None
    except json.JSONDecodeError:
        message = log.message_full

    try:
        response = json.loads(log.response_full) if log.response_full else None
    except json.JSONDecodeError:
        response = log.response_full

    return {
        "id": str(log.id),
        "query_id": log.query_id,
        "tenant_id": str(log.tenant_id),
        "assistant_id": str(log.assistant_id) if log.assistant_id else None,
        "message": message,
        "search_query": log.search_query,
        "top_k": log.top_k,
        "response": response,
        "knowledge_chunks_used": log.knowledge_chunks_used,
        "cached": log.cached,
        "processing_time_ms": log.processing_time_ms,
        "status": log.status,
        "error_message": log.error_message,
        "created_at": log.created_at.isoformat(),
    }
