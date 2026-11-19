import json

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from app.llm import extraer_texto, llm
from app.state import EstadoOrquestador


@tool
def calcular_estadisticas(montos: list[float]) -> str:
    """Calcula estadísticas de una lista de montos de pedidos: cantidad, total, promedio,
    máximo y mínimo. Usar esta herramienta SIEMPRE que haya que obtener el total o el
    promedio por pedido de un cliente, en lugar de hacer la cuenta mentalmente.
    Devuelve un mensaje que empieza con ERROR si la lista está vacía."""
    if not montos:
        return "ERROR: la lista de montos está vacía."
    total = sum(montos)
    return json.dumps({
        "cantidad": len(montos),
        "total": total,
        "promedio": round(total / len(montos), 2),
        "maximo": max(montos),
        "minimo": min(montos),
    })


@tool
def calcular_diferencia_porcentual(valor_a: float, valor_b: float) -> str:
    """Calcula cuánto más grande (en porcentaje) es valor_a respecto de valor_b.
    Usar para comparar dos promedios o dos totales ya calculados. Un resultado positivo
    indica que valor_a es mayor que valor_b. Devuelve un mensaje que empieza con ERROR
    si valor_b es cero."""
    if valor_b == 0:
        return "ERROR: valor_b no puede ser cero."
    return json.dumps({"diferencia_porcentual": round((valor_a - valor_b) / valor_b * 100, 2)})


PROMPT_ANALISTA = """Sos el agente Analista de un sistema multi-agente.
Tu única tarea es CALCULAR y COMPARAR usando tus herramientas, a partir de los datos que
te entrega el Investigador: no tenés herramientas de búsqueda y no debés inventar datos.
Reglas:
1. Usá siempre las herramientas de cálculo, nunca hagas las cuentas de memoria.
2. Usá únicamente los montos que figuren en los datos recibidos.
3. Si faltan datos para calcular, decilo explícitamente en lugar de suponerlos.
4. Respondé con los resultados numéricos y una conclusión breve."""

agente_analista = create_react_agent(
    llm,
    tools=[calcular_estadisticas, calcular_diferencia_porcentual],
    prompt=PROMPT_ANALISTA,
)


async def nodo_analista(state: EstadoOrquestador) -> dict:
    datos = "\n".join(a["contenido"] for a in state["aportes"] if a["agente"] == "investigador")
    consigna = f"{state['instruccion']}\n\nDATOS DEL INVESTIGADOR:\n{datos}"
    resultado = await agente_analista.ainvoke(
        {"messages": [HumanMessage(content=consigna)]},
        config={"recursion_limit": 10},
    )
    texto = extraer_texto(resultado["messages"][-1])
    return {
        "messages": [AIMessage(content=texto, name="analista")],
        "aportes": [{"agente": "analista", "contenido": texto}],
    }
