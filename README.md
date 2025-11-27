# Re-skilling.AI RAG Service

Sistema RAG multi-tenant para evaluación de competencias blandas (soft skills).

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                         Clientes                                │
│    (cada uno con su API Key, Knowledge Base y Prompts)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Service                             │
│  ┌───────────┐  ┌──────────────┐  ┌───────────────────────┐    │
│  │ /evaluate │  │ /documents   │  │ /admin (panel + API)  │    │
│  └─────┬─────┘  └──────┬───────┘  └───────────────────────┘    │
│        │               │                                        │
│        ▼               ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    RAG Pipeline                          │   │
│  │  1. Cache Check (Redis)                                  │   │
│  │  2. Retrieve Context (Pinecone - tenant namespace)       │   │
│  │  3. Generate Evaluation (Claude API)                     │   │
│  │  4. Cache Result                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
    ┌─────────┐   ┌──────────┐   ┌──────────┐
    │ Claude  │   │ Pinecone │   │PostgreSQL│
    │   API   │   │(vectors) │   │  + Redis │
    └─────────┘   └──────────┘   └──────────┘
```

## Características

- **Multi-tenant**: Cada cliente tiene su propia base de conocimiento aislada
- **Consistente**: Mismas respuestas = mismas evaluaciones (cache + temperature=0)
- **Personalizable**: Prompts y rúbricas configurables por tenant
- **Seguro**: API keys hasheadas, validación de tenants

## Requisitos

- Python 3.11+
- Docker & Docker Compose
- API Keys para:
  - [Anthropic (Claude)](https://console.anthropic.com/)
  - [OpenAI (Embeddings)](https://platform.openai.com/)
  - [Pinecone](https://www.pinecone.io/)

## Inicio Rápido

### 1. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus API keys
```

### 2. Iniciar servicios con Docker

```bash
docker-compose up -d
```

Esto levanta:
- PostgreSQL en puerto 5432
- Redis en puerto 6379
- App en puerto 8000

### 3. Acceder al sistema

- **Admin Panel**: http://localhost:8000/admin
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 4. Crear primer tenant

1. Ir al Admin Panel (http://localhost:8000/admin)
2. Login con `ADMIN_SECRET` del `.env`
3. Crear nuevo tenant
4. Generar API key (guardarla, solo se muestra una vez)

### 5. Cargar base de conocimiento

```bash
# Cargar documentos seed
python scripts/seed_knowledge_base.py --tenant-slug <tu-slug>

# O subir documentos desde el Admin Panel
```

## Uso de la API

### Evaluar una respuesta

```bash
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "X-API-Key: sk_xxx_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "competency": "liderazgo",
    "question": "Cuéntame sobre una situación donde lideraste un equipo",
    "answer": "El año pasado lideré un proyecto de migración..."
  }'
```

### Respuesta

```json
{
  "evaluation_id": "uuid",
  "competency": "liderazgo",
  "score": 4.2,
  "level": "Avanzado",
  "strengths": ["Demuestra ownership", "Resultados medibles"],
  "areas_for_improvement": ["Podría profundizar en desarrollo de otros"],
  "justification": "La respuesta muestra un ejemplo completo...",
  "cached": false,
  "context_used": true
}
```

### Evaluación en lote

```bash
curl -X POST http://localhost:8000/api/v1/evaluate/batch \
  -H "X-API-Key: sk_xxx_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "evaluations": [
      {"competency": "liderazgo", "question": "...", "answer": "..."},
      {"competency": "comunicacion", "question": "...", "answer": "..."}
    ]
  }'
```

## API Endpoints

### Evaluación (requiere X-API-Key)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/evaluate` | Evaluar una respuesta |
| POST | `/api/v1/evaluate/batch` | Evaluar múltiples (max 10) |
| POST | `/api/v1/evaluate/preview-context` | Ver contexto RAG |

### Documentos (requiere X-API-Key)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/documents` | Listar documentos del tenant |
| POST | `/api/v1/documents/upload` | Subir documento |
| DELETE | `/api/v1/documents/{id}` | Eliminar documento |

### Admin API (requiere X-Admin-Secret)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/admin/tenants` | Listar tenants |
| POST | `/api/v1/admin/tenants` | Crear tenant |
| GET | `/api/v1/admin/tenants/{id}` | Obtener tenant |
| PATCH | `/api/v1/admin/tenants/{id}` | Actualizar tenant |
| POST | `/api/v1/admin/tenants/{id}/api-keys` | Crear API key |
| POST | `/api/v1/admin/tenants/{id}/prompts` | Crear/actualizar prompt |

## Estructura del Proyecto

```
.
├── app/
│   ├── admin/           # Admin panel web
│   │   ├── routes.py
│   │   └── templates/
│   ├── core/
│   │   ├── prompts.py   # Prompts por defecto
│   │   └── security.py  # Hashing de API keys
│   ├── db/
│   │   ├── database.py  # SQLAlchemy setup
│   │   └── redis.py     # Redis client
│   ├── models/
│   │   └── tenant.py    # SQLModel models
│   ├── routers/
│   │   ├── admin.py     # Admin API
│   │   ├── documents.py # Document management
│   │   ├── evaluate.py  # Evaluation endpoint
│   │   └── health.py    # Health checks
│   ├── schemas/
│   │   └── tenant.py    # Pydantic schemas
│   ├── services/
│   │   ├── cache_service.py
│   │   ├── document_processor.py
│   │   ├── embedding_service.py
│   │   ├── llm_service.py
│   │   ├── rag_service.py
│   │   └── vector_store.py
│   ├── config.py
│   ├── deps.py
│   └── main.py
├── knowledge_base/      # Documentos seed
│   ├── competencies/
│   ├── examples/
│   └── rubrics/
├── scripts/
│   └── seed_knowledge_base.py
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Personalización por Tenant

### Prompts Personalizados

Cada tenant puede tener prompts personalizados para:
- `system`: Instrucciones generales del evaluador
- `evaluation`: Formato de evaluación específico

Configurar via Admin Panel o API:

```bash
curl -X POST http://localhost:8000/api/v1/admin/tenants/{id}/prompts \
  -H "X-Admin-Secret: your_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_type": "system",
    "content": "Eres un evaluador experto en competencias para [industria]..."
  }'
```

### Base de Conocimiento

Cada tenant tiene su namespace aislado en Pinecone (`tenant_{slug}`).

Formatos soportados: PDF, DOCX, TXT, MD

## Desarrollo Local

### Sin Docker

```bash
# Instalar dependencias
pip install -r requirements.txt

# Asegurarse de tener PostgreSQL y Redis corriendo

# Ejecutar
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Tests

```bash
pytest tests/ -v
```

## Deployment a Railway

1. Crear proyecto en Railway
2. Agregar servicios: PostgreSQL, Redis
3. Configurar variables de entorno
4. Conectar repositorio GitHub
5. Deploy automático

## Seguridad

- API keys almacenadas como hash SHA-256
- Prefix de API key para lookup eficiente
- Aislamiento de datos por tenant (namespaces Pinecone)
- Admin secret separado para operaciones administrativas

## Troubleshooting

### Error de conexión a Pinecone
- Verificar `PINECONE_API_KEY` y `PINECONE_INDEX_NAME`
- El índice debe existir y tener dimensión 1536 (OpenAI embeddings)

### Error de embeddings
- Verificar `OPENAI_API_KEY`
- Modelo usado: `text-embedding-3-small`

### Error de evaluación
- Verificar `ANTHROPIC_API_KEY`
- Modelo usado: `claude-sonnet-4-20250514`

## Licencia

Privado - Re-skilling.AI
