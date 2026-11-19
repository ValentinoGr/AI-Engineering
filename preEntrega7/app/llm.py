import os

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

limitador = InMemoryRateLimiter(
    requests_per_second=float(os.getenv("LLM_REQUESTS_PER_SECOND", "0.2")),
    check_every_n_seconds=0.1,
    max_bucket_size=1,
)

llm = ChatGoogleGenerativeAI(model="gemini-flash-lite-latest", temperature=0, rate_limiter=limitador)


def extraer_texto(mensaje: BaseMessage) -> str:
    contenido = mensaje.content
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        return "".join(b.get("text", "") for b in contenido if isinstance(b, dict))
    return str(contenido)
