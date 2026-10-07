import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

CARPETA_DE_ESTA_ENTREGA: Path = Path(__file__).parent
CARPETA_DE_DOCUMENTOS: Path = CARPETA_DE_ESTA_ENTREGA / "data"
RUTA_DEL_GOLDEN_SET: Path = CARPETA_DE_ESTA_ENTREGA / "golden_set.json"

NOMBRE_DEL_INDICE: str = os.getenv("INDEX_NAME", "manual-ib")
NOMBRE_DEL_NAMESPACE: str = os.getenv("PINECONE_NAMESPACE", "manual-ib-colegio")
NUBE_DEL_INDICE: str = "aws"
REGION_DEL_INDICE: str = "us-east-1"
METRICA_DE_SIMILITUD: str = "cosine"

NOMBRE_DEL_MODELO_DE_EMBEDDINGS: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

TOKENS_POR_FRAGMENTO: int = 500
TOKENS_DE_SOLAPAMIENTO: int = 75
CODIFICACION_DE_TIKTOKEN: str = "cl100k_base"
TAMANIO_DEL_LOTE_DE_SUBIDA: int = 100
CANTIDAD_DE_DOCUMENTOS_A_DEVOLVER: int = 5
PESO_DE_LA_BUSQUEDA_LEXICA: float = 0.5
PESO_DE_LA_BUSQUEDA_SEMANTICA: float = 0.5

CATEGORIA_Y_ETIQUETAS_POR_DOCUMENTO: dict[str, tuple[str, list[str]]] = {
    "monografia_EE": ("componente_troncal", ["EE", "monografia", "investigacion", "RPPF"]),
    "teoria_del_conocimiento_TOK": ("componente_troncal", ["TOK", "ensayo", "exposicion"]),
    "creatividad_actividad_servicio_CAS": ("componente_troncal", ["CAS", "servicio", "portafolio"]),
    "evaluacion_interna_IA": ("evaluacion", ["IA", "evaluacion_interna", "moderacion"]),
    "reglamento_de_examenes_de_mayo": ("evaluacion", ["examenes", "convocatoria", "reglamento"]),
}


@lru_cache(maxsize=1)
def obtener_modelo_de_embeddings_compartido() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=NOMBRE_DEL_MODELO_DE_EMBEDDINGS, model_kwargs={"device": "cpu"})


def calcular_dimension_del_modelo_de_embeddings() -> int:
    vector_de_prueba: list[float] = obtener_modelo_de_embeddings_compartido().embed_query("prueba de dimensión")
    return len(vector_de_prueba)


def leer_clave_de_pinecone() -> str:
    clave_de_pinecone: str | None = os.getenv("PINECONE_API_KEY")
    if not clave_de_pinecone:
        raise RuntimeError("Falta PINECONE_API_KEY en el archivo .env (ver .env.example).")
    return clave_de_pinecone
