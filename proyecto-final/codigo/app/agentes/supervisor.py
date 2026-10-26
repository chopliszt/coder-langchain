import logging
from functools import lru_cache
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.configuracion import MAXIMO_DE_PREGUNTAS_DEL_ENTREVISTADOR_POR_PREGUNTA
from app.contratos_de_datos import DecisionDelSupervisor, NombreDelSiguientePaso, TurnoDeLaEntrevista
from app.grafo.estado import (
    VistaDelSupervisor,
    convertir_turnos_en_texto,
    la_pregunta_tiene_borrador_aprobado,
    leer_borradores_propuestos_de_la_pregunta,
    leer_contexto_de_la_pregunta,
    leer_turnos_de_la_pregunta,
)
from app.proveedor_de_modelos import crear_cadena_con_salida_validada

registro: logging.Logger = logging.getLogger("supervisor")

plantilla_del_supervisor: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Sos el Supervisor de una entrevista que ayuda a un candidato a responder una pregunta de un formulario de postulación "
            "con sus propias palabras. NO hacés preguntas ni redactás: solo decidís quién sigue.\n"
            "- Entrevistador: si la última respuesta es vaga, muy corta o le falta un ejemplo concreto, un resultado o un porqué.\n"
            "- Redactor: si las respuestas ya tienen material suficiente y concreto para armar un borrador.",
        ),
        ("human", "Pregunta del formulario: {pregunta_del_formulario}\n\nConversación hasta ahora:\n{conversacion}"),
    ]
)


@lru_cache(maxsize=1)
def obtener_cadena_del_supervisor() -> Runnable:
    return crear_cadena_con_salida_validada(plantilla_del_supervisor, DecisionDelSupervisor)


def decidir_por_reglas_de_codigo(estado: VistaDelSupervisor, numero_de_pregunta: int) -> NombreDelSiguientePaso | None:
    if numero_de_pregunta >= len(estado["preguntas_del_formulario"]):
        return "FINALIZAR"
    if leer_contexto_de_la_pregunta(estado["contextos_del_puesto"], numero_de_pregunta) is None:
        return "Investigador"
    turnos: list[TurnoDeLaEntrevista] = leer_turnos_de_la_pregunta(estado["transcripcion"], numero_de_pregunta)
    if not turnos:
        return "Entrevistador"
    if estado["errores_de_validacion"] and leer_borradores_propuestos_de_la_pregunta(estado["borradores_propuestos"], numero_de_pregunta):
        return "Redactor"
    preguntas_ya_hechas: int = sum(1 for turno in turnos if turno.autor == "entrevistador")
    if preguntas_ya_hechas >= MAXIMO_DE_PREGUNTAS_DEL_ENTREVISTADOR_POR_PREGUNTA:
        return "Redactor"
    return None


async def decidir_el_siguiente_paso_de_la_entrevista(estado: VistaDelSupervisor) -> dict[str, Any]:
    numero_de_pregunta: int = estado["numero_de_pregunta_actual"]
    if la_pregunta_tiene_borrador_aprobado(estado["borradores_aprobados"], numero_de_pregunta):
        numero_de_pregunta += 1

    paso_decidido_por_codigo: NombreDelSiguientePaso | None = decidir_por_reglas_de_codigo(estado, numero_de_pregunta)
    if paso_decidido_por_codigo is not None:
        registro.info("Supervisor (regla de código) -> %s", paso_decidido_por_codigo)
        return {"siguiente_paso": paso_decidido_por_codigo, "numero_de_pregunta_actual": numero_de_pregunta}

    decision: DecisionDelSupervisor = await obtener_cadena_del_supervisor().ainvoke(
        {
            "pregunta_del_formulario": estado["preguntas_del_formulario"][numero_de_pregunta],
            "conversacion": convertir_turnos_en_texto(leer_turnos_de_la_pregunta(estado["transcripcion"], numero_de_pregunta)),
        }
    )
    registro.info("Supervisor (LLM) -> %s (%s)", decision.siguiente, decision.razon)
    return {"siguiente_paso": decision.siguiente, "numero_de_pregunta_actual": numero_de_pregunta}
