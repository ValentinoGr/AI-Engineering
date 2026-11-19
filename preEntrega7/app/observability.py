import logging
import os

from openinference.instrumentation.langchain import LangChainInstrumentor
from phoenix.otel import register

logger = logging.getLogger("observability")


def iniciar_observabilidad() -> None:
    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006").rstrip("/")
    proyecto = os.getenv("PHOENIX_PROJECT_NAME", "preentrega7-multiagente")
    tracer_provider = register(
        project_name=proyecto,
        endpoint=f"{endpoint}/v1/traces",
        batch=True,
        verbose=False,
        set_global_tracer_provider=False,
    )
    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    logger.info("Trazas hacia Phoenix: %s (proyecto %s)", endpoint, proyecto)
