import logging

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from schemas import EntidadesTecnicas

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pipeline_extraccion")


prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Sos un analista técnico. Extraé información estructurada del texto que te pasa el usuario. "
     "Identificá tecnologías mencionadas, evaluá el nivel de criticidad del problema o arquitectura "
     "descripta, y generá un resumen técnico breve."),
    ("human", "{texto}"),
])


def get_model(provider: str):
    if provider == "openai":
        return ChatOpenAI(model="gpt-4o-mini", temperature=0)
    elif provider == "anthropic":
        return ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
    elif provider == "gemini":
        return ChatGoogleGenerativeAI(model="gemini-flash-lite-latest", temperature=0)
    raise ValueError(f"Proveedor no soportado: {provider}")


def build_chain(provider: str = "openai"):
    model = get_model(provider)
    structured_model = model.with_structured_output(EntidadesTecnicas)

    chain = (prompt | structured_model).with_retry(
        stop_after_attempt=3,
        wait_exponential_jitter=True,
    )
    return chain


async def process_text(text: str, provider: str = "openai") -> EntidadesTecnicas:
    chain = build_chain(provider)
    logger.info(f"[{provider}] Procesando texto ({len(text)} caracteres)...")

    try:
        resultado = await chain.ainvoke({"texto": text})
        logger.info(f"[{provider}] ✅ Extracción validada: {resultado.model_dump()}")
        return resultado
    except Exception as e:
        logger.error(f"[{provider}] ❌ Falló tras reintentos: {e}")
        raise
