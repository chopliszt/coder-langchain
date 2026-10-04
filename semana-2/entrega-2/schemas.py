from enum import Enum

from pydantic import BaseModel, Field, field_validator


class NivelDeCriticidad(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class EntidadesTecnicas(BaseModel):
    """Entidades técnicas extraídas de un texto libre (log de error o descripción de arquitectura)."""

    tecnologias: list[str] = Field(
        min_length=1,
        description="Tecnologías, frameworks, bases de datos o herramientas mencionadas explícitamente en el texto.",
    )
    nivel_de_criticidad: NivelDeCriticidad = Field(
        description="Gravedad del problema descripto: baja, media o alta.",
    )
    resumen_tecnico: str = Field(
        min_length=10,
        description="Resumen técnico de una o dos oraciones sobre el contenido del texto.",
    )

    @field_validator("tecnologias")
    @classmethod
    def limpiar_tecnologias_y_rechazar_lista_vacia(cls, tecnologias_recibidas: list[str]) -> list[str]:
        tecnologias_sin_espacios: list[str] = [
            tecnologia.strip() for tecnologia in tecnologias_recibidas if tecnologia.strip()
        ]
        if not tecnologias_sin_espacios:
            raise ValueError("La lista de tecnologías no puede quedar vacía.")
        tecnologias_sin_duplicados: list[str] = list(dict.fromkeys(tecnologias_sin_espacios))
        return tecnologias_sin_duplicados
