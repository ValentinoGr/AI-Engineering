import asyncio
import os

from dotenv import load_dotenv
from pydantic import ValidationError

from manager import AsyncLLMManager
from schemas import ChatMessage, LLMConfig, Provider

PREGUNTA = "¿Qué es la entropía?"

MODELOS_POR_DEFECTO = {
    Provider.OPENAI: "gpt-4o-mini",
    Provider.ANTHROPIC: "claude-haiku-4-5-20251001",
    Provider.GEMINI: "gemini-flash-latest",
}


def probar_validacion() -> None:
    """Pydantic rechaza una config inválida ANTES de llamar a la API."""
    try:
        LLMConfig(provider=Provider.OPENAI, model="gpt-4o-mini", temperature=5)
    except ValidationError as e:
        print("❌ Se detectó ANTES de llamar a la API:\n", e)


def cargar_config() -> LLMConfig:
    provider = Provider(os.getenv("LLM_PROVIDER", "openai").lower())
    return LLMConfig(
        provider=provider,
        model=os.getenv("LLM_MODEL") or MODELOS_POR_DEFECTO[provider],
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        google_api_key=os.getenv("GOOGLE_API_KEY") or None,
        temperature=0.7,
        max_tokens=1024,
    )


async def main() -> None:
    load_dotenv()

    print("--- Validación con Pydantic ---")
    probar_validacion()

    try:
        manager = AsyncLLMManager(cargar_config())
    except (ValueError, ValidationError) as e:
        print(f"\nError de configuración: {e}")
        return

    mensajes = [ChatMessage(role="user", content=PREGUNTA)]

    print(f"\n--- Modo normal ({manager.config.provider.value}) ---")
    respuesta = await manager.generate(mensajes)
    if respuesta.error:
        print(f"Error controlado: {respuesta.error}")
    else:
        print(respuesta.content)

    print(f"\n--- Modo streaming ({manager.config.provider.value}) ---")
    async for fragmento in manager.generate_stream(mensajes):
        print(fragmento, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
