import logging
from typing import Any, Literal

from langchain_core.messages import AIMessage
from langgraph.types import Command, interrupt

from state import AnalisisDeCoincidencia, EstadoDelOrquestador, OfertaInvestigada, leer_analisis_de_coincidencia, leer_oferta_investigada

registro: logging.Logger = logging.getLogger("hitl")

PORCENTAJE_MINIMO_PARA_PROPONER_POSTULARSE: float = 60.0


def es_una_accion_critica(estado: EstadoDelOrquestador) -> bool:
    analisis: AnalisisDeCoincidencia | None = leer_analisis_de_coincidencia(estado)
    return analisis is not None and analisis.porcentaje_de_coincidencia >= PORCENTAJE_MINIMO_PARA_PROPONER_POSTULARSE


def elegir_ruta_despues_de_la_sintesis(estado: EstadoDelOrquestador) -> Literal["AprobacionHumana", "__end__"]:
    return "AprobacionHumana" if es_una_accion_critica(estado) else "__end__"


async def nodo_aprobacion_humana(estado: EstadoDelOrquestador) -> dict[str, Any]:
    oferta: OfertaInvestigada | None = leer_oferta_investigada(estado)
    analisis: AnalisisDeCoincidencia | None = leer_analisis_de_coincidencia(estado)
    registro.info("Acción crítica detectada: enviar postulación. Se pausa hasta recibir aprobación humana.")
    decision_humana: dict[str, str | bool] = interrupt(
        {
            "accion_critica": "enviar_postulacion",
            "motivo": "Enviar una postulación es una acción con efectos externos: requiere aprobación humana.",
            "empresa": oferta.empresa if oferta else "",
            "puesto": oferta.puesto if oferta else "",
            "porcentaje_de_coincidencia": analisis.porcentaje_de_coincidencia if analisis else 0,
        }
    )
    registro.info("Decisión humana recibida: %s", decision_humana)
    return {"decision_humana": decision_humana}


def elegir_ruta_despues_de_la_aprobacion(estado: EstadoDelOrquestador) -> Literal["EnviarPostulacion", "__end__"]:
    decision_humana: dict[str, str | bool] = estado.get("decision_humana") or {}
    return "EnviarPostulacion" if decision_humana.get("aprobado") is True else "__end__"


async def nodo_enviar_postulacion(estado: EstadoDelOrquestador) -> dict[str, Any]:
    oferta: OfertaInvestigada | None = leer_oferta_investigada(estado)
    registro.info("Postulación enviada (simulado) a %s.", oferta.empresa if oferta else "?")
    return {
        "postulacion_enviada": True,
        "messages": [AIMessage(content=f"Postulación enviada a {oferta.empresa if oferta else '?'} (simulado).", name="EnviarPostulacion")],
    }


def crear_comando_para_reanudar(aprobado: bool, comentario: str) -> Command:
    return Command(resume={"aprobado": aprobado, "comentario": comentario})
