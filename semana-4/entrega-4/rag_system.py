import logging
import re
import unicodedata

from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

from configuracion import (
    CANTIDAD_DE_DOCUMENTOS_A_DEVOLVER,
    NOMBRE_DEL_INDICE,
    NOMBRE_DEL_NAMESPACE,
    PESO_DE_LA_BUSQUEDA_LEXICA,
    PESO_DE_LA_BUSQUEDA_SEMANTICA,
    leer_clave_de_pinecone,
    obtener_modelo_de_embeddings_compartido,
)
from ingest import cargar_y_fragmentar_documentos

registro: logging.Logger = logging.getLogger("rag_system")


def separar_en_palabras_normalizadas(texto: str) -> list[str]:
    texto_sin_tildes: str = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.findall(r"\w+", texto_sin_tildes.lower())


def crear_buscador_por_palabras_clave(cantidad_de_documentos: int) -> BM25Retriever:
    buscador_bm25: BM25Retriever = BM25Retriever.from_documents(
        cargar_y_fragmentar_documentos(),
        preprocess_func=separar_en_palabras_normalizadas,
    )
    buscador_bm25.k = cantidad_de_documentos
    return buscador_bm25


def crear_buscador_por_significado_en_pinecone(cantidad_de_documentos: int) -> VectorStoreRetriever:
    base_vectorial_en_la_nube: PineconeVectorStore = PineconeVectorStore(
        index=Pinecone(api_key=leer_clave_de_pinecone()).Index(NOMBRE_DEL_INDICE),
        embedding=obtener_modelo_de_embeddings_compartido(),
        namespace=NOMBRE_DEL_NAMESPACE,
    )
    return base_vectorial_en_la_nube.as_retriever(search_kwargs={"k": cantidad_de_documentos, "namespace": NOMBRE_DEL_NAMESPACE})


class RAGSystem:
    def __init__(self, cantidad_de_documentos: int = CANTIDAD_DE_DOCUMENTOS_A_DEVOLVER) -> None:
        self.cantidad_de_documentos: int = cantidad_de_documentos
        self.buscador_por_palabras_clave: BM25Retriever = crear_buscador_por_palabras_clave(cantidad_de_documentos)
        self.buscador_por_significado: VectorStoreRetriever = crear_buscador_por_significado_en_pinecone(cantidad_de_documentos)
        self.buscador_hibrido: EnsembleRetriever = EnsembleRetriever(
            retrievers=[self.buscador_por_palabras_clave, self.buscador_por_significado],
            weights=[PESO_DE_LA_BUSQUEDA_LEXICA, PESO_DE_LA_BUSQUEDA_SEMANTICA],
        )

    async def recuperar_top_5_solo_por_palabras_clave(self, consulta: str) -> list[Document]:
        return (await self.buscador_por_palabras_clave.ainvoke(consulta))[: self.cantidad_de_documentos]

    async def recuperar_top_5_solo_por_significado(self, consulta: str) -> list[Document]:
        return (await self.buscador_por_significado.ainvoke(consulta))[: self.cantidad_de_documentos]

    async def recuperar_top_5_documentos(self, consulta: str) -> list[Document]:
        fragmentos_fusionados: list[Document] = await self.buscador_hibrido.ainvoke(consulta)
        registro.info("Híbrido '%s' -> %s", consulta, [fragmento.metadata["documento_id"] for fragmento in fragmentos_fusionados[: self.cantidad_de_documentos]])
        return fragmentos_fusionados[: self.cantidad_de_documentos]
