from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.db.database import init_db
from app.db.redis import init_redis, close_redis

# Import routers
from app.routers import health, admin, evaluate, documents
from app.admin.routes import router as admin_panel_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    print("=" * 50)
    print("Starting Re-skilling.AI RAG Service...")
    print("=" * 50)
    await init_db()
    print("✓ Database initialized")
    await init_redis()
    print("✓ Redis initialized")
    print("=" * 50)
    print("Service ready!")
    print("Admin panel: http://localhost:8000/admin")
    print("API docs: http://localhost:8000/docs")
    print("=" * 50)
    yield
    # Shutdown
    print("Shutting down...")
    await close_redis()
    print("Connections closed")


app = FastAPI(
    title="Re-skilling.AI RAG Service",
    description="""
## Sistema RAG Multi-Tenant Genérico

Este servicio proporciona un sistema RAG (Retrieval Augmented Generation) genérico y flexible.

### Características
- **Multi-tenant**: Cada empresa tiene su propia base de conocimiento aislada
- **Asistentes personalizables**: Cada tenant puede crear múltiples asistentes con prompts propios
- **Genérico**: Acepta cualquier estructura de mensaje - el prompt del asistente define el comportamiento
- **Consistente**: Las mismas consultas producen las mismas respuestas (cache + temperature=0)

### Uso
1. Crea un tenant (empresa)
2. Sube documentos a la base de conocimiento
3. Crea asistentes con prompts personalizados
4. Envía consultas con cualquier estructura JSON

### Autenticación
Usa el header `X-API-Key` con tu API key de tenant para los endpoints de query y documentos.
""",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers

# Health checks
app.include_router(health.router, prefix="/api/v1", tags=["Health"])

# Admin API (requires X-Admin-Secret header)
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin API"])

# Main query endpoint (requires X-API-Key header)
app.include_router(evaluate.router, prefix="/api/v1", tags=["Query"])

# Document management (requires X-API-Key header)
app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])

# Admin web panel (uses session-based auth)
app.include_router(admin_panel_router, prefix="/admin", tags=["Admin Panel"])


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Re-skilling.AI RAG Service",
        "version": "1.0.0",
        "description": "Sistema RAG multi-tenant genérico con asistentes personalizables",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "admin_panel": "/admin",
            "api": "/api/v1",
        },
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "reskilling-rag"}
