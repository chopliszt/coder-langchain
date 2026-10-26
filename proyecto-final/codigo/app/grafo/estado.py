import operator
from typing import Annotated, Any, TypedDict

from app.contratos_de_datos import (
    BorradorAprobado,
    BorradorPropuestoGuardado,
    ContextoDelPuestoGuardado,
    NombreDelSiguientePaso,
    TurnoDeLaEntrevista,
)

RegistrosQueSoloCrecen = Annotated[list[dict[str, Any]], operator.add]


class EstadoDeLaEntrevista(TypedDict):
    empresa: str
    puesto: str
    preguntas_del_formulario: list[str]
    numero_de_pregunta_actual: int
    siguiente_paso: NombreDelSiguientePaso | None
    contextos_del_puesto: RegistrosQueSoloCrecen
    transcripcion: RegistrosQueSoloCrecen
    borradores_propuestos: RegistrosQueSoloCrecen
    errores_de_validacion: list[str]
    borradores_aprobados: RegistrosQueSoloCrecen


class VistaDelSupervisor(TypedDict):
    preguntas_del_formulario: list[str]
    numero_de_pregunta_actual: int
    contextos_del_puesto: RegistrosQueSoloCrecen
    transcripcion: RegistrosQueSoloCrecen
    borradores_propuestos: RegistrosQueSoloCrecen
    errores_de_validacion: list[str]
    borradores_aprobados: RegistrosQueSoloCrecen


class VistaDelInvestigador(TypedDict):
    empresa: str
    puesto: str
    preguntas_del_formulario: list[str]
    numero_de_pregunta_actual: int


class VistaDelEntrevistador(TypedDict):
    empresa: str
    puesto: str
    preguntas_del_formulario: list[str]
    numero_de_pregunta_actual: int
    contextos_del_puesto: RegistrosQueSoloCrecen
    transcripcion: RegistrosQueSoloCrecen


class VistaDelCandidato(TypedDict):
    numero_de_pregunta_actual: int
    transcripcion: RegistrosQueSoloCrecen


class VistaDelRedactor(TypedDict):
    preguntas_del_formulario: list[str]
    numero_de_pregunta_actual: int
    transcripcion: RegistrosQueSoloCrecen
    errores_de_validacion: list[str]


class VistaDelValidador(TypedDict):
    preguntas_del_formulario: list[str]
    numero_de_pregunta_actual: int
    transcripcion: RegistrosQueSoloCrecen
    borradores_propuestos: RegistrosQueSoloCrecen


def crear_estado_inicial(empresa: str, puesto: str, preguntas_del_formulario: list[str]) -> EstadoDeLaEntrevista:
    return {
        "empresa": empresa,
        "puesto": puesto,
        "preguntas_del_formulario": preguntas_del_formulario,
        "numero_de_pregunta_actual": 0,
        "siguiente_paso": None,
        "contextos_del_puesto": [],
        "transcripcion": [],
        "borradores_propuestos": [],
        "errores_de_validacion": [],
        "borradores_aprobados": [],
    }


def leer_turnos_de_la_pregunta(transcripcion: list[dict[str, Any]], numero_de_pregunta: int) -> list[TurnoDeLaEntrevista]:
    turnos: list[TurnoDeLaEntrevista] = [TurnoDeLaEntrevista.model_validate(turno) for turno in transcripcion]
    return [turno for turno in turnos if turno.numero_de_pregunta == numero_de_pregunta]


def leer_respuestas_del_candidato(transcripcion: list[dict[str, Any]], numero_de_pregunta: int) -> list[str]:
    return [turno.texto for turno in leer_turnos_de_la_pregunta(transcripcion, numero_de_pregunta) if turno.autor == "candidato"]


def convertir_turnos_en_texto(turnos: list[TurnoDeLaEntrevista]) -> str:
    etiquetas_por_autor: dict[str, str] = {"entrevistador": "Entrevistador", "candidato": "Candidato"}
    return "\n".join(f"{etiquetas_por_autor[turno.autor]}: {turno.texto}" for turno in turnos) or "(todavía no hay conversación)"


def leer_contexto_de_la_pregunta(contextos_del_puesto: list[dict[str, Any]], numero_de_pregunta: int) -> ContextoDelPuestoGuardado | None:
    for contexto in contextos_del_puesto:
        contexto_validado: ContextoDelPuestoGuardado = ContextoDelPuestoGuardado.model_validate(contexto)
        if contexto_validado.numero_de_pregunta == numero_de_pregunta:
            return contexto_validado
    return None


def leer_borradores_propuestos_de_la_pregunta(
    borradores_propuestos: list[dict[str, Any]], numero_de_pregunta: int
) -> list[BorradorPropuestoGuardado]:
    borradores: list[BorradorPropuestoGuardado] = [BorradorPropuestoGuardado.model_validate(borrador) for borrador in borradores_propuestos]
    return [borrador for borrador in borradores if borrador.numero_de_pregunta == numero_de_pregunta]


def la_pregunta_tiene_borrador_aprobado(borradores_aprobados: list[dict[str, Any]], numero_de_pregunta: int) -> bool:
    return any(BorradorAprobado.model_validate(borrador).numero_de_pregunta == numero_de_pregunta for borrador in borradores_aprobados)
