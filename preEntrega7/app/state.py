import operator
from typing import Annotated, TypedDict

from langgraph.graph import MessagesState


class Aporte(TypedDict):
    agente: str
    contenido: str


class EstadoOrquestador(MessagesState):
    next_agent: str
    instruccion: str
    task_completed: bool
    pasos: int
    aportes: Annotated[list[Aporte], operator.add]
