import hashlib
import logging
import re
import sys
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from langchain_text_splitters import RecursiveCharacterTextSplitter

from configuracion import (
    CARPETA_DE_DOCUMENTOS,
    CARPETA_DE_LA_BASE_VECTORIAL,
    CODIFICACION_DE_TIKTOKEN,
    NOMBRE_DE_LA_COLECCION,
    TOKENS_DE_SOLAPAMIENTO,
    TOKENS_POR_FRAGMENTO,
    obtener_modelo_de_embeddings_compartido,
)

registro: logging.Logger = logging.getLogger("ingesta")


def limpiar_texto_crudo(texto_crudo: str) -> str:
    texto_sin_caracteres_invisibles: str = re.sub(r"[​ \t\r]", " ", texto_crudo)
    texto_sin_espacios_repetidos: str = re.sub(r"[ ]{2,}", " ", texto_sin_caracteres_invisibles)
    texto_sin_lineas_vacias_repetidas: str = re.sub(r"\n{3,}", "\n\n", texto_sin_espacios_repetidos)
    return texto_sin_lineas_vacias_repetidas.strip()


def crear_identificador_deterministico_del_fragmento(nombre_del_archivo: str, indice_del_fragmento: int, contenido: str) -> str:
    huella_del_contenido: str = hashlib.sha256(contenido.encode("utf-8")).hexdigest()[:16]
    return f"{nombre_del_archivo}::{indice_del_fragmento}::{huella_del_contenido}"


def crear_divisor_de_texto_por_tokens() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name=CODIFICACION_DE_TIKTOKEN,
        chunk_size=TOKENS_POR_FRAGMENTO,
        chunk_overlap=TOKENS_DE_SOLAPAMIENTO,
    )


def abrir_coleccion_persistente() -> Collection:
    cliente_persistente: chromadb.ClientAPI = chromadb.PersistentClient(path=str(CARPETA_DE_LA_BASE_VECTORIAL))
    return cliente_persistente.get_or_create_collection(
        name=NOMBRE_DE_LA_COLECCION,
        metadata={"hnsw:space": "cosine"},
    )


def indexar_documentos_de_la_carpeta_data(coleccion: Collection) -> int:
    divisor_de_texto: RecursiveCharacterTextSplitter = crear_divisor_de_texto_por_tokens()
    modelo_de_embeddings = obtener_modelo_de_embeddings_compartido()

    identificadores: list[str] = []
    contenidos: list[str] = []
    metadatos: list[dict[str, str | int]] = []

    rutas_de_documentos: list[Path] = sorted([*CARPETA_DE_DOCUMENTOS.glob("*.md"), *CARPETA_DE_DOCUMENTOS.glob("*.txt")])
    for ruta_del_documento in rutas_de_documentos:
        texto_limpio: str = limpiar_texto_crudo(ruta_del_documento.read_text(encoding="utf-8"))
        fragmentos_del_documento: list[str] = divisor_de_texto.split_text(texto_limpio)
        registro.info("%s -> %d fragmentos", ruta_del_documento.name, len(fragmentos_del_documento))

        for indice_del_fragmento, contenido_del_fragmento in enumerate(fragmentos_del_documento):
            identificadores.append(
                crear_identificador_deterministico_del_fragmento(ruta_del_documento.name, indice_del_fragmento, contenido_del_fragmento)
            )
            contenidos.append(contenido_del_fragmento)
            metadatos.append({"fuente": ruta_del_documento.name, "indice_del_fragmento": indice_del_fragmento})

    vectores: list[list[float]] = modelo_de_embeddings.embed_documents(contenidos)
    coleccion.upsert(ids=identificadores, documents=contenidos, metadatas=metadatos, embeddings=vectores)
    return len(identificadores)


def ejecutar_ingesta_si_hace_falta(forzar_reindexado: bool = False) -> None:
    coleccion: Collection = abrir_coleccion_persistente()
    cantidad_de_fragmentos_existentes: int = coleccion.count()

    if cantidad_de_fragmentos_existentes > 0 and not forzar_reindexado:
        registro.info(
            "La colección '%s' ya tiene %d fragmentos. No se reindexa (usá --reindexar para forzar).",
            NOMBRE_DE_LA_COLECCION,
            cantidad_de_fragmentos_existentes,
        )
        return

    cantidad_de_fragmentos_indexados: int = indexar_documentos_de_la_carpeta_data(coleccion)
    registro.info("Ingesta terminada: %d fragmentos guardados con upsert en '%s'.", cantidad_de_fragmentos_indexados, NOMBRE_DE_LA_COLECCION)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    ejecutar_ingesta_si_hace_falta(forzar_reindexado="--reindexar" in sys.argv)
