import json
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from app.data import DESCUENTOS_APLICADOS, PEDIDOS_DB
from app.llm import extraer_texto, llm
from app.state import EstadoOrquestador


@tool
def aplicar_descuento(cliente_id: int, porcentaje: float) -> str:
    """Aplica de forma PERMANENTE un descuento porcentual sobre la cuenta de un cliente.
    Es una acción con efectos secundarios reales: solo debe llamarse cuando se pidió
    explícitamente aplicar el descuento. Requiere el cliente_id NUMÉRICO y un porcentaje
    entre 1 y 50. Devuelve un mensaje que empieza con ERROR si el cliente no existe o el
    porcentaje es inválido."""
    if cliente_id not in PEDIDOS_DB:
        return f"ERROR: no existe ningún cliente con id={cliente_id}."
    if not 1 <= porcentaje <= 50:
        return "ERROR: el porcentaje debe estar entre 1 y 50."
    registro = {
        "cliente_id": cliente_id,
        "porcentaje": porcentaje,
        "aplicado_en": datetime.now(timezone.utc).isoformat(),
    }
    DESCUENTOS_APLICADOS.append(registro)
    return json.dumps({"estado": "aplicado", **registro})


PROMPT_EJECUTOR = """Sos el agente Ejecutor de un sistema multi-agente.
Tu única tarea es ejecutar la acción que te indica el Supervisor, que ya fue APROBADA por
un humano. No investigues ni analices datos.
Reglas:
1. Ejecutá exactamente la acción indicada, una sola vez, con los parámetros indicados.
2. Si la herramienta devuelve un ERROR, informalo tal cual y no reintentes con otros valores.
3. Respondé confirmando qué se ejecutó y con qué resultado."""

agente_ejecutor = create_react_agent(
    llm,
    tools=[aplicar_descuento],
    prompt=PROMPT_EJECUTOR,
)


async def nodo_ejecutor(state: EstadoOrquestador) -> dict:
    datos = "\n".join(a["contenido"] for a in state["aportes"] if a["agente"] == "investigador")
    consigna = f"{state['instruccion']}\n\nDATOS DEL INVESTIGADOR:\n{datos}"
    resultado = await agente_ejecutor.ainvoke(
        {"messages": [HumanMessage(content=consigna)]},
        config={"recursion_limit": 10},
    )
    texto = extraer_texto(resultado["messages"][-1])
    return {
        "messages": [AIMessage(content=texto, name="ejecutor")],
        "aportes": [{"agente": "ejecutor", "contenido": texto}],
    }
