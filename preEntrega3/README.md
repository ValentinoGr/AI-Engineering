# Sistema de recuperación semántica local (RAG)

Flujo End-to-End de RAG sobre documentos de políticas internas de una empresa ficticia
(TechCorp): ingesta de archivos `.txt`, chunking, indexación en ChromaDB, recuperación por
similitud semántica y generación de respuestas basadas exclusivamente en el contexto
recuperado.

## Estructura

| Archivo | Contenido |
|---|---|
| `data/` | Dataset de ejemplo: 4 archivos `.txt` (vacaciones, teletrabajo, seguridad informática, onboarding) |
| `ingesta.py` | Carga de documentos, chunking, embeddings y persistencia en ChromaDB |
| `rag_chain.py` | Retriever, esquemas Pydantic, prompt, cadena LCEL y `get_rag_response()` |
| `main.py` | Pruebas: pregunta con respuesta en los documentos, pregunta trampa y modo interactivo |
| `.env.example` | Plantilla de variables de entorno |

## Requisitos

- Python 3.12 o superior
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

La primera ejecución descarga el modelo de embeddings (`all-MiniLM-L6-v2`) e indexa los
documentos en `./vectorstore`. Las siguientes ejecuciones detectan el índice existente y lo
cargan sin reindexar. Para forzar una nueva indexación, borrá la carpeta `vectorstore`.

El script ejecuta, en orden:

1. Una prueba rápida del retriever, que muestra los fragmentos recuperados.
2. Una pregunta cuya respuesta **sí** está en los documentos.
3. Una "pregunta trampa" cuya respuesta **no** está en los documentos, para verificar que el
   modelo no alucine.
4. Un modo interactivo para hacer preguntas propias (se sale escribiendo `salir` o
   presionando Enter con la línea vacía).

## Cómo funciona

1. **Chunking.** Se usa `RecursiveCharacterTextSplitter.from_tiktoken_encoder` con
   `chunk_size=500` y `chunk_overlap=70`. El tamaño se mide en tokens y no en caracteres,
   porque el límite de contexto del LLM se mide en tokens. Con documentos cortos como los
   del ejemplo, cada archivo genera un único fragmento: `chunk_size` es un techo, no un
   mínimo forzado.
2. **Embeddings y persistencia.** Se usa el mismo modelo de embeddings
   (`sentence-transformers/all-MiniLM-L6-v2`) para indexar y para consultar, ya que mezclar
   modelos produce distancias vectoriales sin sentido. Los vectores se guardan en una
   colección persistente de ChromaDB, y el script verifica si el índice ya existe antes de
   volver a indexar.
3. **Retriever.** Búsqueda por similitud con `k=4`: un `top_k` entre 3 y 5 evita pasarle
   demasiado contexto al LLM.
4. **Salida estructurada.** El LLM genera solo el texto de la respuesta
   (`RespuestaLLM`), parseado con `PydanticOutputParser`. Las fuentes las arma el propio
   código a partir de los metadatos reales de los documentos recuperados, y no el LLM, que
   podría inventar referencias. El resultado final es un objeto `RAGResponse` con la
   respuesta, las fuentes y la cantidad de fragmentos usados.
5. **Prompt de veracidad.** El prompt de sistema instruye al modelo a responder únicamente
   con el CONTEXTO y a decir "No tengo acceso a esa información en los documentos
   disponibles." cuando la respuesta no está.
6. **Cadena LCEL asíncrona.** `prompt | llm | parser`, invocada con `.ainvoke()`, y el
   retriever también se consulta de forma asíncrona con `.ainvoke()`.
