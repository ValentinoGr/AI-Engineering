import asyncio
import json
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import HumanMessage

from graph import grafo

PREGUNTAS = [
    "Compará el gasto promedio por pedido de Ana García y Juan Pérez, y decime quién gasta más por pedido.",
    "¿Cuál es el gasto promedio por pedido de Roberto Sánchez?",
]


async def ejecutar(pregunta: str) -> list[dict]:
    estado_inicial = {
        "messages": [HumanMessage(content=pregunta)],
        "next_agent": "",
        "instruccion": "",
        "task_completed": False,
        "pasos": 0,
        "aportes": [],
    }
    traza: list[dict] = []

    print("=" * 80)
    print("🧑", pregunta)
    print("=" * 80)

    async for evento in grafo.astream(
        estado_inicial, config={"recursion_limit": 25}, stream_mode="updates"
    ):
        for nodo, cambios in evento.items():
            aporte = cambios["aportes"][0]["contenido"]
            traza.append({"nodo": nodo, "contenido": aporte})
            if nodo == "supervisor":
                print(f"\n🧭 supervisor → {aporte}")
                if cambios["instruccion"]:
                    print(f"   instrucción: {cambios['instruccion']}")
            elif nodo == "responder":
                print(f"\n🤖 respuesta final:\n{aporte}")
            else:
                print(f"\n🔧 {nodo}:\n{aporte}")

    return traza


async def main() -> None:
    trazas = {}
    for i, pregunta in enumerate(PREGUNTAS, 1):
        trazas[f"consulta_{i}"] = {"pregunta": pregunta, "traza": await ejecutar(pregunta)}

    with open("traza_ejecucion.json", "w", encoding="utf-8") as f:
        json.dump(trazas, f, ensure_ascii=False, indent=2)

    print("\n✅ Traza guardada en traza_ejecucion.json")


if __name__ == "__main__":
    asyncio.run(main())
