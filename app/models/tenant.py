from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional


class Tenant(SQLModel, table=True):
    """
    A tenant represents a client organization (e.g., Reskilling, BCIE).
    Each tenant has isolated data in Pinecone (via namespace) and their own assistants.
    """

    __tablename__ = "tenants"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)  # Used as Pinecone namespace
    description: str | None = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    api_keys: list["APIKey"] = Relationship(back_populates="tenant")
    prompts: list["TenantPrompt"] = Relationship(back_populates="tenant")
    documents: list["Document"] = Relationship(back_populates="tenant")
    assistants: list["Assistant"] = Relationship(back_populates="tenant")

    @property
    def pinecone_namespace(self) -> str:
        """Get the Pinecone namespace for this tenant."""
        return f"tenant_{self.slug}"


class APIKey(SQLModel, table=True):
    """
    API keys for tenant authentication.
    The full key is never stored - only prefix (for lookup) and hash (for verification).
    """

    __tablename__ = "api_keys"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    name: str = Field(default="default")  # e.g., "production", "development"

    # Key storage - prefix for lookup, hash for verification
    key_prefix: str = Field(index=True)  # First 8 chars: "sk_abc12"
    key_hash: str  # SHA-256 hash of full key

    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime | None = None
    expires_at: datetime | None = None

    # Relationship
    tenant: Tenant = Relationship(back_populates="api_keys")


class TenantPrompt(SQLModel, table=True):
    """
    Custom prompts per tenant.
    Allows each tenant to customize the evaluation behavior.
    """

    __tablename__ = "tenant_prompts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)

    prompt_type: str = Field(index=True)  # "system", "evaluation", "summary"
    name: str = Field(default="default")
    content: str  # The actual prompt text
    is_active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    tenant: Tenant = Relationship(back_populates="prompts")


class Document(SQLModel, table=True):
    """
    Metadata for documents uploaded to the knowledge base.
    Actual content is stored in Pinecone as vectors.
    """

    __tablename__ = "documents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)

    title: str
    document_type: str  # "competency", "rubric", "example", "methodology"
    filename: str | None = None
    source: str | None = None  # Original source/URL if applicable

    # Processing info
    chunks_count: int = Field(default=0)
    status: str = Field(default="pending")  # "pending", "processing", "completed", "failed"
    error_message: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    tenant: Tenant = Relationship(back_populates="documents")


class Assistant(SQLModel, table=True):
    """
    An assistant within a tenant.
    Each assistant has its own system prompt/instructions but shares the tenant's knowledge base.
    Examples: "Evaluador de Liderazgo", "Coach de Comunicación", "Entrevistador Técnico"
    """

    __tablename__ = "assistants"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)

    name: str = Field(index=True)  # "Evaluador de Liderazgo"
    slug: str = Field(index=True)  # "evaluador-liderazgo" (unique per tenant)
    description: str | None = None

    # Assistant's instructions/personality
    system_prompt: str  # The main instructions for this assistant

    # Optional: specific evaluation prompt (if different from default)
    evaluation_prompt: str | None = None

    # Configuration
    model: str = Field(default="claude-sonnet-4-20250514")
    temperature: float = Field(default=0.0)  # 0 for consistency

    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    tenant: Tenant = Relationship(back_populates="assistants")
