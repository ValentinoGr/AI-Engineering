import asyncio
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from openinference.instrumentation import using_session
from redis.asyncio import Redis

from app.jobs import actualizar_job
from app.llm import extraer_texto

logger = logging.getLogger("worker")

RECURSION_LIMIT = 30


async def worker_loop(
    nombre: str, cola: asyncio.Queue, grafo: CompiledStateGraph, redis: Redis
) -> None:
    while True:
        item = await cola.get()
        try:
            await procesar(item, grafo, redis)
        except Exception:
            logger.exception("[%s] error al registrar el resultado del job %s", nombre, item["job_id"])
        finally:
            cola.task_done()


async def procesar(item: dict[str, Any], grafo: CompiledStateGraph, redis: Redis) -> None:
    job_id: str = item["job_id"]
    config = {"configurable": {"thread_id": job_id}, "recursion_limit": RECURSION_LIMIT}

    try:
        await actualizar_job(redis, job_id, status="RUNNING")
        with using_session(session_id=job_id):
            if item["tipo"] == "nuevo":
                entrada: Any = {
                    "messages": [HumanMessage(content=item["pregunta"])],
                    "next_agent": "",
                    "instruccion": "",
                    "task_completed": False,
                    "pasos": 0,
                    "aportes": [],
                }
            else:
                entrada = Command(resume=item["decision"])
            await grafo.ainvoke(entrada, config=config)

        snapshot = await grafo.aget_state(config)
        if snapshot.next:
            pendientes = [i.value for t in snapshot.tasks for i in t.interrupts]
            await actualizar_job(
                redis,
                job_id,
                status="WAITING_APPROVAL",
                aprobacion_pendiente=pendientes[0] if pendientes else None,
            )
            logger.info("job %s pausado: espera aprobación humana", job_id)
            return

        await actualizar_job(
            redis,
            job_id,
            status="DONE",
            resultado=extraer_texto(snapshot.values["messages"][-1]),
            aportes=snapshot.values["aportes"],
        )
        logger.info("job %s terminado", job_id)
    except Exception as e:
        logger.exception("job %s falló", job_id)
        await actualizar_job(redis, job_id, status="FAILED", error=f"{type(e).__name__}: {e}")
