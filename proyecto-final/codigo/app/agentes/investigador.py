import logging
from functools import lru_cache
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.graph.state import CompiledStateGraph

from app.contratos_de_datos import ConsultaALosDocumentosDelPuesto, ContextoDelPuesto, ContextoDelPuestoGuardado, ResultadoDeLaBusqueda
from app.grafo.estado import VistaDelInvestigador
from app.proveedor_de_modelos import crear_modelo_de_chat
from app.rag.busqueda import buscar_fragmentos_relevantes, listar_empresas_disponibles

registro: logging.Logger = logging.getLogger("investigador")

INSTRUCCIONES_DEL_INVESTIGADOR: str = (
    "Sos el agente Investigador. Preparás el contexto que va a usar un entrevistador para ayudar a un candidato "
    "a responder una pregunta de un formulario de postulación. Usá buscar_contexto_del_puesto_en_los_documentos "
    "(una o dos búsquedas) y devolvé solo datos que estén en los documentos: qué pide el puesto y qué valora la empresa "
    "en relación con ESA pregunta. No inventes datos ni escribas la respuesta del candidato."
)


@tool(args_schema=ConsultaALosDocumentosDelPuesto)
async def buscar_contexto_del_puesto_en_los_documentos(consulta: str, empresa: str) -> str:
    """Busca en la oferta de trabajo y en los documentos públicos de la empresa. Devuelve fragmentos con su fuente."""
    if empresa not in listar_empresas_disponibles():
        return f"ERROR: la empresa '{empresa}' no existe. Empresas disponibles: {listar_empresas_disponibles()}"
    resultado: ResultadoDeLaBusqueda = await buscar_fragmentos_relevantes(consulta, empresa)
    if not resultado.fragmentos:
        return "No se encontraron fragmentos para esa búsqueda. Probá con otras palabras."
    return resultado.model_dump_json()


@lru_cache(maxsize=1)
def obtener_agente_investigador() -> CompiledStateGraph:
    return create_agent(
        model=crear_modelo_de_chat(),
        tools=[buscar_contexto_del_puesto_en_los_documentos],
        system_prompt=INSTRUCCIONES_DEL_INVESTIGADOR,
        response_format=ContextoDelPuesto,
    )


async def preparar_contexto_del_puesto_para_la_pregunta(estado: VistaDelInvestigador) -> dict[str, Any]:
    numero_de_pregunta: int = estado["numero_de_pregunta_actual"]
    instruccion: str = (
        f"Empresa: {estado['empresa']}\nPuesto: {estado['puesto']}\n"
        f"Pregunta del formulario: {estado['preguntas_del_formulario'][numero_de_pregunta]}"
    )
    resultado_del_agente: dict[str, Any] = await obtener_agente_investigador().ainvoke({"messages": [HumanMessage(content=instruccion)]})
    contexto: ContextoDelPuesto = resultado_del_agente["structured_response"]
    registro.info("Investigador: %d puntos clave de %s", len(contexto.puntos_clave), contexto.fuentes)
    contexto_guardado: ContextoDelPuestoGuardado = ContextoDelPuestoGuardado(numero_de_pregunta=numero_de_pregunta, **contexto.model_dump())
    return {"contextos_del_puesto": [contexto_guardado.model_dump()]}
