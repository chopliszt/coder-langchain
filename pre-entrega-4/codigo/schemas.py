from pydantic import BaseModel, Field


class MetadatosDelFragmento(BaseModel):
    documento_id: str = Field(description="Nombre del archivo sin extensión. Es el ID que usa el golden set.")
    fuente: str = Field(description="Nombre del archivo original.")
    categoria: str
    etiquetas: list[str]
    pagina: int = Field(ge=1, description="Número de sección del Markdown donde empieza el fragmento (equivalente a página).")
    seccion: str
    indice_del_fragmento: int = Field(ge=0)


class CasoDelGoldenSet(BaseModel):
    pregunta: str
    documento_id_esperado: str


class ResultadoDeUnaPregunta(BaseModel):
    pregunta: str
    documento_id_esperado: str
    documentos_recuperados: list[str]
    recall_en_5: float
    precision_en_5: float
