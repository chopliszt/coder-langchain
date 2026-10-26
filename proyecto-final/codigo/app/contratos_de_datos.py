from typing import Literal

from pydantic import BaseModel, Field

AutorDelTurno = Literal["entrevistador", "candidato"]
NombreDelSiguientePaso = Literal["Investigador", "Entrevistador", "Redactor", "FINALIZAR"]


class TurnoDeLaEntrevista(BaseModel):
    numero_de_pregunta: int = Field(ge=0, description="Índice de la pregunta del formulario a la que pertenece este turno.")
    autor: AutorDelTurno
    texto: str = Field(min_length=1)


class RespuestaDelCandidato(BaseModel):
    texto: str = Field(min_length=1, max_length=5000, examples=["Coordiné la migración de 40 docentes a la plataforma nueva..."])


class ConsultaALosDocumentosDelPuesto(BaseModel):
    consulta: str = Field(min_length=3, description="Qué buscar en la oferta y en los documentos de la empresa, por ejemplo 'valores de la empresa'.")
    empresa: str = Field(min_length=2, description="Identificador de la empresa tal cual aparece en la instrucción, por ejemplo 'pampa-ai'.")


class FragmentoDeDocumento(BaseModel):
    fuente: str
    tipo_de_documento: str
    texto: str


class ResultadoDeLaBusqueda(BaseModel):
    fragmentos: list[FragmentoDeDocumento]


class ContextoDelPuesto(BaseModel):
    puntos_clave: list[str] = Field(
        min_length=1, max_length=5, description="Datos del puesto o de la empresa útiles para esta pregunta, una oración cada uno."
    )
    fuentes: list[str] = Field(min_length=1, description="Nombres de los documentos de donde salieron los puntos clave.")


class ContextoDelPuestoGuardado(ContextoDelPuesto):
    numero_de_pregunta: int = Field(ge=0)


class PreguntaDelEntrevistador(BaseModel):
    pregunta: str = Field(min_length=10, max_length=400, description="Una sola pregunta abierta y corta para el candidato.")


class DecisionDelSupervisor(BaseModel):
    siguiente: Literal["Entrevistador", "Redactor"] = Field(
        description="Entrevistador si la respuesta todavía es vaga o le falta un ejemplo concreto; Redactor si ya alcanza para un borrador."
    )
    razon: str = Field(description="Justificación breve de la decisión.")


class BorradorPropuesto(BaseModel):
    fragmentos_textuales: list[str] = Field(
        min_length=1, description="Fragmentos copiados LITERALMENTE de las respuestas del candidato, en el orden en que deben leerse."
    )


class BorradorPropuestoGuardado(BorradorPropuesto):
    numero_de_pregunta: int = Field(ge=0)


class BorradorAprobado(BaseModel):
    numero_de_pregunta: int = Field(ge=0)
    pregunta_del_formulario: str
    texto: str
    fragmentos_descartados: list[str] = Field(default_factory=list, description="Fragmentos que no estaban en la transcripción.")
