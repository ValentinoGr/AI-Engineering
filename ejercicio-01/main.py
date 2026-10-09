import asyncio


async def gpt_4_call():
    print("[GPT-4] Iniciando llamada...")
    await asyncio.sleep(1.2)
    print("[GPT-4] Respuesta completada.")
    return "Respuesta de GPT-4"


async def claude_3_call():
    print("[Claude-3] Iniciando llamada...")
    await asyncio.sleep(0.8)
    print("[Claude-3] Respuesta completada.")
    return "Respuesta de Claude-3"


async def local_llama_call():
    print("[Llama-Local] Iniciando llamada...")
    await asyncio.sleep(2.5)
    print("[Llama-Local] Respuesta completada.")
    return "Respuesta de Llama"


async def orquestar_llamadas():
    print("\n--- Ejecutando llamadas simultaneas con Timeout (2s) ---")
    try:
        async with asyncio.timeout(2.0):
            resultados = await asyncio.gather(
                gpt_4_call(), claude_3_call(), local_llama_call()
            )
            print("Resultados:", resultados)

    except TimeoutError:
        print("ERROR: La operacion excedio el tiempo limite de 2 segundos.")


async def llamada_con_semaforo(semaphore: asyncio.Semaphore, id_tarea: int):
    async with semaphore:
        print(f"[Tarea {id_tarea}] Bloque adquirido. Ejecutando...")
        await asyncio.sleep(1.0)
        print(f"[Tarea {id_tarea}] Finalizada.")


async def probar_semaforo():
    print("\n--- Probando Semaphore (Maximo 2 concurrentes) ---")
    sem = asyncio.Semaphore(2)

    tareas = [llamada_con_semaforo(sem, i) for i in range(1, 11)]
    await asyncio.gather(*tareas)


async def main():
    await orquestar_llamadas()
    await probar_semaforo()


if __name__ == "__main__":
    asyncio.run(main())
