"""
Tenant portal web routes.
Allows tenants to login and manage their own data (assistants, documents, API keys, logs).
"""
from fastapi import APIRouter, Request, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID
from datetime import datetime
from pathlib import Path
import bcrypt
import secrets
import json as json_module

from app.config import get_settings
from app.deps import get_db
from app.models.tenant import Tenant, APIKey, Document, Assistant, QueryLog
from app.core.security import generate_api_key
from app.services.document_processor import get_document_processor
from app.services.vector_store import get_vector_store
from app.services.rag_service import get_rag_service

settings = get_settings()
router = APIRouter()

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Tenant session tracking: session_id -> tenant_id
_tenant_sessions: dict[str, str] = {}


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def get_tenant_session(request: Request) -> str | None:
    """Get the tenant ID from session cookie."""
    session_id = request.cookies.get("tenant_session")
    if session_id and session_id in _tenant_sessions:
        return _tenant_sessions[session_id]
    return None


async def get_current_tenant(request: Request, db: AsyncSession) -> Tenant | None:
    """Get the current logged-in tenant."""
    tenant_id = get_tenant_session(request)
    if not tenant_id:
        return None

    result = await db.execute(select(Tenant).where(Tenant.id == UUID(tenant_id)))
    return result.scalar_one_or_none()


# ============== Auth Routes ==============


@router.get("/", response_class=HTMLResponse)
async def portal_root(request: Request):
    """Portal root - redirect to dashboard or login."""
    if get_tenant_session(request):
        return RedirectResponse(url="/portal/dashboard", status_code=303)
    return RedirectResponse(url="/portal/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Tenant login page."""
    # If already logged in, redirect to dashboard
    if get_tenant_session(request):
        return RedirectResponse(url="/portal/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Process tenant login."""
    # Find tenant by email
    result = await db.execute(select(Tenant).where(Tenant.email == email))
    tenant = result.scalar_one_or_none()

    if not tenant or not tenant.password_hash:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Email o contraseña incorrectos"},
        )

    if not verify_password(password, tenant.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Email o contraseña incorrectos"},
        )

    if not tenant.is_active:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Tu cuenta está desactivada. Contacta al administrador."},
        )

    # Create session
    session_id = secrets.token_urlsafe(32)
    _tenant_sessions[session_id] = str(tenant.id)

    response = RedirectResponse(url="/portal/dashboard", status_code=303)
    response.set_cookie(key="tenant_session", value=session_id, httponly=True)
    return response


@router.get("/logout")
async def logout(request: Request):
    """Tenant logout."""
    session_id = request.cookies.get("tenant_session")
    if session_id and session_id in _tenant_sessions:
        del _tenant_sessions[session_id]

    response = RedirectResponse(url="/portal/login", status_code=303)
    response.delete_cookie("tenant_session")
    return response


# ============== Dashboard ==============


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Tenant dashboard."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    # Get counts
    docs_result = await db.execute(
        select(Document).where(Document.tenant_id == tenant.id)
    )
    documents = docs_result.scalars().all()

    assistants_result = await db.execute(
        select(Assistant).where(Assistant.tenant_id == tenant.id)
    )
    assistants = assistants_result.scalars().all()

    keys_result = await db.execute(
        select(APIKey).where(APIKey.tenant_id == tenant.id)
    )
    api_keys = keys_result.scalars().all()

    logs_result = await db.execute(
        select(QueryLog).where(QueryLog.tenant_id == tenant.id)
    )
    logs = logs_result.scalars().all()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "tenant": tenant,
            "documents_count": len(documents),
            "assistants_count": len(assistants),
            "api_keys_count": len(api_keys),
            "queries_count": len(logs),
        },
    )


# ============== Assistants ==============


@router.get("/assistants", response_class=HTMLResponse)
async def list_assistants(request: Request, db: AsyncSession = Depends(get_db)):
    """List tenant's assistants."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    result = await db.execute(
        select(Assistant).where(Assistant.tenant_id == tenant.id).order_by(Assistant.created_at.desc())
    )
    assistants = result.scalars().all()

    return templates.TemplateResponse(
        "assistants.html",
        {"request": request, "tenant": tenant, "assistants": assistants},
    )


@router.get("/assistants/new", response_class=HTMLResponse)
async def new_assistant_form(request: Request, db: AsyncSession = Depends(get_db)):
    """Form to create a new assistant."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    return templates.TemplateResponse(
        "assistant_new.html",
        {"request": request, "tenant": tenant},
    )


@router.post("/assistants/new")
async def create_assistant(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    description: str = Form(None),
    system_prompt: str = Form(...),
    evaluation_prompt: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Create a new assistant."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    # Check slug uniqueness within tenant
    existing = await db.execute(
        select(Assistant).where(
            Assistant.tenant_id == tenant.id,
            Assistant.slug == slug,
        )
    )
    if existing.scalar_one_or_none():
        return templates.TemplateResponse(
            "assistant_new.html",
            {"request": request, "tenant": tenant, "error": f"El slug '{slug}' ya existe"},
        )

    assistant = Assistant(
        tenant_id=tenant.id,
        name=name,
        slug=slug,
        description=description,
        system_prompt=system_prompt,
        evaluation_prompt=evaluation_prompt if evaluation_prompt else None,
    )
    db.add(assistant)
    await db.commit()

    return RedirectResponse(url=f"/portal/assistants/{assistant.id}", status_code=303)


@router.get("/assistants/{assistant_id}", response_class=HTMLResponse)
async def assistant_detail(
    request: Request,
    assistant_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Assistant detail page."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    result = await db.execute(
        select(Assistant).where(
            Assistant.id == assistant_id,
            Assistant.tenant_id == tenant.id,
        )
    )
    assistant = result.scalar_one_or_none()

    if not assistant:
        raise HTTPException(status_code=404, detail="Asistente no encontrado")

    return templates.TemplateResponse(
        "assistant_detail.html",
        {"request": request, "tenant": tenant, "assistant": assistant},
    )


@router.get("/assistants/{assistant_id}/edit", response_class=HTMLResponse)
async def edit_assistant_form(
    request: Request,
    assistant_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Form to edit an assistant."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    result = await db.execute(
        select(Assistant).where(
            Assistant.id == assistant_id,
            Assistant.tenant_id == tenant.id,
        )
    )
    assistant = result.scalar_one_or_none()

    if not assistant:
        raise HTTPException(status_code=404, detail="Asistente no encontrado")

    return templates.TemplateResponse(
        "assistant_edit.html",
        {"request": request, "tenant": tenant, "assistant": assistant},
    )


@router.post("/assistants/{assistant_id}/edit")
async def update_assistant(
    request: Request,
    assistant_id: UUID,
    name: str = Form(...),
    description: str = Form(None),
    system_prompt: str = Form(...),
    evaluation_prompt: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Update an assistant."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    result = await db.execute(
        select(Assistant).where(
            Assistant.id == assistant_id,
            Assistant.tenant_id == tenant.id,
        )
    )
    assistant = result.scalar_one_or_none()

    if not assistant:
        raise HTTPException(status_code=404, detail="Asistente no encontrado")

    assistant.name = name
    assistant.description = description
    assistant.system_prompt = system_prompt
    assistant.evaluation_prompt = evaluation_prompt if evaluation_prompt else None
    assistant.updated_at = datetime.utcnow()
    db.add(assistant)
    await db.commit()

    return RedirectResponse(url=f"/portal/assistants/{assistant_id}", status_code=303)


@router.post("/assistants/{assistant_id}/toggle")
async def toggle_assistant(
    request: Request,
    assistant_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Toggle assistant active status."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    result = await db.execute(
        select(Assistant).where(
            Assistant.id == assistant_id,
            Assistant.tenant_id == tenant.id,
        )
    )
    assistant = result.scalar_one_or_none()

    if assistant:
        assistant.is_active = not assistant.is_active
        assistant.updated_at = datetime.utcnow()
        db.add(assistant)
        await db.commit()

    return RedirectResponse(url=f"/portal/assistants/{assistant_id}", status_code=303)


# ============== Documents ==============


@router.get("/documents", response_class=HTMLResponse)
async def list_documents(request: Request, db: AsyncSession = Depends(get_db)):
    """List tenant's documents."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    result = await db.execute(
        select(Document).where(Document.tenant_id == tenant.id).order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()

    return templates.TemplateResponse(
        "documents.html",
        {"request": request, "tenant": tenant, "documents": documents},
    )


@router.get("/documents/upload", response_class=HTMLResponse)
async def upload_document_form(request: Request, db: AsyncSession = Depends(get_db)):
    """Document upload form."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    return templates.TemplateResponse(
        "document_upload.html",
        {"request": request, "tenant": tenant},
    )


@router.post("/documents/upload")
async def upload_document(
    request: Request,
    title: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    from uuid import uuid4

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


@router.post("/documents/{document_id}/delete")
async def delete_document(
    request: Request,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its vectors from Pinecone."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == tenant.id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Delete vectors from Pinecone if document was processed
    if document.status == "completed" and document.chunks_count > 0:
        try:
            vector_store = get_vector_store()
            chunk_ids = [f"{document_id}_chunk_{i}" for i in range(document.chunks_count)]
            await vector_store.delete_documents(tenant.slug, chunk_ids)
        except Exception as e:
            print(f"Warning: Could not delete vectors for document {document_id}: {e}")

    await db.delete(document)
    await db.commit()

    return RedirectResponse(url="/portal/documents", status_code=303)


# ============== API Keys ==============


@router.get("/api-keys", response_class=HTMLResponse)
async def list_api_keys(request: Request, db: AsyncSession = Depends(get_db)):
    """List tenant's API keys."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    result = await db.execute(
        select(APIKey).where(APIKey.tenant_id == tenant.id).order_by(APIKey.created_at.desc())
    )
    api_keys = result.scalars().all()

    return templates.TemplateResponse(
        "api_keys.html",
        {"request": request, "tenant": tenant, "api_keys": api_keys},
    )


@router.post("/api-keys/new")
async def create_api_key(
    request: Request,
    name: str = Form(default="default"),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    full_key, key_prefix, key_hash = generate_api_key()

    api_key = APIKey(
        tenant_id=tenant.id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
    )
    db.add(api_key)
    await db.commit()

    return templates.TemplateResponse(
        "api_key_created.html",
        {
            "request": request,
            "tenant": tenant,
            "api_key": full_key,
            "key_name": name,
        },
    )


@router.post("/api-keys/{key_id}/delete")
async def delete_api_key(
    request: Request,
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete an API key."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.tenant_id == tenant.id,
        )
    )
    api_key = result.scalar_one_or_none()

    if api_key:
        await db.delete(api_key)
        await db.commit()

    return RedirectResponse(url="/portal/api-keys", status_code=303)


@router.post("/api-keys/{key_id}/toggle")
async def toggle_api_key(
    request: Request,
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Toggle API key active status."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.tenant_id == tenant.id,
        )
    )
    api_key = result.scalar_one_or_none()

    if api_key:
        api_key.is_active = not api_key.is_active
        db.add(api_key)
        await db.commit()

    return RedirectResponse(url="/portal/api-keys", status_code=303)


# ============== Logs ==============


@router.get("/logs", response_class=HTMLResponse)
async def list_logs(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    status: str = None,
    assistant_id: str = None,
    db: AsyncSession = Depends(get_db),
):
    """List tenant's query logs."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    # Get assistants for filter dropdown
    assistants_result = await db.execute(
        select(Assistant).where(Assistant.tenant_id == tenant.id)
    )
    assistants = assistants_result.scalars().all()

    # Build query
    stmt = select(QueryLog).where(QueryLog.tenant_id == tenant.id)

    if status:
        stmt = stmt.where(QueryLog.status == status)

    if assistant_id:
        stmt = stmt.where(QueryLog.assistant_id == UUID(assistant_id))

    stmt = stmt.order_by(QueryLog.created_at.desc())

    # Count total
    count_stmt = select(QueryLog).where(QueryLog.tenant_id == tenant.id)
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
        "logs.html",
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


@router.get("/logs/{query_id}", response_class=HTMLResponse)
async def log_detail(
    request: Request,
    query_id: str,
    db: AsyncSession = Depends(get_db),
):
    """View detail of a specific log."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    result = await db.execute(
        select(QueryLog).where(
            QueryLog.tenant_id == tenant.id,
            QueryLog.query_id == query_id,
        )
    )
    log = result.scalar_one_or_none()

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


# ============== Playground ==============


@router.get("/playground", response_class=HTMLResponse)
async def playground_form(request: Request, db: AsyncSession = Depends(get_db)):
    """Playground to test queries."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    # Get assistants
    assistants_result = await db.execute(
        select(Assistant).where(Assistant.tenant_id == tenant.id, Assistant.is_active == True)
    )
    assistants = assistants_result.scalars().all()

    # Get documents count
    docs_result = await db.execute(
        select(Document).where(Document.tenant_id == tenant.id, Document.status == "completed")
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


@router.post("/playground", response_class=HTMLResponse)
async def playground_query(
    request: Request,
    json_payload: str = Form(...),
    assistant_id: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Process a playground query."""
    tenant = await get_current_tenant(request, db)
    if not tenant:
        return RedirectResponse(url="/portal/login", status_code=303)

    # Get assistants for the form
    assistants_result = await db.execute(
        select(Assistant).where(Assistant.tenant_id == tenant.id, Assistant.is_active == True)
    )
    assistants = assistants_result.scalars().all()

    # Get documents count
    docs_result = await db.execute(
        select(Document).where(Document.tenant_id == tenant.id, Document.status == "completed")
    )
    documents = docs_result.scalars().all()

    # Get selected assistant if provided
    selected_assistant = None
    if assistant_id and assistant_id.strip():
        assistant_result = await db.execute(
            select(Assistant).where(
                Assistant.id == UUID(assistant_id),
                Assistant.tenant_id == tenant.id,
            )
        )
        selected_assistant = assistant_result.scalar_one_or_none()

    try:
        # Parse JSON payload
        payload = json_module.loads(json_payload)

        # Extract optional instructions from payload
        instructions = payload.pop("_instructions", None)
        search_query = payload.pop("_search_query", None)

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
