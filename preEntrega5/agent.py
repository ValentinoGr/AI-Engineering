from dotenv import load_dotenv
from langchain_core.messages import AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

from tools import herramientas

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-flash-lite-latest", temperature=0)
llm_con_herramientas = llm.bind_tools(herramientas)


async def nodo_modelo(state: MessagesState) -> dict:
    """Le pasa el historial completo al LLM y devuelve su respuesta (que puede
    incluir tool_calls o ser la respuesta final)."""
    respuesta = await llm_con_herramientas.ainvoke(state["messages"])
    return {"messages": [respuesta]}


grafo = StateGraph(MessagesState)  # hereda el reducer add_messages, como pide la consigna
grafo.add_node("modelo", nodo_modelo)
grafo.add_node("herramientas", ToolNode(herramientas, handle_tool_errors=True))

grafo.add_edge(START, "modelo")
grafo.add_conditional_edges(
    "modelo",
    tools_condition,  # mira si el último mensaje trae tool_calls
    {"tools": "herramientas", END: END},
)
grafo.add_edge("herramientas", "modelo")  # el ciclo: vuelve al modelo con el resultado de la tool


def extraer_texto(mensaje) -> str:
    """Normaliza el content de un mensaje (Gemini a veces devuelve una lista de bloques)."""
    contenido = mensaje.content
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        return "".join(b.get("text", "") for b in contenido if isinstance(b, dict))
    return str(contenido)


def serializar_traza(mensajes) -> list:
    """Convierte los mensajes de LangGraph a un formato JSON simple, para dejar
    la traza ReAct como log dentro del repo (pedido explícito de la consigna)."""
    traza = []
    for m in mensajes:
        entrada = {"tipo": type(m).__name__, "contenido": extraer_texto(m)}
        if isinstance(m, AIMessage) and m.tool_calls:
            entrada["tool_calls"] = [
                {"nombre": tc["name"], "argumentos": tc["args"]} for tc in m.tool_calls
            ]
        if isinstance(m, ToolMessage):
            entrada["herramienta"] = m.name
        traza.append(entrada)
    return traza
