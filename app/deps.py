"""
FastAPI dependencies for authentication and database access.
"""
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from datetime import datetime

from app.db.database import get_session
from app.models.tenant import Tenant, APIKey
from app.core.security import extract_prefix, verify_api_key
from app.config import get_settings

settings = get_settings()


async def get_db() -> AsyncSession:
    """Database session dependency."""
    async for session in get_session():
        yield session


async def get_current_tenant(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """
    Authenticate request and return the associated tenant.

    Extracts API key from header, validates it, and returns the tenant.
    Updates last_used_at timestamp on the API key.

    Raises:
        HTTPException: If API key is invalid, expired, or tenant is inactive
    """
    # Extract prefix for database lookup
    prefix = extract_prefix(x_api_key)
    if not prefix:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Look up API key by prefix
    stmt = (
        select(APIKey)
        .where(APIKey.key_prefix == prefix)
        .where(APIKey.is_active == True)
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify the full key hash
    if not verify_api_key(x_api_key, api_key.key_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if key has expired
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get the tenant
    stmt = select(Tenant).where(Tenant.id == api_key.tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last_used_at (fire and forget - don't wait)
    api_key.last_used_at = datetime.utcnow()
    db.add(api_key)
    await db.commit()

    return tenant


async def verify_admin_secret(
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
) -> bool:
    """
    Verify admin secret for admin-only endpoints.

    Raises:
        HTTPException: If admin secret is invalid
    """
    if x_admin_secret != settings.admin_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin secret",
        )
    return True


# Type alias for cleaner dependency injection
CurrentTenant = Depends(get_current_tenant)
AdminAuth = Depends(verify_admin_secret)
Database = Depends(get_db)
