"""Health check endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.db.redis import get_redis
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """Simple health check."""
    return {"status": "healthy"}


@router.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
):
    """
    Detailed health check including database and Redis status.
    """
    health_status = {
        "status": "healthy",
        "services": {
            "database": "unknown",
            "redis": "unknown",
            "pinecone": "unknown",
        },
    }

    # Check database
    try:
        await db.execute("SELECT 1")
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check Redis
    try:
        redis = await get_redis()
        await redis.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check Pinecone (basic - just verify config exists)
    if settings.pinecone_api_key:
        health_status["services"]["pinecone"] = "configured"
    else:
        health_status["services"]["pinecone"] = "not configured"

    return health_status
