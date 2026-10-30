# Unified Async LLM Client

Cliente asíncrono para LLMs con una interfaz común para **OpenAI** y **Anthropic**
(más **Gemini**, usando su endpoint compatible con el SDK de OpenAI).
Incluye validación con Pydantic, streaming con generadores asíncronos y manejo
controlado de errores (rate limit, conexión, API).

## Estructura

| Archivo | Contenido |
|---|---|
| `schemas.py` | Modelos Pydantic: `ChatMessage`, `LLMConfig`, `ModelResponse`, `Provider` |
| `clients.py` | `BaseLLMClient` (abstracta), `OpenAIClient`, `GeminiClient`, `AnthropicClient` |
| `manager.py` | `AsyncLLMManager`: elige el cliente según la configuración |
| `main.py` | Script de prueba: modo normal y streaming |
| `.env.example` | Plantilla de variables de entorno |

## Requisitos

- Python 3.12 o superior
- Una API key de OpenAI y/o de Anthropic

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Variables de entorno

Copiá `.env.example` a `.env` y completalo:

| Variable | Descripción |
|---|---|
| `LLM_PROVIDER` | `openai`, `anthropic` o `gemini` |
| `OPENAI_API_KEY` | Clave de OpenAI (si usás `openai`) |
| `ANTHROPIC_API_KEY` | Clave de Anthropic (si usás `anthropic`) |
| `GOOGLE_API_KEY` | Clave de Google AI Studio (si usás `gemini`; tiene plan gratuito) |
| `LLM_MODEL` | Opcional. Por defecto `gpt-4o-mini` (OpenAI), `claude-haiku-4-5-20251001` (Anthropic) o `gemini-flash-latest` (Gemini) |

El archivo `.env` está en `.gitignore`: nunca se sube al repositorio.

## Ejecutar la prueba

```powershell
python main.py
```

El script:

1. Muestra cómo Pydantic rechaza una configuración inválida (`temperature=5`) antes de llamar a la API.
2. Pregunta "¿Qué es la entropía?" en **modo normal**.
3. Hace la misma pregunta en **modo streaming**, imprimiendo los fragmentos a medida que llegan.

## Notas

- `temperature` se valida entre 0 y 2. Anthropic solo admite de 0 a 1, así que usá valores hasta 1 con ese proveedor.
- Los mensajes con rol `system` se envían a Anthropic en su parámetro `system`, porque no los acepta dentro de `messages`.
- Los errores de rate limit, conexión y API no rompen el programa: en modo normal se devuelven en `ModelResponse.error`, y en streaming se emiten como un mensaje de error.
