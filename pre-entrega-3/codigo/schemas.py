from pydantic import BaseModel, Field

FRASE_CUANDO_NO_HAY_INFORMACION: str = "No lo sé"


class RespuestaGeneradaPorElModelo(BaseModel):
    """Respuesta a la pregunta del usuario basada exclusivamente en el CONTEXTO recibido."""

    respuesta: str = Field(
        description=f"Respuesta basada solo en el CONTEXTO. Si el CONTEXTO no la contiene, exactamente: '{FRASE_CUANDO_NO_HAY_INFORMACION}'.",
    )
    la_respuesta_esta_en_el_contexto: bool = Field(
        description="true solo si la respuesta sale del CONTEXTO; false si se respondió 'No lo sé'.",
    )


class FuenteConsultada(BaseModel):
    archivo: str
    indice_del_fragmento: int


class RespuestaRAG(BaseModel):
    pregunta: str
    respuesta: str
    la_respuesta_esta_en_el_contexto: bool
    fuentes: list[FuenteConsultada] = Field(description="Fragmentos que respaldan la respuesta. Vacío si la respuesta es 'No lo sé'.")
    cantidad_de_fragmentos_recuperados: int
