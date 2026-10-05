from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

CARPETA_DE_ESTA_ENTREGA: Path = Path(__file__).parent
CARPETA_DE_DOCUMENTOS: Path = CARPETA_DE_ESTA_ENTREGA / "data"
CARPETA_DE_LA_BASE_VECTORIAL: Path = CARPETA_DE_ESTA_ENTREGA / "vectorstore"
NOMBRE_DE_LA_COLECCION: str = "adecuaciones_pedagogicas"

NOMBRE_DEL_MODELO_DE_EMBEDDINGS: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

TOKENS_POR_FRAGMENTO: int = 500
TOKENS_DE_SOLAPAMIENTO: int = 50
CODIFICACION_DE_TIKTOKEN: str = "cl100k_base"
CANTIDAD_DE_FRAGMENTOS_A_RECUPERAR: int = 4


@lru_cache(maxsize=1)
def obtener_modelo_de_embeddings_compartido() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=NOMBRE_DEL_MODELO_DE_EMBEDDINGS, model_kwargs={"device": "cpu"})
