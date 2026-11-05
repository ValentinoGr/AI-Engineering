import asyncio
import json
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent import extraer_texto, grafo, serializar_traza

CONFIG = {"configurable": {"thread_id": "conversacion-demo-1"}, "recursion_limit": 10}


async def main():
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        app = grafo.compile(checkpointer=checkpointer)

        print("=" * 80)
        print("🧑 Turno 1: '¿Cuántos pedidos tuvo Ana García y cuál fue el total?'")
        print("=" * 80)
        resultado1 = await app.ainvoke(
            {"messages": [HumanMessage(content="¿Cuántos pedidos tuvo Ana García y cuál fue el total?")]},
            config=CONFIG,
        )
        print("🤖", extraer_texto(resultado1["messages"][-1]))

        print("\n" + "=" * 80)
        print("🧑 Turno 2 (mismo thread_id): '¿Y Juan Pérez?'")
        print("=" * 80)
        resultado2 = await app.ainvoke(
            {"messages": [HumanMessage(content="¿Y Juan Pérez?")]},  # depende del contexto del turno 1
            config=CONFIG,
        )
        print("🤖", extraer_texto(resultado2["messages"][-1]))

        return resultado1, resultado2


async def probar_error():
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        app = grafo.compile(checkpointer=checkpointer)
        config_error = {"configurable": {"thread_id": "conversacion-error-1"}, "recursion_limit": 10}

        resultado = await app.ainvoke(
            {"messages": [HumanMessage(content="¿Cuántos pedidos tuvo el cliente Roberto Sánchez?")]},
            config=config_error,
        )
        print("🤖", extraer_texto(resultado["messages"][-1]))
        return resultado


async def ejecutar():
    resultado1, resultado2 = await main()
    resultado_error = await probar_error()

    traza_completa = {
        "turno_1_multi_paso": serializar_traza(resultado1["messages"]),
        "turno_2_memoria": serializar_traza(resultado2["messages"]),
        "prueba_error_y_aclaracion": serializar_traza(resultado_error["messages"]),
    }

    with open("traza_ejecucion.json", "w", encoding="utf-8") as f:
        json.dump(traza_completa, f, ensure_ascii=False, indent=2)

    print("✅ Traza guardada en traza_ejecucion.json")
    print(json.dumps(traza_completa["turno_1_multi_paso"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(ejecutar())
