from typing import Optional
from app.config import settings


class ResumenService:
    """
    Pluggable LLM summary service.
    Follows project guidelines:
    - Neutral political tone
    - Plain language (lenguaje llano)
    - Clearly marked as automated summary
    - Disabled by default when no LLM key is provided
    """

    @classmethod
    async def generar_resumen(cls, titulo: str, extracto: str, tipo: str) -> Optional[str]:
        if not settings.ENABLE_LLM_SUMMARIES or not settings.LLM_API_KEY:
            return None

        # When enabled by the user in future steps, it calls OpenAI/Anthropic/Gemini
        # For now, cleanly returns None so that UI displays human official extract
        return None
