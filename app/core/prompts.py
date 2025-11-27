"""
Default system prompts - generic and minimal.
Each assistant should define its own specific prompts.
"""

# Generic default - assistants should override this
SYSTEM_PROMPT = """Eres un asistente inteligente que utiliza una base de conocimiento para responder consultas.

## Instrucciones Generales
1. Basa tus respuestas en el contexto proporcionado de la base de conocimiento
2. Si no tienes información suficiente, indícalo claramente
3. Sé preciso y conciso en tus respuestas
4. Sigue las instrucciones específicas que se te den en cada consulta"""


# Generic template - just passes through the user's message with RAG context
USER_PROMPT_TEMPLATE = """{instructions}

## Contexto de la Base de Conocimiento
{rag_context}

## Consulta
{user_message}"""


def format_rag_context(chunks: list) -> str:
    """Format retrieved chunks into context string."""
    if not chunks:
        return "No se encontró contexto relevante en la base de conocimiento."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        title = chunk.metadata.get("title", f"Documento {i}")
        context_parts.append(f"### {title}\n{chunk.content}")

    return "\n\n".join(context_parts)
