import json
import unicodedata

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from app.data import CLIENTES_DB, PEDIDOS_DB
from app.llm import extraer_texto, llm
from app.state import EstadoOrquestador


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").strip().lower()


CLIENTES_NORMALIZADOS: dict[str, int] = {normalizar(n): i for n, i in CLIENTES_DB.items()}


@tool
def buscar_cliente_por_nombre(nombre: str) -> str:
    """Busca el ID interno (cliente_id) de un cliente a partir de su nombre completo.
    La búsqueda ignora mayúsculas y tildes. Usar esta herramienta SIEMPRE que se mencione
    un cliente por su nombre y haga falta su cliente_id para consultar sus pedidos.
    Devuelve un mensaje que empieza con ERROR si el nombre no coincide con ningún
    cliente registrado."""
    clave = normalizar(nombre)
    if clave not in CLIENTES_NORMALIZADOS:
        return f"ERROR: no se encontró ningún cliente con el nombre '{nombre}'."
    return f"Cliente encontrado: '{nombre}' → cliente_id={CLIENTES_NORMALIZADOS[clave]}"


@tool
def obtener_pedidos_cliente(cliente_id: int) -> str:
    """Devuelve el listado de montos de TODOS los pedidos de un cliente, dado su
    cliente_id NUMÉRICO (no su nombre: si solo se tiene el nombre, primero usar
    buscar_cliente_por_nombre). La respuesta es un JSON con la cantidad de pedidos y la
    lista de montos. Devuelve un mensaje que empieza con ERROR si el cliente_id no existe."""
    if cliente_id not in PEDIDOS_DB:
        return f"ERROR: no existe ningún cliente con id={cliente_id}."
    montos = PEDIDOS_DB[cliente_id]
    return json.dumps({"cliente_id": cliente_id, "cantidad_pedidos": len(montos), "montos": montos})


PROMPT_INVESTIGADOR = """Sos el agente Investigador de un sistema multi-agente.
Tu única tarea es RECOPILAR datos usando tus herramientas: no calcules promedios ni
compares clientes, eso lo hace otro agente.
Reglas:
1. Para cada cliente mencionado, buscá su cliente_id y después sus pedidos.
2. Si una herramienta devuelve un ERROR, informalo tal cual en tu respuesta y no inventes datos.
3. Respondé con los datos crudos encontrados (cliente, cliente_id y lista de montos), sin interpretación."""

agente_investigador = create_react_agent(
    llm,
    tools=[buscar_cliente_por_nombre, obtener_pedidos_cliente],
    prompt=PROMPT_INVESTIGADOR,
)


async def nodo_investigador(state: EstadoOrquestador) -> dict:
    resultado = await agente_investigador.ainvoke(
        {"messages": [HumanMessage(content=state["instruccion"])]},
        config={"recursion_limit": 10},
    )
    texto = extraer_texto(resultado["messages"][-1])
    return {
        "messages": [AIMessage(content=texto, name="investigador")],
        "aportes": [{"agente": "investigador", "contenido": texto}],
    }
