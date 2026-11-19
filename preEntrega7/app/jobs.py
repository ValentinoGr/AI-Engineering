import json
import time
import uuid
from typing import Any

from redis.asyncio import Redis

PREFIJO = "job:"
TTL_SEGUNDOS = 86400


def clave(job_id: str) -> str:
    return f"{PREFIJO}{job_id}"


async def crear_job(redis: Redis, pregunta: str) -> dict[str, Any]:
    ahora = time.time()
    job = {
        "job_id": uuid.uuid4().hex,
        "status": "PENDING",
        "pregunta": pregunta,
        "resultado": None,
        "aportes": [],
        "aprobacion_pendiente": None,
        "error": None,
        "creado_ts": ahora,
        "actualizado_ts": ahora,
        "duracion_s": None,
    }
    await redis.set(clave(job["job_id"]), json.dumps(job), ex=TTL_SEGUNDOS)
    return job


async def obtener_job(redis: Redis, job_id: str) -> dict[str, Any] | None:
    crudo = await redis.get(clave(job_id))
    return json.loads(crudo) if crudo else None


async def actualizar_job(redis: Redis, job_id: str, **campos: Any) -> dict[str, Any]:
    job = await obtener_job(redis, job_id)
    if job is None:
        raise KeyError(f"No existe el job {job_id}")
    job.update(campos)
    job["actualizado_ts"] = time.time()
    if job["status"] in ("DONE", "FAILED"):
        job["duracion_s"] = round(job["actualizado_ts"] - job["creado_ts"], 2)
    await redis.set(clave(job_id), json.dumps(job, default=str), ex=TTL_SEGUNDOS)
    return job
