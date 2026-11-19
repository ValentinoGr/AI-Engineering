import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from pydantic import BaseModel, Field
from redis.asyncio import Redis

load_dotenv()

from app.graph import construir_grafo
from app.hitl import router as hitl_router
from app.jobs import crear_job, obtener_job
from app.observability import iniciar_observabilidad
from app.worker import worker_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
NUM_WORKERS = int(os.getenv("NUM_WORKERS", "5"))


class TareaNueva(BaseModel):
    pregunta: str = Field(min_length=3, description="Consulta o pedido para el sistema multi-agente")


class TareaEncolada(BaseModel):
    job_id: str
    status: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    iniciar_observabilidad()
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    async with AsyncRedisSaver.from_conn_string(REDIS_URL) as checkpointer:
        await checkpointer.asetup()
        grafo = construir_grafo(checkpointer)
        cola: asyncio.Queue = asyncio.Queue()
        workers = [
            asyncio.create_task(worker_loop(f"worker-{i}", cola, grafo, redis))
            for i in range(NUM_WORKERS)
        ]
        app.state.redis = redis
        app.state.cola = cola
        app.state.grafo = grafo
        yield
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
    await redis.aclose()


app = FastAPI(title="API multi-agente asíncrona", lifespan=lifespan)
app.include_router(hitl_router)


@app.get("/health")
async def health(request: Request) -> dict:
    await request.app.state.redis.ping()
    return {"status": "ok", "workers": NUM_WORKERS, "en_cola": request.app.state.cola.qsize()}


@app.post("/tasks", status_code=202, response_model=TareaEncolada)
async def crear_tarea(tarea: TareaNueva, request: Request) -> TareaEncolada:
    job = await crear_job(request.app.state.redis, tarea.pregunta)
    await request.app.state.cola.put(
        {"tipo": "nuevo", "job_id": job["job_id"], "pregunta": tarea.pregunta}
    )
    return TareaEncolada(job_id=job["job_id"], status=job["status"])


@app.get("/tasks/{job_id}")
async def obtener_tarea(job_id: str, request: Request) -> dict:
    job = await obtener_job(request.app.state.redis, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return job
