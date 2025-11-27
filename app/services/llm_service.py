"""
LLM service using Claude API - generic for any use case.
"""
import json
from anthropic import AsyncAnthropic
from typing import Any, Optional

from app.config import get_settings
from app.core.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, format_rag_context

settings = get_settings()


class LLMService:
    """Service for interacting with Claude API."""

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.max_output_tokens

    async def query(
        self,
        message: Any,
        rag_chunks: list,
        instructions: Optional[str] = None,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> dict:
        """
        Process a query using Claude with RAG context.

        Args:
            message: The user's message (string or structured data)
            rag_chunks: Retrieved context chunks from knowledge base
            instructions: Additional instructions for this query
            system_prompt: Custom system prompt (from assistant)
            model: Model override
            temperature: Temperature override

        Returns:
            Dict with response and metadata
        """
        # Format RAG context
        rag_context = format_rag_context(rag_chunks)

        # Convert message to string if it's structured data
        if isinstance(message, dict) or isinstance(message, list):
            user_message = json.dumps(message, indent=2, ensure_ascii=False)
        else:
            user_message = str(message)

        # Build the user prompt
        user_prompt = USER_PROMPT_TEMPLATE.format(
            instructions=instructions or "Responde a la consulta basándote en el contexto proporcionado.",
            rag_context=rag_context,
            user_message=user_message,
        )

        # Use custom system prompt if provided, otherwise default
        final_system_prompt = system_prompt or SYSTEM_PROMPT

        # Use provided model/temperature or defaults
        use_model = model or self.model
        use_temperature = temperature if temperature is not None else self.temperature

        # Call Claude API
        response = await self.client.messages.create(
            model=use_model,
            max_tokens=self.max_tokens,
            temperature=use_temperature,
            system=final_system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
        )

        # Extract the response text
        response_text = response.content[0].text

        # Try to parse as JSON if it looks like JSON
        parsed_response = self._try_parse_json(response_text)

        return {
            "response": parsed_response,
            "raw_response": response_text,
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
            "model_used": use_model,
        }

    def _try_parse_json(self, text: str) -> Any:
        """Try to parse text as JSON, return original if not valid JSON."""
        text = text.strip()

        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract from markdown code blocks
        if "```json" in text:
            try:
                json_start = text.find("```json") + 7
                json_end = text.find("```", json_start)
                json_str = text[json_start:json_end].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass

        if "```" in text:
            try:
                json_start = text.find("```") + 3
                json_end = text.find("```", json_start)
                json_str = text[json_start:json_end].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass

        # Return as string if not JSON
        return text


# Singleton instance
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get the singleton LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
