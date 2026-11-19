import argparse
import asyncio
import json
import os

import httpx

BASE_URL = os.getenv("API_URL", "http://localhost:8000")
PREGUNTA = "Aplicá un descuento del 10% a la cuenta de Ana García."


async def esperar(cliente: httpx.AsyncClient, job_id: str, estados: set[str]) -> dict:
    while True:
        job = (await cliente.get(f"/tasks/{job_id}")).json()
        print(f"   estado: {job['status']}")
        if job["status"] in estados:
            return job
        await asyncio.sleep(1)


async def main(rechazar: bool) -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as cliente:
        print(f"🧑 {PREGUNTA}")
        job_id = (await cliente.post("/tasks", json={"pregunta": PREGUNTA})).json()["job_id"]
        print(f"   job_id: {job_id}")

        job = await esperar(cliente, job_id, {"WAITING_APPROVAL", "DONE", "FAILED"})
        if job["status"] != "WAITING_APPROVAL":
            print("La tarea terminó sin pedir aprobación:", job["resultado"] or job["error"])
            return

        print("\n⏸️  La ejecución está pausada esperando aprobación humana:")
        print(json.dumps(job["aprobacion_pendiente"], ensure_ascii=False, indent=2))

        decision = {"aprobado": not rechazar, "comentario": "Rechazado desde el script de demo." if rechazar else "Aprobado desde el script de demo."}
        print(f"\n👤 Enviando decisión: {decision}")
        await cliente.post(f"/tasks/{job_id}/approve", json=decision)

        job = await esperar(cliente, job_id, {"DONE", "FAILED"})
        print("\n🤖 Resultado final:")
        print(job["resultado"] or job["error"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rechazar", action="store_true", help="Rechaza la acción en lugar de aprobarla")
    asyncio.run(main(parser.parse_args().rechazar))
