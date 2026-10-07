import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph.state import CompiledStateGraph

from proveedor_de_modelos import crear_modelo_de_chat
from state import AnalisisDeCoincidencia, EstadoDelOrquestador, OfertaInvestigada

RUTA_DEL_PERFIL_DEL_CANDIDATO: Path = Path(__file__).parent.parent / "data" / "perfil_del_candidato.json"

INSTRUCCIONES_DEL_ANALISTA: str = (
    "Sos el agente Analista. Tu única función es comparar los requisitos de una oferta con el perfil del candidato "
    "usando la herramienta comparar_requisitos_con_el_perfil. Usá EXACTAMENTE el porcentaje y las listas que devuelve "
    "la herramienta; no calcules a mano. Agregá una recomendación breve y concreta. No busques ofertas nuevas."
)


def cargar_habilidades_del_candidato() -> set[str]:
    perfil: dict[str, Any] = json.loads(RUTA_DEL_PERFIL_DEL_CANDIDATO.read_text(encoding="utf-8"))
    return {habilidad.strip().lower() for habilidad in perfil["habilidades"]}


@tool
def comparar_requisitos_con_el_perfil(requisitos: list[str], deseables: list[str]) -> str:
    """Compara los requisitos obligatorios y deseables de una oferta con las habilidades del perfil del candidato.
    Devuelve un JSON con requisitos_cumplidos, requisitos_faltantes, deseables_cumplidos y porcentaje_de_coincidencia
    (porcentaje de requisitos obligatorios cumplidos, redondeado a 1 decimal)."""
    habilidades_del_candidato: set[str] = cargar_habilidades_del_candidato()
    requisitos_cumplidos: list[str] = [requisito for requisito in requisitos if requisito.strip().lower() in habilidades_del_candidato]
    requisitos_faltantes: list[str] = [requisito for requisito in requisitos if requisito not in requisitos_cumplidos]
    deseables_cumplidos: list[str] = [deseable for deseable in deseables if deseable.strip().lower() in habilidades_del_candidato]
    porcentaje_de_coincidencia: float = round(100 * len(requisitos_cumplidos) / len(requisitos), 1) if requisitos else 0.0
    return json.dumps(
        {
            "requisitos_cumplidos": requisitos_cumplidos,
            "requisitos_faltantes": requisitos_faltantes,
            "deseables_cumplidos": deseables_cumplidos,
            "porcentaje_de_coincidencia": porcentaje_de_coincidencia,
        },
        ensure_ascii=False,
    )


@lru_cache(maxsize=1)
def obtener_agente_analista() -> CompiledStateGraph:
    return create_agent(
        model=crear_modelo_de_chat(),
        tools=[comparar_requisitos_con_el_perfil],
        system_prompt=INSTRUCCIONES_DEL_ANALISTA,
        response_format=AnalisisDeCoincidencia,
    )


def armar_instruccion_minima_para_el_analista(estado: EstadoDelOrquestador) -> str:
    oferta_investigada: OfertaInvestigada | None = estado.get("oferta_investigada")
    datos_de_la_oferta: str = oferta_investigada.model_dump_json() if oferta_investigada else "(sin oferta)"
    errores_a_corregir: list[str] = estado.get("errores_de_validacion", [])
    instruccion: str = f"Analizá qué tan bien encaja el candidato con esta oferta:\n{datos_de_la_oferta}"
    if errores_a_corregir:
        instruccion += f"\n\nTu análisis anterior tuvo estos errores, corregilos: {errores_a_corregir}"
    return instruccion


async def nodo_analista(estado: EstadoDelOrquestador) -> dict[str, Any]:
    resultado_del_agente: dict[str, Any] = await obtener_agente_analista().ainvoke(
        {"messages": [HumanMessage(content=armar_instruccion_minima_para_el_analista(estado))]}
    )
    analisis: AnalisisDeCoincidencia = resultado_del_agente["structured_response"]
    resumen_del_aporte: str = f"Coincidencia: {analisis.porcentaje_de_coincidencia}%. Faltan: {analisis.requisitos_faltantes}"
    return {
        "analisis_de_coincidencia": analisis,
        "messages": [AIMessage(content=resumen_del_aporte, name="Analista")],
        "contribuciones": [{"agente": "Analista", "aporte": analisis.model_dump_json()}],
        "pasos": estado.get("pasos", 0) + 1,
    }
