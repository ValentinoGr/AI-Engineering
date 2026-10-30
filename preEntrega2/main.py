import asyncio

from chain import process_text

texto_ejemplo = """
Nuestra API en FastAPI está devolviendo timeouts intermitentes. El caché en Redis
parece saturarse en picos de tráfico y las conexiones a PostgreSQL se agotan
porque el pool está mal dimensionado. Esto está afectando a usuarios en producción.
"""

texto_ambiguo = "El sistema anda medio raro últimamente, no sé bien qué está pasando."


async def main():
    for provider in ["openai", "anthropic", "gemini"]:
        try:
            resultado = await process_text(texto_ejemplo, provider=provider)
            print(f"\n--- {provider.upper()} ---")
            print(resultado.model_dump_json(indent=2))
        except Exception as e:
            print(f"\n--- {provider.upper()} falló: {e} ---")

    print("\n--- PRUEBA DE ESTRÉS (texto ambiguo, gemini) ---")
    resultado = await process_text(texto_ambiguo, provider="gemini")
    print(resultado.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
