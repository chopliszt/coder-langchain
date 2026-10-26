from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from app.configuracion import (
    CANTIDAD_DE_FRAGMENTOS_A_RECUPERAR,
    CARPETA_DE_DOCUMENTOS_DEL_PUESTO,
    CARPETA_DE_LA_BASE_VECTORIAL,
    NOMBRE_DE_LA_COLECCION,
    NOMBRE_DEL_MODELO_DE_EMBEDDINGS,
)
from app.contratos_de_datos import FragmentoDeDocumento, ResultadoDeLaBusqueda


@lru_cache(maxsize=1)
def obtener_modelo_de_embeddings_compartido() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=NOMBRE_DEL_MODELO_DE_EMBEDDINGS, model_kwargs={"device": "cpu"})


@lru_cache(maxsize=1)
def obtener_base_vectorial() -> Chroma:
    return Chroma(
        collection_name=NOMBRE_DE_LA_COLECCION,
        embedding_function=obtener_modelo_de_embeddings_compartido(),
        persist_directory=str(CARPETA_DE_LA_BASE_VECTORIAL),
        collection_metadata={"hnsw:space": "cosine"},
    )


def listar_empresas_disponibles() -> list[str]:
    return sorted(carpeta.name for carpeta in CARPETA_DE_DOCUMENTOS_DEL_PUESTO.iterdir() if carpeta.is_dir())


async def buscar_fragmentos_relevantes(consulta: str, empresa: str) -> ResultadoDeLaBusqueda:
    documentos_encontrados: list[Document] = await obtener_base_vectorial().asimilarity_search(
        consulta, k=CANTIDAD_DE_FRAGMENTOS_A_RECUPERAR, filter={"empresa": empresa}
    )
    return ResultadoDeLaBusqueda(
        fragmentos=[
            FragmentoDeDocumento(
                fuente=documento.metadata["fuente"],
                tipo_de_documento=documento.metadata["tipo_de_documento"],
                texto=documento.page_content,
            )
            for documento in documentos_encontrados
        ]
    )
