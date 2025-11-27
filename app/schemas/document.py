"""Pydantic schemas for document-related operations."""
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


class DocumentCreate(BaseModel):
    """Schema for creating a document via text content."""

    title: str = Field(..., min_length=1, max_length=255)
    document_type: str = Field(
        ...,
        pattern=r"^(competency|rubric|example|methodology)$",
        description="Type of document",
    )
    content: str = Field(..., min_length=1, description="Text content to process")
    source: Optional[str] = Field(None, description="Original source/URL")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Competencia de Liderazgo",
                "document_type": "competency",
                "content": "# Liderazgo\n\nCapacidad de influir, motivar y guiar a otros...",
                "source": "Manual de competencias v2.0",
            }
        }


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""

    id: UUID
    title: str
    document_type: str
    filename: Optional[str]
    chunks_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """Schema for document details response."""

    id: UUID
    tenant_id: UUID
    title: str
    document_type: str
    filename: Optional[str]
    source: Optional[str]
    chunks_count: int
    status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Schema for listing documents."""

    documents: list[DocumentResponse]
    total: int


class DocumentChunk(BaseModel):
    """Schema for a document chunk (for debugging/inspection)."""

    chunk_id: str
    content: str
    metadata: dict
    score: Optional[float] = None  # Similarity score if from search


class DocumentSearchResult(BaseModel):
    """Schema for document search results."""

    chunks: list[DocumentChunk]
    total_found: int
    query: str
