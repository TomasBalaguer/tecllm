"""Pydantic schemas for tenant-related operations."""
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


# ============== Tenant Schemas ==============

class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Universidad XYZ",
                "slug": "universidad-xyz",
                "description": "Tenant para Universidad XYZ",
            }
        }


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    """Schema for tenant response."""

    id: UUID
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    """Schema for listing tenants."""

    tenants: list[TenantResponse]
    total: int


# ============== API Key Schemas ==============

class APIKeyCreate(BaseModel):
    """Schema for creating a new API key."""

    name: str = Field(default="default", max_length=100)
    expires_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "production",
                "expires_at": None,
            }
        }


class APIKeyResponse(BaseModel):
    """Schema for API key response (without the full key)."""

    id: UUID
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeyCreatedResponse(BaseModel):
    """
    Schema for newly created API key.
    Includes the full key - ONLY shown once!
    """

    id: UUID
    name: str
    key_prefix: str
    api_key: str  # Full key - show only once!
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    warning: str = "Save this API key - it won't be shown again!"


class APIKeyListResponse(BaseModel):
    """Schema for listing API keys."""

    api_keys: list[APIKeyResponse]
    total: int


# ============== Prompt Schemas ==============

class TenantPromptCreate(BaseModel):
    """Schema for creating a tenant prompt."""

    prompt_type: str = Field(..., pattern=r"^(system|evaluation|summary)$")
    name: str = Field(default="default", max_length=100)
    content: str = Field(..., min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "prompt_type": "system",
                "name": "default",
                "content": "Eres un evaluador experto en competencias blandas...",
            }
        }


class TenantPromptUpdate(BaseModel):
    """Schema for updating a tenant prompt."""

    name: Optional[str] = Field(None, max_length=100)
    content: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class TenantPromptResponse(BaseModel):
    """Schema for tenant prompt response."""

    id: UUID
    tenant_id: UUID
    prompt_type: str
    name: str
    content: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantPromptListResponse(BaseModel):
    """Schema for listing tenant prompts."""

    prompts: list[TenantPromptResponse]
    total: int


# ============== Assistant Schemas ==============


class AssistantCreate(BaseModel):
    """Schema for creating an assistant."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None
    system_prompt: str = Field(..., min_length=1)
    evaluation_prompt: Optional[str] = None
    model: str = Field(default="claude-sonnet-4-20250514")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Evaluador de Liderazgo",
                "slug": "evaluador-liderazgo",
                "description": "Evalúa competencias de liderazgo usando metodología STAR",
                "system_prompt": "Eres un evaluador experto en competencias de liderazgo...",
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.0,
            }
        }


class AssistantUpdate(BaseModel):
    """Schema for updating an assistant."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=1)
    evaluation_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_active: Optional[bool] = None


class AssistantResponse(BaseModel):
    """Schema for assistant response."""

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    description: Optional[str]
    system_prompt: str
    evaluation_prompt: Optional[str]
    model: str
    temperature: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssistantListResponse(BaseModel):
    """Schema for listing assistants."""

    assistants: list[AssistantResponse]
    total: int
