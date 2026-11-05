# Agente ReAct con memoria persistente

Agente construido con LangGraph que decide por sí mismo, turno a turno, si necesita usar
una herramienta o si ya puede responder. Ese ciclo (modelo → ¿herramienta? → herramienta →
modelo → ...) es el patrón ReAct (Reasoning + Acting). El estado de la conversación se
guarda en SQLite, por lo que el agente recuerda las interacciones previas de un mismo
`thread_id`.

## Estructura

| Archivo | Contenido |
|---|---|
| `tools.py` | Base de datos simulada y las herramientas `buscar_cliente_por_nombre` y `buscar_pedidos` |
| `agent.py` | LLM con herramientas, `StateGraph`, nodos, arista condicional y funciones de traza |
| `main.py` | Pruebas: razonamiento multi-paso, memoria entre turnos y manejo de errores |
| `traza_ejecucion.json` | Traza ReAct de la última ejecución (se genera al correr `main.py`) |
| `.env.example` | Plantilla de variables de entorno |

## Requisitos

- Python 3.12
- Una API key de Google Gemini (gratis en
  [aistudio.google.com/apikey](https://aistudio.google.com/apikey))

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Variables de entorno

Copiá `.env.example` a `.env` y completá tu clave:

| Variable | Descripción |
|---|---|
| `GOOGLE_API_KEY` | Clave de Google AI Studio, usada por el LLM (Gemini) |

El archivo `.env` está en `.gitignore`: nunca se sube al repositorio.

## Ejecutar

```powershell
python main.py
```

El script ejecuta tres pruebas y guarda la traza en `traza_ejecucion.json`. El historial
de la conversación se persiste en `checkpoints.sqlite`, que se crea automáticamente.

## Cómo funciona

1. **Herramientas.** Se definen con `@tool` y docstrings descriptivos: el LLM decide qué
   herramienta usar leyendo únicamente esa descripción. Hay dos herramientas sobre dos
   tablas separadas, `buscar_cliente_por_nombre` y `buscar_pedidos`, para forzar que el
   agente razone en dos pasos: primero necesita el ID del cliente y después sus pedidos.
2. **Grafo.** Un `StateGraph` sobre `MessagesState`, que ya incluye el reducer de mensajes.
   El nodo `modelo` llama al LLM con el historial completo, y el nodo `herramientas`
   (`ToolNode`) ejecuta las herramientas. La arista condicional `tools_condition` envía el
   flujo a las herramientas si el último mensaje trae `tool_calls`, y a `END` si no. La
   arista `herramientas → modelo` cierra el ciclo, por lo que el modelo puede volver a usar
   herramientas las veces que necesite.
3. **Persistencia.** `AsyncSqliteSaver` guarda el estado en un archivo SQLite. Al usar el
   mismo `thread_id`, LangGraph recupera el historial antes de responder.
4. **Límite de recursión.** Todas las invocaciones definen `recursion_limit=10`, para evitar
   bucles infinitos y costos inesperados.
5. **Errores de herramientas.** `ToolNode` está configurado con `handle_tool_errors=True`,
   y las herramientas devuelven mensajes que empiezan con `ERROR:`. El modelo recibe ese
   texto como un mensaje normal y puede pedir una aclaración en lugar de inventar un dato.

## Pruebas

| Prueba | Qué verifica |
|---|---|
| Turno 1: "¿Cuántos pedidos tuvo Ana García y cuál fue el total?" | Razonamiento multi-paso: el agente llama a `buscar_cliente_por_nombre`, obtiene el ID y llama a `buscar_pedidos` (dos usos de herramientas) |
| Turno 2, mismo `thread_id`: "¿Y Juan Pérez?" | Memoria: la pregunta solo tiene sentido con el contexto del turno 1 |
| "¿Cuántos pedidos tuvo el cliente Roberto Sánchez?" | Ciclo de retorno: el cliente no existe, la herramienta devuelve un error y el agente pide verificar el nombre |

## Ejemplo de traza

Traza del turno 1 (la traza completa está en `traza_ejecucion.json`):

1. Usuario: "¿Cuántos pedidos tuvo Ana García y cuál fue el total?"
2. El agente llama a `buscar_cliente_por_nombre(nombre="Ana García")`.
3. La herramienta devuelve `Cliente encontrado: 'Ana García' → cliente_id=102`.
4. El agente llama a `buscar_pedidos(cliente_id=102)`.
5. La herramienta devuelve `pedidos=3, total=$14500`.
6. Respuesta: "Ana García tuvo un total de 3 pedidos y el monto gastado fue de $14,500."
