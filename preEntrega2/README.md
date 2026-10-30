# Pipeline de Extracción de Entidades Técnicas

Pipeline con LangChain que recibe un texto libre (por ejemplo, un log de error o una
descripción de arquitectura) y devuelve un objeto validado con Pydantic: tecnologías
mencionadas, nivel de criticidad y un resumen técnico.

Proveedores soportados de forma intercambiable: **OpenAI**, **Anthropic** y **Gemini**.

## Estructura

| Archivo | Contenido |
|---|---|
| `schemas.py` | Modelo Pydantic `EntidadesTecnicas` y el enum `NivelCriticidad` |
| `chain.py` | Prompt, fábrica de modelos, cadena LCEL con reintento y `process_text()` |
| `main.py` | Script de prueba asíncrono: un ejemplo con los 3 proveedores y una prueba de estrés |
| `.env.example` | Plantilla de variables de entorno |

## Requisitos

- Python 3.12 o superior
- Una API key de al menos uno de los proveedores (Gemini tiene plan gratuito en
  [aistudio.google.com/apikey](https://aistudio.google.com/apikey))

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Variables de entorno

Copiá `.env.example` a `.env` y completá las claves que vayas a usar:

| Variable | Proveedor |
|---|---|
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic |
| `GOOGLE_API_KEY` | Gemini |

El archivo `.env` está en `.gitignore`: nunca se sube al repositorio.

## Ejecutar el script de prueba

```powershell
python main.py
```

El script procesa el mismo texto con los tres proveedores. Si falta la clave de alguno,
ese proveedor muestra un error controlado y el script sigue con el siguiente. Después
ejecuta una prueba de estrés con un texto ambiguo.

## Ejemplo de salida

Entrada:

```
Nuestra API en FastAPI está devolviendo timeouts intermitentes. El caché en Redis
parece saturarse en picos de tráfico y las conexiones a PostgreSQL se agotan
porque el pool está mal dimensionado. Esto está afectando a usuarios en producción.
```

Salida (Gemini):

```json
{
  "tecnologias": [
    "FastAPI",
    "Redis",
    "PostgreSQL"
  ],
  "nivel_de_criticidad": "alta",
  "resumen_tecnico": "La API en FastAPI sufre timeouts intermitentes en produccion debido a la saturacion del cache en Redis y el agotamiento del pool de conexiones en PostgreSQL durante picos de trafico."
}
```

## Cómo funciona

1. **Esquema Pydantic (el contrato de salida).** `nivel_de_criticidad` es un `Enum`
   (no un string libre) para que el modelo no pueda inventar valores como "high" o
   "ALTA". La lista de tecnologías no puede quedar vacía ni tener duplicados.
2. **Prompt modular con `ChatPromptTemplate`.** Se evitan los f-strings hardcodeados:
   el template declara `{texto}` como variable de entrada, que LangChain resuelve al
   invocar la cadena. La instrucción del sistema (rol del analista) está separada del
   mensaje humano (el texto a procesar).
3. **Fábrica de modelos intercambiable.** `get_model()` decide qué proveedor
   instanciar. Se usa `temperature=0`: para extracción estructurada se busca
   determinismo, no creatividad.
4. **Cadena LCEL con salida forzada y reintento.**
   `prompt | model.with_structured_output(EntidadesTecnicas)` hace que el modelo
   devuelva directamente una instancia del esquema, no texto crudo. `.with_retry()`
   reintenta automáticamente (hasta 3 intentos, con espera exponencial) si la llamada
   falla, por ejemplo con un JSON mal formado o incompleto.
5. **Función asíncrona con logs.** `process_text()` ejecuta la cadena con `.ainvoke()`
   (versión async, no bloqueante) y registra con `logging` el inicio, la validación
   exitosa y los errores si fallan todos los reintentos.

## Prueba de estrés

`main.py` pasa un texto sin detalles técnicos claros
(`"El sistema anda medio raro últimamente, no sé bien qué está pasando."`) para observar
cómo se comporta el pipeline: si el modelo inventa tecnologías, si asigna una
criticidad por defecto y si el validador de Pydantic rechaza la salida.

Resultado (Gemini, `gemini-flash-lite-latest`):

```json
{
  "tecnologias": [
    "desconocida"
  ],
  "nivel_de_criticidad": "baja",
  "resumen_tecnico": "El sistema presenta un comportamiento inespecifico y requiere revision general para identificar posibles fallas."
}
```

Observaciones:

- El validador **no lanzó ninguna excepción**: el modelo se recuperó por sí solo y devolvió un objeto válido.
- No inventó tecnologías reales, pero como el esquema exige al menos una (`min_length=1`), rellenó la lista con el valor `"desconocida"`. El contrato obliga a devolver algo aunque el texto no mencione ninguna tecnología, así que ese valor es un marcador y no una entidad real.
- Asignó criticidad `baja`, en vez de `media` o `alta`, ante la falta de información.

## Modelo y disponibilidad

Las pruebas se hicieron con Gemini (`gemini-flash-lite-latest`), porque tiene plan gratuito.
Los clientes de OpenAI y Anthropic están implementados con la misma interfaz, pero no se
probaron con claves reales. Con `gemini-flash-latest` se observaron errores 503 por alta
demanda del servicio: el reintento automático está pensado para ese tipo de fallas
temporales.
