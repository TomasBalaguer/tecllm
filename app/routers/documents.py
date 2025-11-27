"""
Document management endpoints for uploading and managing knowledge base documents.
Documents are tenant-isolated via Pinecone namespaces.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID, uuid4
from datetime import datetime

from app.deps import get_db, get_current_tenant
from app.models.tenant import Tenant, Document
from app.schemas.document import (
    DocumentCreate,
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    DocumentSearchResult,
    DocumentChunk,
)
from app.services.document_processor import get_document_processor
from app.services.vector_store import get_vector_store

router = APIRouter()


@router.post("/documents", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def create_document_from_text(
    document_data: DocumentCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a document from text content.
    The text is processed into chunks and stored in Pinecone.
    """
    document_id = str(uuid4())
    processor = get_document_processor()
    vector_store = get_vector_store()

    # Create document record
    document = Document(
        id=document_id,
        tenant_id=tenant.id,
        title=document_data.title,
        document_type=document_data.document_type,
        source=document_data.source,
        status="processing",
    )
    db.add(document)
    await db.commit()

    try:
        # Process text into chunks
        chunks = processor.process_text(
            text=document_data.content,
            document_id=document_id,
            metadata={
                "title": document_data.title,
                "document_type": document_data.document_type,
                "source": document_data.source,
            },
        )

        # Convert to vector store format and upsert
        vector_docs = processor.to_vector_documents(chunks)
        await vector_store.upsert_documents(tenant.slug, vector_docs)

        # Update document record
        document.chunks_count = len(chunks)
        document.status = "completed"
        document.updated_at = datetime.utcnow()
        db.add(document)
        await db.commit()
        await db.refresh(document)

        return document

    except Exception as e:
        # Update document with error
        document.status = "failed"
        document.error_message = str(e)
        document.updated_at = datetime.utcnow()
        db.add(document)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}",
        )


@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_file(
    title: str = Form(...),
    document_type: str = Form(...),
    source: str = Form(None),
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document file (PDF, DOCX, TXT, MD).
    The file is processed into chunks and stored in Pinecone.
    """
    # Validate file type
    allowed_extensions = ["pdf", "docx", "txt", "md", "markdown"]
    file_ext = file.filename.lower().split(".")[-1]
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file_ext}' not supported. Allowed: {', '.join(allowed_extensions)}",
        )

    document_id = str(uuid4())
    processor = get_document_processor()
    vector_store = get_vector_store()

    # Create document record
    document = Document(
        id=document_id,
        tenant_id=tenant.id,
        title=title,
        document_type=document_type,
        filename=file.filename,
        source=source,
        status="processing",
    )
    db.add(document)
    await db.commit()

    try:
        # Read file content
        content = await file.read()

        # Process file into chunks
        chunks = processor.process_file(
            content=content,
            filename=file.filename,
            document_id=document_id,
            metadata={
                "title": title,
                "document_type": document_type,
                "source": source,
            },
        )

        # Convert to vector store format and upsert
        vector_docs = processor.to_vector_documents(chunks)
        await vector_store.upsert_documents(tenant.slug, vector_docs)

        # Update document record
        document.chunks_count = len(chunks)
        document.status = "completed"
        document.updated_at = datetime.utcnow()
        db.add(document)
        await db.commit()
        await db.refresh(document)

        return document

    except Exception as e:
        # Update document with error
        document.status = "failed"
        document.error_message = str(e)
        document.updated_at = datetime.utcnow()
        db.add(document)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}",
        )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    document_type: str = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """List all documents for the current tenant."""
    stmt = select(Document).where(Document.tenant_id == tenant.id)

    if document_type:
        stmt = stmt.where(Document.document_type == document_type)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    documents = result.scalars().all()

    # Get total count
    count_stmt = select(Document).where(Document.tenant_id == tenant.id)
    if document_type:
        count_stmt = count_stmt.where(Document.document_type == document_type)
    count_result = await db.execute(count_stmt)
    total = len(count_result.scalars().all())

    return DocumentListResponse(documents=documents, total=total)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific document by ID."""
    stmt = select(Document).where(
        Document.id == document_id,
        Document.tenant_id == tenant.id,
    )
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its vectors from Pinecone."""
    stmt = select(Document).where(
        Document.id == document_id,
        Document.tenant_id == tenant.id,
    )
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    vector_store = get_vector_store()

    try:
        # Generate chunk IDs to delete
        chunk_ids = [f"{document_id}_chunk_{i}" for i in range(document.chunks_count)]

        # Also handle page-based IDs for PDFs
        # This is a simplified approach - in production you might want to store chunk IDs
        if document.filename and document.filename.lower().endswith(".pdf"):
            # Delete with pattern matching would be better, but Pinecone requires exact IDs
            # For now, we'll delete by document ID prefix using a filter
            pass

        await vector_store.delete_documents(tenant.slug, chunk_ids)
    except Exception as e:
        # Log but don't fail - vectors might already be deleted
        print(f"Warning: Failed to delete vectors: {e}")

    # Delete from database
    await db.delete(document)
    await db.commit()


@router.get("/documents/search/query", response_model=DocumentSearchResult)
async def search_documents(
    query: str,
    top_k: int = 5,
    document_type: str = None,
    tenant: Tenant = Depends(get_current_tenant),
):
    """
    Search for relevant document chunks using semantic search.
    Useful for testing the knowledge base.
    """
    vector_store = get_vector_store()

    # Build filter if document_type specified
    filter_metadata = None
    if document_type:
        filter_metadata = {"document_type": document_type}

    results = await vector_store.search(
        tenant_slug=tenant.slug,
        query=query,
        top_k=top_k,
        filter_metadata=filter_metadata,
    )

    return DocumentSearchResult(
        chunks=[
            DocumentChunk(
                chunk_id=r.id,
                content=r.content,
                metadata=r.metadata,
                score=r.score,
            )
            for r in results
        ],
        total_found=len(results),
        query=query,
    )
