from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, trim_messages
from langchain_core.runnables import Runnable
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from herramientas import HERRAMIENTAS_DEL_AGENTE
from proveedor_de_modelos import crear_modelo_de_chat

CANTIDAD_MAXIMA_DE_MENSAJES_ENVIADOS_AL_MODELO: int = 20

INSTRUCCIONES_DEL_AGENTE: SystemMessage = SystemMessage(
    content=(
        "Sos un asistente que ayuda al usuario a seguir sus postulaciones laborales. "
        "Usá las herramientas para consultar datos; nunca inventes estados, fechas ni contactos. "
        "Si una herramienta devuelve un ERROR con nombres sugeridos, volvé a intentar con el nombre sugerido. "
        "Si no hay sugerencias, pedile al usuario que aclare. Respondé en español, breve y claro."
    )
)


class EstadoDelAgenteDePostulaciones(MessagesState):
    pass


@lru_cache(maxsize=1)
def obtener_modelo_con_herramientas() -> Runnable:
    modelo_de_chat: BaseChatModel = crear_modelo_de_chat()
    return modelo_de_chat.bind_tools(HERRAMIENTAS_DEL_AGENTE)


def recortar_historial_para_no_llenar_el_contexto(mensajes: list[BaseMessage]) -> list[BaseMessage]:
    return trim_messages(
        mensajes,
        strategy="last",
        token_counter=len,
        max_tokens=CANTIDAD_MAXIMA_DE_MENSAJES_ENVIADOS_AL_MODELO,
        start_on="human",
        include_system=False,
    )


async def nodo_modelo(estado: EstadoDelAgenteDePostulaciones) -> dict[str, list[BaseMessage]]:
    mensajes_recientes: list[BaseMessage] = recortar_historial_para_no_llenar_el_contexto(estado["messages"])
    respuesta_del_modelo: BaseMessage = await obtener_modelo_con_herramientas().ainvoke([INSTRUCCIONES_DEL_AGENTE, *mensajes_recientes])
    return {"messages": [respuesta_del_modelo]}


def construir_grafo_react() -> StateGraph:
    grafo: StateGraph = StateGraph(EstadoDelAgenteDePostulaciones)
    grafo.add_node("modelo", nodo_modelo)
    grafo.add_node("herramientas", ToolNode(HERRAMIENTAS_DEL_AGENTE, handle_tool_errors=True))
    grafo.add_edge(START, "modelo")
    grafo.add_conditional_edges("modelo", tools_condition, {"tools": "herramientas", END: END})
    grafo.add_edge("herramientas", "modelo")
    return grafo
