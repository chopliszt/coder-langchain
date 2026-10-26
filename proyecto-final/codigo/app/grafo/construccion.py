from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agentes.candidato import pausar_hasta_recibir_la_respuesta
from app.agentes.entrevistador import formular_la_siguiente_pregunta_al_candidato
from app.agentes.investigador import preparar_contexto_del_puesto_para_la_pregunta
from app.agentes.redactor import armar_borrador_con_las_frases_del_candidato
from app.agentes.supervisor import decidir_el_siguiente_paso_de_la_entrevista
from app.agentes.validador import descartar_frases_que_no_estan_en_la_transcripcion
from app.contratos_de_datos import NombreDelSiguientePaso
from app.grafo.estado import (
    EstadoDeLaEntrevista,
    VistaDelCandidato,
    VistaDelEntrevistador,
    VistaDelInvestigador,
    VistaDelRedactor,
    VistaDelSupervisor,
    VistaDelValidador,
)


def elegir_ruta_despues_del_supervisor(estado: EstadoDeLaEntrevista) -> NombreDelSiguientePaso:
    return estado["siguiente_paso"] or "FINALIZAR"


def construir_grafo_de_la_entrevista() -> StateGraph:
    grafo: StateGraph = StateGraph(EstadoDeLaEntrevista)
    grafo.add_node("Supervisor", decidir_el_siguiente_paso_de_la_entrevista, input_schema=VistaDelSupervisor)
    grafo.add_node("Investigador", preparar_contexto_del_puesto_para_la_pregunta, input_schema=VistaDelInvestigador)
    grafo.add_node("Entrevistador", formular_la_siguiente_pregunta_al_candidato, input_schema=VistaDelEntrevistador)
    grafo.add_node("EsperarRespuestaDelCandidato", pausar_hasta_recibir_la_respuesta, input_schema=VistaDelCandidato)
    grafo.add_node("Redactor", armar_borrador_con_las_frases_del_candidato, input_schema=VistaDelRedactor)
    grafo.add_node("Validador", descartar_frases_que_no_estan_en_la_transcripcion, input_schema=VistaDelValidador)

    grafo.add_edge(START, "Supervisor")
    grafo.add_conditional_edges(
        "Supervisor",
        elegir_ruta_despues_del_supervisor,
        {"Investigador": "Investigador", "Entrevistador": "Entrevistador", "Redactor": "Redactor", "FINALIZAR": END},
    )
    grafo.add_edge("Investigador", "Supervisor")
    grafo.add_edge("Entrevistador", "EsperarRespuestaDelCandidato")
    grafo.add_edge("EsperarRespuestaDelCandidato", "Supervisor")
    grafo.add_edge("Redactor", "Validador")
    grafo.add_edge("Validador", "Supervisor")
    return grafo


def compilar_grafo_con_persistencia(guardador_de_checkpoints: BaseCheckpointSaver | None) -> CompiledStateGraph:
    return construir_grafo_de_la_entrevista().compile(checkpointer=guardador_de_checkpoints)
