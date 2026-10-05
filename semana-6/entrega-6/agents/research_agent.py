import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph.state import CompiledStateGraph

from proveedor_de_modelos import crear_modelo_de_chat
from state import EstadoDelOrquestador, OfertaInvestigada

CARPETA_DE_OFERTAS: Path = Path(__file__).parent.parent / "data" / "ofertas"

INSTRUCCIONES_DEL_INVESTIGADOR: str = (
    "Sos el agente Investigador. Tu única función es encontrar la oferta de trabajo que pide el usuario "
    "usando tus herramientas y extraer empresa, puesto, requisitos y deseables COPIADOS TAL CUAL de la oferta. "
    "Primero buscá con buscar_ofertas_de_trabajo y después leé la oferta completa con leer_oferta_completa. "
    "No evalúes si el candidato encaja: eso lo hace otro agente."
)


def separar_en_palabras(texto: str) -> set[str]:
    return set(re.findall(r"\w+", texto.lower()))


@tool
def buscar_ofertas_de_trabajo(consulta: str) -> str:
    """Busca ofertas de trabajo guardadas por empresa, puesto o tecnología (por ejemplo 'Pampa AI AI Engineer').
    Devuelve hasta 2 ofertas con su oferta_id y su título. Usá después leer_oferta_completa con el oferta_id."""
    palabras_de_la_consulta: set[str] = separar_en_palabras(consulta)
    ofertas_con_puntaje: list[tuple[int, Path]] = [
        (len(palabras_de_la_consulta & separar_en_palabras(ruta.read_text(encoding="utf-8"))), ruta)
        for ruta in CARPETA_DE_OFERTAS.glob("*.md")
    ]
    ofertas_relevantes: list[tuple[int, Path]] = [oferta for oferta in sorted(ofertas_con_puntaje, reverse=True) if oferta[0] > 0][:2]
    if not ofertas_relevantes:
        return "ERROR: no se encontró ninguna oferta para esa búsqueda. Probá con el nombre de la empresa o el puesto."
    return "\n".join(
        f"oferta_id={ruta.stem} | {ruta.read_text(encoding='utf-8').splitlines()[0].lstrip('# ')}" for _, ruta in ofertas_relevantes
    )


@tool
def leer_oferta_completa(oferta_id: str) -> str:
    """Devuelve el texto completo de una oferta de trabajo (requisitos, deseables, condiciones) a partir de su oferta_id."""
    ruta_de_la_oferta: Path = CARPETA_DE_OFERTAS / f"{oferta_id}.md"
    if not ruta_de_la_oferta.exists():
        return f"ERROR: no existe la oferta '{oferta_id}'. Usá buscar_ofertas_de_trabajo para obtener un oferta_id válido."
    return ruta_de_la_oferta.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def obtener_agente_investigador() -> CompiledStateGraph:
    return create_agent(
        model=crear_modelo_de_chat(),
        tools=[buscar_ofertas_de_trabajo, leer_oferta_completa],
        system_prompt=INSTRUCCIONES_DEL_INVESTIGADOR,
        response_format=OfertaInvestigada,
    )


def armar_instruccion_minima_para_el_investigador(estado: EstadoDelOrquestador) -> str:
    pedido_del_usuario: str = str(estado["messages"][0].content)
    errores_a_corregir: list[str] = estado.get("errores_de_validacion", [])
    if errores_a_corregir:
        return f"{pedido_del_usuario}\n\nTu intento anterior tuvo estos errores, corregilos: {errores_a_corregir}"
    return pedido_del_usuario


async def nodo_investigador(estado: EstadoDelOrquestador) -> dict[str, Any]:
    resultado_del_agente: dict[str, Any] = await obtener_agente_investigador().ainvoke(
        {"messages": [HumanMessage(content=armar_instruccion_minima_para_el_investigador(estado))]}
    )
    oferta_investigada: OfertaInvestigada = resultado_del_agente["structured_response"]
    resumen_del_aporte: str = f"Oferta encontrada: {oferta_investigada.puesto} en {oferta_investigada.empresa}. Requisitos: {oferta_investigada.requisitos}"
    return {
        "oferta_investigada": oferta_investigada,
        "messages": [AIMessage(content=resumen_del_aporte, name="Investigador")],
        "contribuciones": [{"agente": "Investigador", "aporte": oferta_investigada.model_dump_json()}],
        "pasos": estado.get("pasos", 0) + 1,
    }
