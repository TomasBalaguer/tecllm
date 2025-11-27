"""
Admin panel web routes using Jinja2 templates.
Simple web UI for managing tenants and documents.
"""
from fastapi import APIRouter, Request, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID
from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.deps import get_db
from app.models.tenant import Tenant, APIKey, TenantPrompt, Document, Assistant, QueryLog
from app.core.security import generate_api_key
from app.services.document_processor import get_document_processor
from app.services.vector_store import get_vector_store
from app.services.rag_service import get_rag_service
import json as json_module

settings = get_settings()
router = APIRouter()

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Simple session tracking (in production, use proper session management)
_authenticated_sessions = set()


def check_admin_auth(request: Request) -> bool:
    """Check if the request is authenticated as admin."""
    session_id = request.cookies.get("admin_session")
    if not session_id or session_id not in _authenticated_sessions:
        return False
    return True


# ============== Auth Routes ==============


@router.get("/", response_class=HTMLResponse)
async def admin_root(request: Request):
    """Admin root - redirect to dashboard or login."""
    if check_admin_auth(request):
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Admin login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(request: Request, password: str = Form(...)):
    """Process admin login."""
    if password == settings.admin_secret:
        import secrets
        session_id = secrets.token_urlsafe(32)
        _authenticated_sessions.add(session_id)

        response = RedirectResponse(url="/admin/dashboard", status_code=303)
        response.set_cookie(key="admin_session", value=session_id, httponly=True)
        return response

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Contraseña incorrecta"},
    )


@router.get("/logout")
async def logout(request: Request):
    """Admin logout."""
    session_id = request.cookies.get("admin_session")
    if session_id:
        _authenticated_sessions.discard(session_id)

    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("admin_session")
    return response


# ============== Dashboard ==============


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Admin dashboard."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    # Get stats
    tenants_result = await db.execute(select(Tenant))
    tenants = tenants_result.scalars().all()

    docs_result = await db.execute(select(Document))
    documents = docs_result.scalars().all()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "tenants_count": len(tenants),
            "documents_count": len(documents),
            "active_tenants": len([t for t in tenants if t.is_active]),
        },
    )


# ============== Tenants ==============


@router.get("/tenants", response_class=HTMLResponse)
async def list_tenants(request: Request, db: AsyncSession = Depends(get_db)):
    """List all tenants."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = result.scalars().all()

    return templates.TemplateResponse(
        "tenants.html",
        {"request": request, "tenants": tenants},
    )


@router.get("/tenants/new", response_class=HTMLResponse)
async def new_tenant_form(request: Request):
    """Form to create a new tenant."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    return templates.TemplateResponse("tenant_new.html", {"request": request})


@router.post("/tenants/new")
async def create_tenant(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    description: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Create a new tenant."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    # Check slug uniqueness
    existing = await db.execute(select(Tenant).where(Tenant.slug == slug))
    if existing.scalar_one_or_none():
        return templates.TemplateResponse(
            "tenant_new.html",
            {"request": request, "error": f"El slug '{slug}' ya existe"},
        )

    tenant = Tenant(name=name, slug=slug, description=description)
    db.add(tenant)
    await db.commit()

    return RedirectResponse(url=f"/admin/tenants/{tenant.id}", status_code=303)


@router.get("/tenants/{tenant_id}", response_class=HTMLResponse)
async def tenant_detail(
    request: Request,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Tenant detail page."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    # Get API keys
    keys_result = await db.execute(
        select(APIKey).where(APIKey.tenant_id == tenant_id)
    )
    api_keys = keys_result.scalars().all()

    # Get prompts
    prompts_result = await db.execute(
        select(TenantPrompt).where(TenantPrompt.tenant_id == tenant_id)
    )
    prompts = prompts_result.scalars().all()

    # Get documents
    docs_result = await db.execute(
        select(Document).where(Document.tenant_id == tenant_id)
    )
    documents = docs_result.scalars().all()

    # Get assistants
    assistants_result = await db.execute(
        select(Assistant).where(Assistant.tenant_id == tenant_id)
    )
    assistants = assistants_result.scalars().all()

    return templates.TemplateResponse(
        "tenant_detail.html",
        {
            "request": request,
            "tenant": tenant,
            "api_keys": api_keys,
            "prompts": prompts,
            "documents": documents,
            "assistants": assistants,
        },
    )


@router.post("/tenants/{tenant_id}/api-keys")
async def create_api_key_web(
    request: Request,
    tenant_id: UUID,
    name: str = Form(default="default"),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key for a tenant."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    full_key, key_prefix, key_hash = generate_api_key()

    api_key = APIKey(
        tenant_id=tenant_id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
    )
    db.add(api_key)
    await db.commit()

    # Redirect with the new key shown (one time only!)
    return templates.TemplateResponse(
        "api_key_created.html",
        {
            "request": request,
            "tenant_id": tenant_id,
            "api_key": full_key,
            "key_name": name,
        },
    )


@router.post("/tenants/{tenant_id}/toggle")
async def toggle_tenant(
    tenant_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Toggle tenant active status."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if tenant:
        tenant.is_active = not tenant.is_active
        tenant.updated_at = datetime.utcnow()
        db.add(tenant)
        await db.commit()

    return RedirectResponse(url=f"/admin/tenants/{tenant_id}", status_code=303)


# ============== Documents ==============


@router.get("/tenants/{tenant_id}/documents/upload", response_class=HTMLResponse)
async def upload_document_form(
    request: Request,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Document upload form."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    return templates.TemplateResponse(
        "document_upload.html",
        {"request": request, "tenant": tenant},
    )


@router.post("/tenants/{tenant_id}/documents/upload")
async def upload_document_web(
    request: Request,
    tenant_id: UUID,
    title: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    from uuid import uuid4

    document_id = str(uuid4())
    processor = get_document_processor()
    vector_store = get_vector_store()

    # Create document record
    document = Document(
        id=document_id,
        tenant_id=tenant_id,
        title=title,
        document_type=document_type,
        filename=file.filename,
        status="processing",
    )
    db.add(document)
    await db.commit()

    try:
        content = await file.read()
        chunks = processor.process_file(
            content=content,
            filename=file.filename,
            document_id=document_id,
            metadata={"title": title, "document_type": document_type},
        )

        vector_docs = processor.to_vector_documents(chunks)
        await vector_store.upsert_documents(tenant.slug, vector_docs)

        document.chunks_count = len(chunks)
        document.status = "completed"
        document.updated_at = datetime.utcnow()
        db.add(document)
        await db.commit()

        return templates.TemplateResponse(
            "document_upload.html",
            {
                "request": request,
                "tenant": tenant,
                "success": f"Documento '{title}' procesado. {len(chunks)} chunks creados.",
            },
        )

    except Exception as e:
        document.status = "failed"
        document.error_message = str(e)
        db.add(document)
        await db.commit()

        return templates.TemplateResponse(
            "document_upload.html",
            {
                "request": request,
                "tenant": tenant,
                "error": f"Error al procesar documento: {str(e)}",
            },
        )


@router.post("/tenants/{tenant_id}/documents/{document_id}/delete")
async def delete_document_web(
    request: Request,
    tenant_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its vectors from Pinecone."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    # Get tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    # Get document
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    document = doc_result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Delete vectors from Pinecone if document was processed
    if document.status == "completed" and document.chunks_count > 0:
        try:
            vector_store = get_vector_store()
            # Generate the chunk IDs that were created during processing
            chunk_ids = [f"{document_id}_chunk_{i}" for i in range(document.chunks_count)]
            await vector_store.delete_documents(tenant.slug, chunk_ids)
        except Exception as e:
            # Log but don't fail - document might not have vectors
            print(f"Warning: Could not delete vectors for document {document_id}: {e}")

    # Delete document record from database
    await db.delete(document)
    await db.commit()

    return RedirectResponse(url=f"/admin/tenants/{tenant_id}", status_code=303)


# ============== Assistants ==============


@router.get("/tenants/{tenant_id}/assistants/new", response_class=HTMLResponse)
async def new_assistant_form(
    request: Request,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Form to create a new assistant."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    return templates.TemplateResponse(
        "assistant_new.html",
        {"request": request, "tenant": tenant},
    )


@router.post("/tenants/{tenant_id}/assistants/new")
async def create_assistant_web(
    request: Request,
    tenant_id: UUID,
    name: str = Form(...),
    slug: str = Form(...),
    description: str = Form(None),
    system_prompt: str = Form(...),
    evaluation_prompt: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Create a new assistant."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    # Check slug uniqueness within tenant
    existing = await db.execute(
        select(Assistant).where(
            Assistant.tenant_id == tenant_id,
            Assistant.slug == slug,
        )
    )
    if existing.scalar_one_or_none():
        return templates.TemplateResponse(
            "assistant_new.html",
            {"request": request, "tenant": tenant, "error": f"El slug '{slug}' ya existe para este tenant"},
        )

    assistant = Assistant(
        tenant_id=tenant_id,
        name=name,
        slug=slug,
        description=description,
        system_prompt=system_prompt,
        evaluation_prompt=evaluation_prompt if evaluation_prompt else None,
    )
    db.add(assistant)
    await db.commit()

    return RedirectResponse(url=f"/admin/tenants/{tenant_id}/assistants/{assistant.id}", status_code=303)


@router.get("/tenants/{tenant_id}/assistants/{assistant_id}", response_class=HTMLResponse)
async def assistant_detail(
    request: Request,
    tenant_id: UUID,
    assistant_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Assistant detail page."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    assistant_result = await db.execute(
        select(Assistant).where(Assistant.id == assistant_id)
    )
    assistant = assistant_result.scalar_one_or_none()

    if not assistant:
        raise HTTPException(status_code=404, detail="Asistente no encontrado")

    return templates.TemplateResponse(
        "assistant_detail.html",
        {"request": request, "tenant": tenant, "assistant": assistant},
    )


@router.get("/tenants/{tenant_id}/assistants/{assistant_id}/edit", response_class=HTMLResponse)
async def edit_assistant_form(
    request: Request,
    tenant_id: UUID,
    assistant_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Form to edit an assistant."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    assistant_result = await db.execute(
        select(Assistant).where(Assistant.id == assistant_id)
    )
    assistant = assistant_result.scalar_one_or_none()

    if not tenant or not assistant:
        raise HTTPException(status_code=404, detail="No encontrado")

    return templates.TemplateResponse(
        "assistant_edit.html",
        {"request": request, "tenant": tenant, "assistant": assistant},
    )


@router.post("/tenants/{tenant_id}/assistants/{assistant_id}/edit")
async def update_assistant_web(
    request: Request,
    tenant_id: UUID,
    assistant_id: UUID,
    name: str = Form(...),
    description: str = Form(None),
    system_prompt: str = Form(...),
    evaluation_prompt: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Update an assistant."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    assistant_result = await db.execute(
        select(Assistant).where(Assistant.id == assistant_id)
    )
    assistant = assistant_result.scalar_one_or_none()

    if not assistant:
        raise HTTPException(status_code=404, detail="Asistente no encontrado")

    assistant.name = name
    assistant.description = description
    assistant.system_prompt = system_prompt
    assistant.evaluation_prompt = evaluation_prompt if evaluation_prompt else None
    assistant.updated_at = datetime.utcnow()
    db.add(assistant)
    await db.commit()

    return RedirectResponse(url=f"/admin/tenants/{tenant_id}/assistants/{assistant_id}", status_code=303)


@router.post("/tenants/{tenant_id}/assistants/{assistant_id}/toggle")
async def toggle_assistant(
    request: Request,
    tenant_id: UUID,
    assistant_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Toggle assistant active status."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    result = await db.execute(select(Assistant).where(Assistant.id == assistant_id))
    assistant = result.scalar_one_or_none()

    if assistant:
        assistant.is_active = not assistant.is_active
        assistant.updated_at = datetime.utcnow()
        db.add(assistant)
        await db.commit()

    return RedirectResponse(url=f"/admin/tenants/{tenant_id}/assistants/{assistant_id}", status_code=303)


# ============== Playground ==============


@router.get("/tenants/{tenant_id}/playground", response_class=HTMLResponse)
async def playground_form(
    request: Request,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Playground to test evaluations."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    # Get assistants
    assistants_result = await db.execute(
        select(Assistant).where(Assistant.tenant_id == tenant_id, Assistant.is_active == True)
    )
    assistants = assistants_result.scalars().all()

    # Get documents count
    docs_result = await db.execute(
        select(Document).where(Document.tenant_id == tenant_id, Document.status == "completed")
    )
    documents = docs_result.scalars().all()

    return templates.TemplateResponse(
        "playground.html",
        {
            "request": request,
            "tenant": tenant,
            "assistants": assistants,
            "documents_count": len(documents),
        },
    )


@router.post("/tenants/{tenant_id}/playground", response_class=HTMLResponse)
async def playground_query(
    request: Request,
    tenant_id: UUID,
    json_payload: str = Form(...),
    assistant_id: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Process a playground query with JSON payload - generic, works with any assistant."""
    import json as json_module

    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    # Get assistants for the form
    assistants_result = await db.execute(
        select(Assistant).where(Assistant.tenant_id == tenant_id, Assistant.is_active == True)
    )
    assistants = assistants_result.scalars().all()

    # Get documents count
    docs_result = await db.execute(
        select(Document).where(Document.tenant_id == tenant_id, Document.status == "completed")
    )
    documents = docs_result.scalars().all()

    # Get selected assistant if provided
    selected_assistant = None
    if assistant_id and assistant_id.strip():
        assistant_result = await db.execute(
            select(Assistant).where(Assistant.id == UUID(assistant_id))
        )
        selected_assistant = assistant_result.scalar_one_or_none()

    try:
        # Parse JSON payload - can be any structure
        payload = json_module.loads(json_payload)

        # Extract optional instructions from payload (if provided)
        instructions = payload.pop("_instructions", None)
        search_query = payload.pop("_search_query", None)

        # The rest of the payload is the message
        message = payload

        rag_service = get_rag_service()
        query_result = await rag_service.query(
            tenant=tenant,
            message=message,
            instructions=instructions,
            search_query=search_query,
            assistant=selected_assistant,
        )

        return templates.TemplateResponse(
            "playground.html",
            {
                "request": request,
                "tenant": tenant,
                "assistants": assistants,
                "documents_count": len(documents),
                "result": query_result,
                "json_payload": json_payload,
                "selected_assistant_id": assistant_id,
            },
        )

    except json_module.JSONDecodeError as e:
        return templates.TemplateResponse(
            "playground.html",
            {
                "request": request,
                "tenant": tenant,
                "assistants": assistants,
                "documents_count": len(documents),
                "error": f"JSON inválido: {str(e)}",
                "json_payload": json_payload,
                "selected_assistant_id": assistant_id,
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            "playground.html",
            {
                "request": request,
                "tenant": tenant,
                "assistants": assistants,
                "documents_count": len(documents),
                "error": str(e),
                "json_payload": json_payload,
                "selected_assistant_id": assistant_id,
            },
        )


# ============== Logs ==============


@router.get("/tenants/{tenant_id}/logs", response_class=HTMLResponse)
async def tenant_logs(
    request: Request,
    tenant_id: UUID,
    limit: int = 50,
    offset: int = 0,
    status: str = None,
    assistant_id: str = None,
    db: AsyncSession = Depends(get_db),
):
    """View query logs for a tenant."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    # Get assistants for filter dropdown
    assistants_result = await db.execute(
        select(Assistant).where(Assistant.tenant_id == tenant_id)
    )
    assistants = assistants_result.scalars().all()

    # Build query
    stmt = select(QueryLog).where(QueryLog.tenant_id == tenant_id)

    if status:
        stmt = stmt.where(QueryLog.status == status)

    if assistant_id:
        stmt = stmt.where(QueryLog.assistant_id == UUID(assistant_id))

    # Order by newest first
    stmt = stmt.order_by(QueryLog.created_at.desc())

    # Count total
    count_stmt = select(QueryLog).where(QueryLog.tenant_id == tenant_id)
    if status:
        count_stmt = count_stmt.where(QueryLog.status == status)
    if assistant_id:
        count_stmt = count_stmt.where(QueryLog.assistant_id == UUID(assistant_id))

    count_result = await db.execute(count_stmt)
    total = len(count_result.scalars().all())

    # Apply pagination
    stmt = stmt.offset(offset).limit(limit)
    logs_result = await db.execute(stmt)
    logs = logs_result.scalars().all()

    return templates.TemplateResponse(
        "tenant_logs.html",
        {
            "request": request,
            "tenant": tenant,
            "logs": logs,
            "assistants": assistants,
            "total": total,
            "limit": limit,
            "offset": offset,
            "status_filter": status,
            "assistant_filter": assistant_id,
        },
    )


@router.get("/tenants/{tenant_id}/logs/{query_id}", response_class=HTMLResponse)
async def log_detail(
    request: Request,
    tenant_id: UUID,
    query_id: str,
    db: AsyncSession = Depends(get_db),
):
    """View detail of a specific log."""
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    log_result = await db.execute(
        select(QueryLog).where(
            QueryLog.tenant_id == tenant_id,
            QueryLog.query_id == query_id,
        )
    )
    log = log_result.scalar_one_or_none()

    if not log:
        raise HTTPException(status_code=404, detail="Log no encontrado")

    # Format JSON for display
    try:
        message = json_module.loads(log.message_full) if log.message_full else None
        message_formatted = json_module.dumps(message, indent=2, ensure_ascii=False) if message else log.message_full
    except json_module.JSONDecodeError:
        message_formatted = log.message_full

    try:
        response = json_module.loads(log.response_full) if log.response_full else None
        response_formatted = json_module.dumps(response, indent=2, ensure_ascii=False) if response else log.response_full
    except json_module.JSONDecodeError:
        response_formatted = log.response_full

    return templates.TemplateResponse(
        "log_detail.html",
        {
            "request": request,
            "tenant": tenant,
            "log": log,
            "message_formatted": message_formatted,
            "response_formatted": response_formatted,
        },
    )
