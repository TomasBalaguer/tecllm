"""
Admin API router for tenant and API key management.
Protected by admin secret header.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from datetime import datetime
from uuid import UUID

from app.deps import get_db, verify_admin_secret
from app.models.tenant import Tenant, APIKey, TenantPrompt, Assistant
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListResponse,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyCreatedResponse,
    APIKeyListResponse,
    TenantPromptCreate,
    TenantPromptUpdate,
    TenantPromptResponse,
    TenantPromptListResponse,
    AssistantCreate,
    AssistantUpdate,
    AssistantResponse,
    AssistantListResponse,
)
from app.core.security import generate_api_key

router = APIRouter()


# ============== Tenant Endpoints ==============


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """Create a new tenant."""
    # Check if slug already exists
    stmt = select(Tenant).where(Tenant.slug == tenant_data.slug)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with slug '{tenant_data.slug}' already exists",
        )

    tenant = Tenant(**tenant_data.model_dump())
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    return tenant


@router.get("/tenants", response_model=TenantListResponse)
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """List all tenants."""
    stmt = select(Tenant).offset(skip).limit(limit)
    result = await db.execute(stmt)
    tenants = result.scalars().all()

    count_stmt = select(Tenant)
    count_result = await db.execute(count_stmt)
    total = len(count_result.scalars().all())

    return TenantListResponse(tenants=tenants, total=total)


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """Get a specific tenant by ID."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return tenant


@router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    tenant_data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """Update a tenant."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    update_data = tenant_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tenant, key, value)

    tenant.updated_at = datetime.utcnow()
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    return tenant


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """Delete a tenant and all associated data."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # TODO: Also delete data from Pinecone namespace

    await db.delete(tenant)
    await db.commit()


# ============== API Key Endpoints ==============


@router.post(
    "/tenants/{tenant_id}/api-keys",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    tenant_id: UUID,
    key_data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """
    Create a new API key for a tenant.
    The full API key is returned ONLY in this response - save it!
    """
    # Verify tenant exists
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Generate API key
    full_key, key_prefix, key_hash = generate_api_key()

    api_key = APIKey(
        tenant_id=tenant_id,
        name=key_data.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        expires_at=key_data.expires_at,
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return APIKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        api_key=full_key,  # Only time we return the full key!
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
    )


@router.get("/tenants/{tenant_id}/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """List all API keys for a tenant."""
    stmt = select(APIKey).where(APIKey.tenant_id == tenant_id)
    result = await db.execute(stmt)
    api_keys = result.scalars().all()

    return APIKeyListResponse(api_keys=api_keys, total=len(api_keys))


@router.delete("/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    api_key_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """Revoke (deactivate) an API key."""
    stmt = select(APIKey).where(APIKey.id == api_key_id)
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    api_key.is_active = False
    db.add(api_key)
    await db.commit()


# ============== Prompt Endpoints ==============


@router.post(
    "/tenants/{tenant_id}/prompts",
    response_model=TenantPromptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt(
    tenant_id: UUID,
    prompt_data: TenantPromptCreate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """Create a custom prompt for a tenant."""
    # Verify tenant exists
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    prompt = TenantPrompt(tenant_id=tenant_id, **prompt_data.model_dump())
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)

    return prompt


@router.get("/tenants/{tenant_id}/prompts", response_model=TenantPromptListResponse)
async def list_prompts(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """List all prompts for a tenant."""
    stmt = select(TenantPrompt).where(TenantPrompt.tenant_id == tenant_id)
    result = await db.execute(stmt)
    prompts = result.scalars().all()

    return TenantPromptListResponse(prompts=prompts, total=len(prompts))


@router.patch("/prompts/{prompt_id}", response_model=TenantPromptResponse)
async def update_prompt(
    prompt_id: UUID,
    prompt_data: TenantPromptUpdate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """Update a tenant prompt."""
    stmt = select(TenantPrompt).where(TenantPrompt.id == prompt_id)
    result = await db.execute(stmt)
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )

    update_data = prompt_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prompt, key, value)

    prompt.updated_at = datetime.utcnow()
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)

    return prompt


@router.delete("/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """Delete a tenant prompt."""
    stmt = select(TenantPrompt).where(TenantPrompt.id == prompt_id)
    result = await db.execute(stmt)
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )

    await db.delete(prompt)
    await db.commit()


# ============== Assistant Endpoints ==============


@router.post(
    "/tenants/{tenant_id}/assistants",
    response_model=AssistantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assistant(
    tenant_id: UUID,
    assistant_data: AssistantCreate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """Create a new assistant for a tenant."""
    # Verify tenant exists
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Check if slug already exists for this tenant
    slug_stmt = select(Assistant).where(
        Assistant.tenant_id == tenant_id,
        Assistant.slug == assistant_data.slug,
    )
    slug_result = await db.execute(slug_stmt)
    if slug_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assistant with slug '{assistant_data.slug}' already exists for this tenant",
        )

    assistant = Assistant(tenant_id=tenant_id, **assistant_data.model_dump())
    db.add(assistant)
    await db.commit()
    await db.refresh(assistant)

    return assistant


@router.get("/tenants/{tenant_id}/assistants", response_model=AssistantListResponse)
async def list_assistants(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """List all assistants for a tenant."""
    stmt = select(Assistant).where(Assistant.tenant_id == tenant_id)
    result = await db.execute(stmt)
    assistants = result.scalars().all()

    return AssistantListResponse(assistants=assistants, total=len(assistants))


@router.get("/assistants/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(
    assistant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """Get a specific assistant by ID."""
    stmt = select(Assistant).where(Assistant.id == assistant_id)
    result = await db.execute(stmt)
    assistant = result.scalar_one_or_none()

    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant not found",
        )

    return assistant


@router.patch("/assistants/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(
    assistant_id: UUID,
    assistant_data: AssistantUpdate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """Update an assistant."""
    stmt = select(Assistant).where(Assistant.id == assistant_id)
    result = await db.execute(stmt)
    assistant = result.scalar_one_or_none()

    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant not found",
        )

    update_data = assistant_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(assistant, key, value)

    assistant.updated_at = datetime.utcnow()
    db.add(assistant)
    await db.commit()
    await db.refresh(assistant)

    return assistant


@router.delete("/assistants/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assistant(
    assistant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """Delete an assistant."""
    stmt = select(Assistant).where(Assistant.id == assistant_id)
    result = await db.execute(stmt)
    assistant = result.scalar_one_or_none()

    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant not found",
        )

    await db.delete(assistant)
    await db.commit()
