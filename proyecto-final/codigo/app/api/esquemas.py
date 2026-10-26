from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.configuracion import MAXIMO_DE_PREGUNTAS_DEL_FORMULARIO
from app.contratos_de_datos import BorradorAprobado, TurnoDeLaEntrevista
from app.rag.busqueda import listar_empresas_disponibles


class PedidoDeNuevaEntrevista(BaseModel):
    empresa: str = Field(examples=["nimbus-edu"], description="Carpeta de la empresa dentro de data/documentos_del_puesto.")
    puesto: str = Field(min_length=3, examples=["Learning Engineer"])
    preguntas_del_formulario: list[str] = Field(
        min_length=1,
        max_length=MAXIMO_DE_PREGUNTAS_DEL_FORMULARIO,
        examples=[["¿Por qué querés trabajar en Nimbus Edu?"]],
    )

    @field_validator("empresa")
    @classmethod
    def verificar_que_la_empresa_tenga_documentos(cls, empresa: str) -> str:
        if empresa not in listar_empresas_disponibles():
            raise ValueError(f"No hay documentos para '{empresa}'. Empresas disponibles: {listar_empresas_disponibles()}")
        return empresa

    @field_validator("preguntas_del_formulario")
    @classmethod
    def verificar_que_las_preguntas_no_esten_vacias(cls, preguntas: list[str]) -> list[str]:
        if any(len(pregunta.strip()) < 10 for pregunta in preguntas):
            raise ValueError("Cada pregunta del formulario tiene que tener al menos 10 caracteres.")
        return preguntas


class EstadoPublicoDeLaEntrevista(BaseModel):
    identificador_de_la_entrevista: str
    estado: Literal["esperando_respuesta", "terminada"]
    numero_de_pregunta_del_formulario: int | None = None
    pregunta_pendiente: str | None = None
    borradores_aprobados: list[BorradorAprobado]


class DetalleDeLaEntrevista(EstadoPublicoDeLaEntrevista):
    empresa: str
    puesto: str
    preguntas_del_formulario: list[str]
    transcripcion: list[TurnoDeLaEntrevista]
