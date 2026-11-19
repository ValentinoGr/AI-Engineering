from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from langgraph.types import Command, interrupt
from pydantic import BaseModel

from app.jobs import actualizar_job, obtener_job
from app.state import EstadoOrquestador

router = APIRouter()


class DecisionAprobacion(BaseModel):
    aprobado: bool
    comentario: str = ""


async def nodo_aprobacion_humana(
    state: EstadoOrquestador,
) -> Command[Literal["ejecutor", "supervisor"]]:
    decision = interrupt({
        "tipo": "aprobacion_requerida",
        "accion": state["instruccion"],
        "motivo": "La acción tiene efectos secundarios y requiere aprobación humana.",
    })
    comentario = decision.get("comentario", "")
    if decision.get("aprobado"):
        return Command(
            goto="ejecutor",
            update={"aportes": [{"agente": "humano", "contenido": f"APROBADO. {comentario}".strip()}]},
        )
    return Command(
        goto="supervisor",
        update={"aportes": [{"agente": "humano", "contenido": f"RECHAZADO. {comentario}".strip()}]},
    )


@router.post("/tasks/{job_id}/approve", status_code=202)
async def aprobar_tarea(job_id: str, decision: DecisionAprobacion, request: Request) -> dict:
    redis = request.app.state.redis
    job = await obtener_job(redis, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if job["status"] != "WAITING_APPROVAL":
        raise HTTPException(
            status_code=409,
            detail=f"La tarea está en estado {job['status']}: no espera aprobación",
        )
    await actualizar_job(redis, job_id, status="RUNNING", aprobacion_pendiente=None)
    await request.app.state.cola.put(
        {"tipo": "reanudar", "job_id": job_id, "decision": decision.model_dump()}
    )
    return {"job_id": job_id, "status": "RUNNING", "aprobado": decision.aprobado}
