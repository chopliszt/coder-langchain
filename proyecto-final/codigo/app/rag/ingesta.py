import hashlib
import logging
import sys
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.configuracion import CARPETA_DE_DOCUMENTOS_DEL_PUESTO, CODIFICACION_DE_TIKTOKEN, TOKENS_DE_SOLAPAMIENTO, TOKENS_POR_FRAGMENTO
from app.rag.busqueda import obtener_base_vectorial

registro: logging.Logger = logging.getLogger("ingesta")


def crear_identificador_deterministico_del_fragmento(ruta_del_documento: Path, indice_del_fragmento: int, contenido: str) -> str:
    huella_del_contenido: str = hashlib.sha256(contenido.encode("utf-8")).hexdigest()[:16]
    return f"{ruta_del_documento.parent.name}/{ruta_del_documento.name}::{indice_del_fragmento}::{huella_del_contenido}"


def dividir_documento_en_fragmentos_con_metadatos(ruta_del_documento: Path) -> list[Document]:
    divisor_de_texto: RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name=CODIFICACION_DE_TIKTOKEN, chunk_size=TOKENS_POR_FRAGMENTO, chunk_overlap=TOKENS_DE_SOLAPAMIENTO
    )
    fragmentos: list[str] = divisor_de_texto.split_text(ruta_del_documento.read_text(encoding="utf-8"))
    return [
        Document(
            id=crear_identificador_deterministico_del_fragmento(ruta_del_documento, indice_del_fragmento, contenido),
            page_content=contenido,
            metadata={
                "empresa": ruta_del_documento.parent.name,
                "tipo_de_documento": ruta_del_documento.stem,
                "fuente": f"{ruta_del_documento.parent.name}/{ruta_del_documento.name}",
                "indice_del_fragmento": indice_del_fragmento,
            },
        )
        for indice_del_fragmento, contenido in enumerate(fragmentos)
    ]


def indexar_documentos_del_puesto(forzar_reindexado: bool = False) -> None:
    base_vectorial = obtener_base_vectorial()
    cantidad_existente: int = base_vectorial._collection.count()
    if cantidad_existente > 0 and not forzar_reindexado:
        registro.info("La base vectorial ya tiene %d fragmentos. No se reindexa (usá --reindexar para forzar).", cantidad_existente)
        return
    documentos: list[Document] = [
        fragmento
        for ruta_del_documento in sorted(CARPETA_DE_DOCUMENTOS_DEL_PUESTO.glob("*/*.md"))
        for fragmento in dividir_documento_en_fragmentos_con_metadatos(ruta_del_documento)
    ]
    base_vectorial.add_documents(documentos, ids=[documento.id for documento in documentos])
    registro.info("Ingesta terminada: %d fragmentos guardados (con metadatos de empresa y tipo de documento).", len(documentos))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s", datefmt="%H:%M:%S")
    indexar_documentos_del_puesto(forzar_reindexado="--reindexar" in sys.argv)
