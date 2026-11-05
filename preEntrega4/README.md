# Sistema RAG escalable en la nube con Pinecone

Sistema de recuperación híbrida sobre documentos de políticas internas de una empresa
ficticia (TechCorp). Combina búsqueda léxica (BM25) con búsqueda vectorial en Pinecone
Serverless, y se evalúa con Precision@5 y Recall@5 sobre un Golden Set.

## Estructura

| Archivo | Contenido |
|---|---|
| `data/` | Dataset de ejemplo: 4 archivos `.txt` (vacaciones, teletrabajo, seguridad informática, onboarding) |
| `setup_index.py` | Embeddings locales y creación del índice Serverless en Pinecone, si no existe |
| `ingesta.py` | Chunking, metadatos y carga de los vectores en Pinecone |
| `rag_system.py` | Recuperador híbrido (`EnsembleRetriever`) y clase `RAGSystem` |
| `evaluate.py` | Cálculo de Precision@5 y Recall@5 |
| `golden_set.json` | Preguntas de prueba con su documento esperado |
| `main.py` | Prueba rápida y modo interactivo |
| `.env.example` | Plantilla de variables de entorno |

## Requisitos

- Python 3.12
- Una cuenta de Pinecone con su API key (plan gratuito en
  [app.pinecone.io](https://app.pinecone.io))

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
| `PINECONE_API_KEY` | Clave de la cuenta de Pinecone |
| `INDEX_NAME` | Nombre del índice (si no se define, se usa `techcorp-rag-hibrido`) |

El archivo `.env` está en `.gitignore`: nunca se sube al repositorio. Los embeddings se
generan localmente, por lo que no hace falta ninguna clave de un proveedor de LLM.

## Replicar el índice de Pinecone

1. Completá `PINECONE_API_KEY` en el `.env`.
2. Ejecutá la ingesta:

   ```powershell
   python ingesta.py
   ```

   Al importar `setup_index.py`, el script verifica si el índice existe y lo crea si hace
   falta (Serverless, AWS `us-east-1`, dimensión 384, métrica coseno). Después divide los
   documentos en chunks y sube los vectores al namespace `politicas-internas`, con el
   texto original y los metadatos (fuente, categoría, id de chunk).

3. Cada ejecución de `python ingesta.py` agrega vectores nuevos al namespace. Si querés
   empezar de cero, borrá el índice desde la consola de Pinecone y volvé a ejecutar.

## Ejecutar

```powershell
python evaluate.py
python main.py
```

- `evaluate.py` corre las 5 preguntas del Golden Set y muestra el reporte en consola.
- `main.py` hace una consulta de ejemplo y abre un modo interactivo para consultar el
  recuperador híbrido (se sale escribiendo `salir`).

## Cómo funciona

1. **Embeddings locales.** Se usa `sentence-transformers/all-MiniLM-L6-v2`, cuya
   dimensión es 384. La dimensión se define una sola vez (`EMBEDDING_DIM`) y se reutiliza
   para crear el índice, para evitar el error de dimensiones que no coinciden.
2. **Chunking.** `RecursiveCharacterTextSplitter.from_tiktoken_encoder` con
   `chunk_size=600` y `chunk_overlap=100`, dentro del rango de 500 a 800 tokens.
3. **Metadatos.** Cada fragmento guarda su fuente, una categoría derivada del nombre del
   archivo y su id de chunk. El texto original se guarda dentro de los metadatos del
   vector en Pinecone, de modo que una sola consulta trae el vector, el texto y la fuente
   sin depender de una base de datos aparte.
4. **Namespace.** Los vectores se guardan en el namespace `politicas-internas`, para que
   la búsqueda no se mezcle con otros tipos de datos.
5. **Recuperador híbrido.** La búsqueda semántica es muy buena con paráfrasis, pero débil
   con términos exactos, siglas o nombres propios (por ejemplo "2FA"). BM25 busca
   coincidencias literales de palabras. `EnsembleRetriever` combina ambos con pesos
   `[0.5, 0.5]`, que se pueden ajustar.
6. **`RAGSystem`.** Encapsula el `EnsembleRetriever` y expone `obtener_top_k(query)`, que
   devuelve los 5 mejores fragmentos con su contenido, fuente y categoría.

## Evaluación

Se usa un Golden Set de 5 preguntas, cada una con un único documento esperado
(`golden_set.json`):

- **Recall@5**: 1 si el documento esperado aparece entre los fragmentos recuperados, 0 si
  no. Como cada pregunta tiene un solo documento relevante, el valor por pregunta solo
  puede ser 0 o 1.
- **Precision@5**: porcentaje de los fragmentos recuperados que provienen del documento
  esperado.

Resultados obtenidos:

| Métrica | Resultado |
|---|---|
| Recall@5 promedio | 100 % |
| Precision@5 promedio | 25 % |

La precisión de 25 % se explica por el tamaño del dataset: hay 4 documentos de menos de
600 tokens, así que el índice contiene solo 4 fragmentos (uno por archivo). El
recuperador devuelve los 4, y como solo uno es el esperado, la precisión máxima posible
con este dataset es 1/4. Con un dataset más grande, la precisión sería más informativa.
