import operator
from typing import Annotated, Literal

from langgraph.graph import MessagesState
from pydantic import BaseModel, Field

NombreDelSiguientePaso = Literal["Investigador", "Analista", "FINALIZAR"]


class OfertaInvestigada(BaseModel):
    """Datos de la oferta de trabajo encontrada por el Investigador."""

    oferta_id: str = Field(description="Nombre del archivo de la oferta, sin extensión.")
    empresa: str
    puesto: str
    requisitos: list[str] = Field(min_length=1, description="Requisitos obligatorios, copiados tal cual de la oferta.")
    deseables: list[str] = Field(default_factory=list, description="Requisitos deseables, copiados tal cual de la oferta.")


class AnalisisDeCoincidencia(BaseModel):
    """Resultado del Analista al comparar la oferta con el perfil del candidato."""

    porcentaje_de_coincidencia: float = Field(ge=0, le=100, description="Porcentaje de requisitos obligatorios cumplidos.")
    requisitos_cumplidos: list[str]
    requisitos_faltantes: list[str]
    deseables_cumplidos: list[str] = Field(default_factory=list)
    recomendacion: str = Field(min_length=10, description="Qué hacer antes de postularse, en una o dos oraciones.")


class EstadoDelOrquestador(MessagesState):
    siguiente_agente: NombreDelSiguientePaso | None
    tarea_completada: bool
    pasos: int
    oferta_investigada: OfertaInvestigada | None
    analisis_de_coincidencia: AnalisisDeCoincidencia | None
    errores_de_validacion: list[str]
    contribuciones: Annotated[list[dict[str, str]], operator.add]
