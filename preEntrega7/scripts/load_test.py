import asyncio
import os
import statistics
import time

import httpx

BASE_URL = os.getenv("API_URL", "http://localhost:8000")
ESTADOS_FINALES = {"DONE", "FAILED", "WAITING_APPROVAL"}

PREGUNTAS = [
    "Compará el gasto promedio por pedido de Ana García y Juan Pérez, y decime quién gasta más por pedido.",
    "¿Cuál es el total gastado por María López y cuál es su promedio por pedido?",
    "¿Quién tiene más pedidos, Ana García o María López?",
    "Calculá el promedio por pedido de Juan Pérez y de María López y decime cuál es mayor.",
    "¿Cuántos pedidos tuvo Ana García y cuál fue su monto máximo?",
]


async def lanzar(cliente: httpx.AsyncClient, indice: int, pregunta: str) -> dict:
    inicio = time.perf_counter()
    respuesta = await cliente.post("/tasks", json={"pregunta": pregunta})
    respuesta.raise_for_status()
    job_id = respuesta.json()["job_id"]
    while True:
        job = (await cliente.get(f"/tasks/{job_id}")).json()
        if job["status"] in ESTADOS_FINALES:
            break
        await asyncio.sleep(1)
    return {
        "n": indice,
        "job_id": job_id,
        "status": job["status"],
        "segundos": time.perf_counter() - inicio,
    }


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as cliente:
        inicio = time.perf_counter()
        resultados = await asyncio.gather(
            *(lanzar(cliente, i, p) for i, p in enumerate(PREGUNTAS, 1))
        )
        total = time.perf_counter() - inicio

    print("=" * 70)
    print(f"{len(resultados)} peticiones concurrentes contra {BASE_URL}")
    print("=" * 70)
    for r in resultados:
        print(f"#{r['n']}  {r['status']:<17} {r['segundos']:6.1f} s   job_id={r['job_id']}")

    latencias = [r["segundos"] for r in resultados]
    p95 = statistics.quantiles(latencias, n=100, method="inclusive")[94]
    print("-" * 70)
    print(f"Tiempo total de la corrida : {total:.1f} s")
    print(f"Latencia p50               : {statistics.median(latencias):.1f} s")
    print(f"Latencia p95               : {p95:.1f} s")
    print(f"Latencia máxima            : {max(latencias):.1f} s")
    print(f"Terminadas OK / fallidas   : {sum(r['status'] == 'DONE' for r in resultados)} / "
          f"{sum(r['status'] == 'FAILED' for r in resultados)}")


if __name__ == "__main__":
    asyncio.run(main())
