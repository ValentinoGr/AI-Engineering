from typing import Literal

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from agents.analyst_agent import nodo_analista
from agents.research_agent import nodo_investigador
from llm import extraer_texto, llm
from state import Aporte, EstadoOrquestador

MAX_PASOS = 6


class DecisionSupervisor(BaseModel):
    siguiente: Literal["investigador", "analista", "FINISH"] = Field(
        description="Quién debe intervenir ahora, o FINISH si la tarea está completa y validada."
    )
    instruccion: str = Field(
        description="Instrucción puntual y autosuficiente para el especialista elegido. Vacío si es FINISH."
    )
    razon: str = Field(description="Justificación breve de la decisión, aplicando la rúbrica.")


PROMPT_SUPERVISOR = ChatPromptTemplate.from_messages([
    ("system",
     "Sos el Supervisor de un sistema multi-agente. Coordinás a dos especialistas:\n"
     "- investigador: busca y recopila datos de clientes y pedidos. No calcula.\n"
     "- analista: calcula estadísticas y compara usando los datos que ya recopiló el investigador. No busca datos.\n\n"
     "Dada la conversación actual, decidí quién debe intervenir ahora o si es momento de finalizar.\n\n"
     "RÚBRICA DE VALIDACIÓN. Solo podés elegir FINISH si se cumplen TODOS estos puntos:\n"
     "1. El investigador aportó datos concretos para todo lo que pidió el usuario, o informó con claridad que no existen.\n"
     "2. Si la pregunta requiere cálculos o comparaciones, el analista los realizó con herramientas.\n"
     "3. Los números del análisis provienen de los datos del investigador y no se contradicen con ellos.\n"
     "4. Ningún aporte contiene errores sin resolver ni datos inventados.\n"
     "Si algún punto falla, enviá a quien corresponda con una instrucción precisa para corregirlo.\n"
     "Si un dato no existe (por ejemplo, un cliente inexistente), no insistas: elegí FINISH para informarlo.\n"
     "Respetá el orden lógico: primero datos (investigador), después cálculos (analista)."),
    ("human",
     "PREGUNTA DEL USUARIO:\n{pregunta}\n\n"
     "APORTES HASTA AHORA:\n{aportes}\n\n"
     "PASOS USADOS: {pasos} de {max_pasos}"),
])

cadena_supervisor = PROMPT_SUPERVISOR | llm.with_structured_output(DecisionSupervisor)

PROMPT_RESPUESTA = ChatPromptTemplate.from_messages([
    ("system",
     "Sos el redactor final de un sistema multi-agente. Respondé la pregunta del usuario en español, "
     "de forma clara y breve, usando EXCLUSIVAMENTE los aportes de los especialistas. "
     "Si faltan datos o hubo errores, explicalo con honestidad en lugar de inventar."),
    ("human", "PREGUNTA DEL USUARIO:\n{pregunta}\n\nAPORTES DE LOS ESPECIALISTAS:\n{aportes}"),
])

cadena_respuesta = PROMPT_RESPUESTA | llm


def formatear_aportes(aportes: list[Aporte]) -> str:
    lineas = [f"[{a['agente']}] {a['contenido']}" for a in aportes if a["agente"] != "supervisor"]
    return "\n\n".join(lineas) if lineas else "(todavía no hay aportes)"


async def nodo_supervisor(state: EstadoOrquestador) -> dict:
    pasos = state.get("pasos", 0)
    if pasos >= MAX_PASOS:
        decision = DecisionSupervisor(
            siguiente="FINISH",
            instruccion="",
            razon="Límite de pasos alcanzado: se cierra con la información disponible.",
        )
    else:
        decision = await cadena_supervisor.ainvoke({
            "pregunta": extraer_texto(state["messages"][0]),
            "aportes": formatear_aportes(state["aportes"]),
            "pasos": pasos,
            "max_pasos": MAX_PASOS,
        })
    return {
        "next_agent": decision.siguiente,
        "instruccion": decision.instruccion,
        "task_completed": decision.siguiente == "FINISH",
        "pasos": pasos + 1,
        "aportes": [{"agente": "supervisor", "contenido": f"{decision.siguiente}: {decision.razon}"}],
    }


def enrutar(state: EstadoOrquestador) -> Literal["investigador", "analista", "responder"]:
    if state["next_agent"] == "FINISH":
        return "responder"
    return state["next_agent"]


async def nodo_responder(state: EstadoOrquestador) -> dict:
    respuesta = await cadena_respuesta.ainvoke({
        "pregunta": extraer_texto(state["messages"][0]),
        "aportes": formatear_aportes(state["aportes"]),
    })
    texto = extraer_texto(respuesta)
    return {
        "messages": [AIMessage(content=texto, name="respuesta_final")],
        "aportes": [{"agente": "respuesta_final", "contenido": texto}],
    }


builder = StateGraph(EstadoOrquestador)
builder.add_node("supervisor", nodo_supervisor)
builder.add_node("investigador", nodo_investigador)
builder.add_node("analista", nodo_analista)
builder.add_node("responder", nodo_responder)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges(
    "supervisor",
    enrutar,
    {"investigador": "investigador", "analista": "analista", "responder": "responder"},
)
builder.add_edge("investigador", "supervisor")
builder.add_edge("analista", "supervisor")
builder.add_edge("responder", END)

grafo = builder.compile()
