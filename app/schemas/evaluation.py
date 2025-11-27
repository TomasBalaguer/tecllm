"""Pydantic schemas for API requests/responses."""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from uuid import UUID


class QueryRequest(BaseModel):
    """Schema for a query request - generic and flexible."""

    assistant_id: Optional[UUID] = Field(
        None,
        description="ID of the assistant to use. If not provided, uses tenant default.",
    )
    assistant_slug: Optional[str] = Field(
        None,
        description="Slug of the assistant to use (alternative to assistant_id)",
    )

    # The actual message/query - can be any structure the client needs
    message: Any = Field(
        ...,
        description="The message/query to process. Can be a string or structured data (JSON object)."
    )

    # Optional instructions to include in the prompt (in addition to assistant's system prompt)
    instructions: Optional[str] = Field(
        None,
        description="Additional instructions for this specific query (e.g., response format)"
    )

    # Search configuration
    search_query: Optional[str] = Field(
        None,
        description="Custom query for knowledge base search. If not provided, uses 'message' content."
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of knowledge base chunks to retrieve"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "assistant_slug": "evaluador-liderazgo",
                "message": {
                    "questions": [
                        {
                            "question": "Describe una situación de liderazgo",
                            "response": "En mi trabajo anterior...",
                            "prosody": {
                                "confidence_score": 78.0,
                                "tone": "confident"
                            }
                        }
                    ]
                },
                "instructions": "Evalúa las respuestas y devuelve JSON con score 1-5, feedback, y recomendaciones.",
                "top_k": 5
            }
        }


class QueryResponse(BaseModel):
    """Schema for query response."""

    query_id: str = Field(..., description="Unique identifier for this query")
    tenant_id: UUID = Field(..., description="Tenant that processed the query")
    assistant_id: Optional[UUID] = Field(None, description="Assistant used (if any)")
    assistant_name: Optional[str] = Field(None, description="Assistant name (if any)")

    # The LLM response - can be any structure
    response: Any = Field(..., description="The assistant's response (string or parsed JSON)")

    # Metadata
    knowledge_chunks_used: int = Field(..., description="Number of knowledge base chunks used")
    cached: bool = Field(default=False, description="Whether response was served from cache")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "query_id": "q-abc123",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                "assistant_id": "660e8400-e29b-41d4-a716-446655440000",
                "assistant_name": "Evaluador de Liderazgo",
                "response": {
                    "score": 4.2,
                    "level": "Alto",
                    "feedback": "Excelente demostración de liderazgo...",
                    "recommendations": ["Mejorar delegación"]
                },
                "knowledge_chunks_used": 5,
                "cached": False,
                "processing_time_ms": 1234
            }
        }


class QueryError(BaseModel):
    """Schema for query errors."""

    error: str
    detail: Optional[str] = None
    query_id: Optional[str] = None
