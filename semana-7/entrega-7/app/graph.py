import logging
from functools import lru_cache
from typing import Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from agents.analyst_agent import nodo_analista
from agents.research_agent import nodo_investigador
from hitl import (
    elegir_ruta_despues_de_la_aprobacion,
    elegir_ruta_despues_de_la_sintesis,
    nodo_aprobacion_humana,
    nodo_enviar_postulacion,
)
from proveedor_de_modelos import crear_modelo_de_chat
from state import (
    AnalisisDeCoincidencia,
    EstadoDelOrquestador,
    NombreDelSiguientePaso,
    OfertaInvestigada,
    leer_analisis_de_coincidencia,
    leer_oferta_investigada,
)

registro: logging.Logger = logging.getLogger("orquestador")

CANTIDAD_MAXIMA_DE_PASOS_DE_ESPECIALISTAS: int = 6
TOLERANCIA_DEL_PORCENTAJE: float = 1.0


class DecisionDelSupervisor(BaseModel):
    siguiente: NombreDelSiguientePaso = Field(description="Próximo especialista, o FINALIZAR si la rúbrica se cumple.")
    razon: str = Field(description="Justificación breve de la decisión.")


plantilla_del_supervisor: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Sos el Supervisor de un equipo que ayuda a evaluar postulaciones laborales. NO hacés el trabajo de los especialistas: solo decidís quién sigue.\n"
            "- Investigador: encuentra la oferta de trabajo y extrae empresa, puesto, requisitos y deseables.\n"
            "- Analista: compara los requisitos con el perfil del candidato y calcula el porcentaje de coincidencia.\n\n"
            "Rúbrica para FINALIZAR (deben cumplirse todas):\n"
            "1. Hay una oferta investigada con al menos un requisito.\n"
            "2. Hay un análisis de coincidencia hecho sobre ESA oferta.\n"
            "3. No hay errores de validación pendientes.\n"
            "Si falta la oferta -> Investigador. Si hay oferta pero falta el análisis -> Analista. "
            "Si hay errores de validación, mandá al especialista responsable de ese error.",
        ),
        (
            "human",
            "Pedido del usuario: {pedido_del_usuario}\n\nEstado actual:\n- Oferta investigada: {resumen_de_la_oferta}\n"
            "- Análisis de coincidencia: {resumen_del_analisis}\n- Errores de validación pendientes: {errores_de_validacion}",
        ),
    ]
)


@lru_cache(maxsize=1)
def obtener_cadena_del_supervisor() -> Runnable:
    modelo_de_chat: BaseChatModel = crear_modelo_de_chat()
    return plantilla_del_supervisor | modelo_de_chat.with_structured_output(DecisionDelSupervisor)


async def nodo_supervisor(estado: EstadoDelOrquestador) -> dict[str, Any]:
    pasos_realizados: int = estado.get("pasos", 0)
    if pasos_realizados >= CANTIDAD_MAXIMA_DE_PASOS_DE_ESPECIALISTAS:
        registro.warning("Supervisor: se alcanzó el máximo de %d pasos. Se fuerza FINALIZAR.", CANTIDAD_MAXIMA_DE_PASOS_DE_ESPECIALISTAS)
        return {"siguiente_agente": "FINALIZAR"}

    oferta: OfertaInvestigada | None = leer_oferta_investigada(estado)
    analisis: AnalisisDeCoincidencia | None = leer_analisis_de_coincidencia(estado)
    decision: DecisionDelSupervisor = await obtener_cadena_del_supervisor().ainvoke(
        {
            "pedido_del_usuario": str(estado["messages"][0].content),
            "resumen_de_la_oferta": oferta.model_dump_json() if oferta else "todavía no",
            "resumen_del_analisis": analisis.model_dump_json() if analisis else "todavía no",
            "errores_de_validacion": estado.get("errores_de_validacion") or "ninguno",
        }
    )
    registro.info("Supervisor decide -> %s (%s)", decision.siguiente, decision.razon)
    return {
        "siguiente_agente": decision.siguiente,
        "messages": [AIMessage(content=f"Decisión: {decision.siguiente}. Motivo: {decision.razon}", name="Supervisor")],
    }


def encontrar_errores_de_validacion(oferta: OfertaInvestigada | None, analisis: AnalisisDeCoincidencia | None) -> list[str]:
    if oferta is None:
        return ["Investigador: falta la oferta investigada."]
    if analisis is None:
        return ["Analista: falta el análisis de coincidencia."]
    errores: list[str] = []
    requisitos_clasificados: set[str] = {requisito.lower() for requisito in analisis.requisitos_cumplidos + analisis.requisitos_faltantes}
    requisitos_sin_clasificar: list[str] = [requisito for requisito in oferta.requisitos if requisito.lower() not in requisitos_clasificados]
    if requisitos_sin_clasificar:
        errores.append(f"Analista: estos requisitos no figuran como cumplidos ni faltantes: {requisitos_sin_clasificar}")
    porcentaje_esperado: float = 100 * len(analisis.requisitos_cumplidos) / len(oferta.requisitos)
    if abs(porcentaje_esperado - analisis.porcentaje_de_coincidencia) > TOLERANCIA_DEL_PORCENTAJE:
        errores.append(
            f"Analista: el porcentaje {analisis.porcentaje_de_coincidencia}% no coincide con {len(analisis.requisitos_cumplidos)} de {len(oferta.requisitos)} requisitos ({porcentaje_esperado:.1f}%)."
        )
    return errores


async def nodo_validador(estado: EstadoDelOrquestador) -> dict[str, Any]:
    errores: list[str] = encontrar_errores_de_validacion(leer_oferta_investigada(estado), leer_analisis_de_coincidencia(estado))
    se_agotaron_los_pasos: bool = estado.get("pasos", 0) >= CANTIDAD_MAXIMA_DE_PASOS_DE_ESPECIALISTAS
    if errores and not se_agotaron_los_pasos:
        registro.warning("Validador: rechazado, vuelve al Supervisor. Errores: %s", errores)
        return {"errores_de_validacion": errores, "tarea_completada": False}
    if errores:
        registro.error("Validador: sigue habiendo errores pero se agotaron los pasos. Se escala a revisión humana: %s", errores)
    else:
        registro.info("Validador: todo OK, se pasa a la síntesis.")
    return {"errores_de_validacion": errores, "tarea_completada": True}


async def nodo_sintesis(estado: EstadoDelOrquestador) -> dict[str, list[BaseMessage]]:
    oferta: OfertaInvestigada | None = leer_oferta_investigada(estado)
    analisis: AnalisisDeCoincidencia | None = leer_analisis_de_coincidencia(estado)
    errores: list[str] = estado.get("errores_de_validacion", [])
    if oferta is None or analisis is None:
        texto_final: str = f"No se pudo completar el análisis. Requiere revisión humana. Errores: {errores}"
    else:
        texto_final = (
            f"{oferta.puesto} en {oferta.empresa}: tu perfil cumple el {analisis.porcentaje_de_coincidencia}% de los requisitos obligatorios.\n"
            f"Cumplís: {', '.join(analisis.requisitos_cumplidos) or 'ninguno'}.\n"
            f"Te falta: {', '.join(analisis.requisitos_faltantes) or 'nada'}.\n"
            f"Deseables que ya tenés: {', '.join(analisis.deseables_cumplidos) or 'ninguno'}.\n"
            f"Recomendación: {analisis.recomendacion}"
        )
        if errores:
            texto_final += f"\n(Atención: quedaron errores sin resolver, revisar a mano: {errores})"
    return {"messages": [AIMessage(content=texto_final, name="Sintesis")]}


def elegir_ruta_despues_del_supervisor(estado: EstadoDelOrquestador) -> Literal["Investigador", "Analista", "Validador"]:
    siguiente: NombreDelSiguientePaso | None = estado.get("siguiente_agente")
    if siguiente == "Investigador":
        return "Investigador"
    if siguiente == "Analista":
        return "Analista"
    return "Validador"


def elegir_ruta_despues_del_validador(estado: EstadoDelOrquestador) -> Literal["Supervisor", "Sintesis"]:
    return "Sintesis" if estado.get("tarea_completada") else "Supervisor"


def construir_grafo_del_orquestador() -> StateGraph:
    grafo: StateGraph = StateGraph(EstadoDelOrquestador)
    grafo.add_node("Supervisor", nodo_supervisor)
    grafo.add_node("Investigador", nodo_investigador)
    grafo.add_node("Analista", nodo_analista)
    grafo.add_node("Validador", nodo_validador)
    grafo.add_node("Sintesis", nodo_sintesis)
    grafo.add_node("AprobacionHumana", nodo_aprobacion_humana)
    grafo.add_node("EnviarPostulacion", nodo_enviar_postulacion)

    grafo.add_edge(START, "Supervisor")
    grafo.add_conditional_edges(
        "Supervisor",
        elegir_ruta_despues_del_supervisor,
        {"Investigador": "Investigador", "Analista": "Analista", "Validador": "Validador"},
    )
    grafo.add_edge("Investigador", "Supervisor")
    grafo.add_edge("Analista", "Supervisor")
    grafo.add_conditional_edges("Validador", elegir_ruta_despues_del_validador, {"Supervisor": "Supervisor", "Sintesis": "Sintesis"})
    grafo.add_conditional_edges("Sintesis", elegir_ruta_despues_de_la_sintesis, {"AprobacionHumana": "AprobacionHumana", END: END})
    grafo.add_conditional_edges("AprobacionHumana", elegir_ruta_despues_de_la_aprobacion, {"EnviarPostulacion": "EnviarPostulacion", END: END})
    grafo.add_edge("EnviarPostulacion", END)
    return grafo


def compilar_grafo_con_persistencia(guardador_de_checkpoints: BaseCheckpointSaver) -> CompiledStateGraph:
    return construir_grafo_del_orquestador().compile(checkpointer=guardador_de_checkpoints)


def crear_estado_inicial(pedido_del_usuario: str) -> dict[str, Any]:
    return {
        "messages": [HumanMessage(content=pedido_del_usuario)],
        "siguiente_agente": None,
        "tarea_completada": False,
        "pasos": 0,
        "oferta_investigada": None,
        "analisis_de_coincidencia": None,
        "errores_de_validacion": [],
        "contribuciones": [],
        "decision_humana": None,
        "postulacion_enviada": False,
    }
