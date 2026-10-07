import hashlib
import logging
import re
import sys
from pathlib import Path

from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone

from configuracion import (
    CARPETA_DE_DOCUMENTOS,
    CATEGORIA_Y_ETIQUETAS_POR_DOCUMENTO,
    CODIFICACION_DE_TIKTOKEN,
    NOMBRE_DEL_INDICE,
    NOMBRE_DEL_NAMESPACE,
    TAMANIO_DEL_LOTE_DE_SUBIDA,
    TOKENS_DE_SOLAPAMIENTO,
    TOKENS_POR_FRAGMENTO,
    leer_clave_de_pinecone,
    obtener_modelo_de_embeddings_compartido,
)
from schemas import MetadatosDelFragmento

registro: logging.Logger = logging.getLogger("ingesta")

PATRON_DE_TITULO_DE_SECCION: re.Pattern[str] = re.compile(r"^## (.+)$", re.MULTILINE)


def limpiar_texto_crudo(texto_crudo: str) -> str:
    texto_sin_avisos_de_cita: str = re.sub(r"^> .*$", "", texto_crudo, flags=re.MULTILINE)
    texto_sin_espacios_repetidos: str = re.sub(r"[ \t]{2,}", " ", texto_sin_avisos_de_cita)
    return re.sub(r"\n{3,}", "\n\n", texto_sin_espacios_repetidos).strip()


def encontrar_seccion_donde_empieza_el_fragmento(texto_completo: str, posicion_de_inicio: int) -> tuple[int, str]:
    todos_los_titulos: list[re.Match[str]] = list(PATRON_DE_TITULO_DE_SECCION.finditer(texto_completo))
    titulos_anteriores: list[re.Match[str]] = [titulo for titulo in todos_los_titulos if titulo.start() <= posicion_de_inicio]
    if not titulos_anteriores:
        return 1, todos_los_titulos[0].group(1).strip()
    return len(titulos_anteriores), titulos_anteriores[-1].group(1).strip()


def crear_identificador_deterministico(documento_id: str, indice_del_fragmento: int, contenido: str) -> str:
    huella_del_contenido: str = hashlib.sha256(contenido.encode("utf-8")).hexdigest()[:12]
    return f"{documento_id}-{indice_del_fragmento}-{huella_del_contenido}"


def cargar_y_fragmentar_documentos() -> list[Document]:
    divisor_de_texto: RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name=CODIFICACION_DE_TIKTOKEN,
        chunk_size=TOKENS_POR_FRAGMENTO,
        chunk_overlap=TOKENS_DE_SOLAPAMIENTO,
    )
    fragmentos_con_metadatos: list[Document] = []

    for ruta_del_documento in sorted(CARPETA_DE_DOCUMENTOS.glob("*.md")):
        documento_id: str = ruta_del_documento.stem
        categoria, etiquetas = CATEGORIA_Y_ETIQUETAS_POR_DOCUMENTO[documento_id]
        texto_limpio: str = limpiar_texto_crudo(ruta_del_documento.read_text(encoding="utf-8"))
        fragmentos_del_documento: list[Document] = divisor_de_texto.create_documents([texto_limpio])

        for indice_del_fragmento, fragmento in enumerate(fragmentos_del_documento):
            posicion_de_inicio: int = texto_limpio.find(fragmento.page_content)
            numero_de_seccion, titulo_de_seccion = encontrar_seccion_donde_empieza_el_fragmento(texto_limpio, posicion_de_inicio)
            metadatos_validados: MetadatosDelFragmento = MetadatosDelFragmento(
                documento_id=documento_id,
                fuente=ruta_del_documento.name,
                categoria=categoria,
                etiquetas=etiquetas,
                pagina=numero_de_seccion,
                seccion=titulo_de_seccion,
                indice_del_fragmento=indice_del_fragmento,
            )
            fragmentos_con_metadatos.append(
                Document(
                    id=crear_identificador_deterministico(documento_id, indice_del_fragmento, fragmento.page_content),
                    page_content=fragmento.page_content,
                    metadata=metadatos_validados.model_dump(),
                )
            )
        registro.info("%s -> %d fragmentos", ruta_del_documento.name, len(fragmentos_del_documento))

    return fragmentos_con_metadatos


def contar_vectores_en_el_namespace(cliente_de_pinecone: Pinecone) -> int:
    estadisticas_del_indice = cliente_de_pinecone.Index(NOMBRE_DEL_INDICE).describe_index_stats()
    namespace_actual = estadisticas_del_indice.namespaces.get(NOMBRE_DEL_NAMESPACE)
    return namespace_actual.vector_count if namespace_actual else 0


def subir_fragmentos_a_pinecone(forzar_resubida: bool = False) -> None:
    cliente_de_pinecone: Pinecone = Pinecone(api_key=leer_clave_de_pinecone())
    fragmentos: list[Document] = cargar_y_fragmentar_documentos()

    cantidad_de_vectores_existentes: int = contar_vectores_en_el_namespace(cliente_de_pinecone)
    if cantidad_de_vectores_existentes >= len(fragmentos) and not forzar_resubida:
        registro.info(
            "El namespace '%s' ya tiene %d vectores. No se vuelve a subir (usá --reindexar para forzar).",
            NOMBRE_DEL_NAMESPACE,
            cantidad_de_vectores_existentes,
        )
        return

    base_vectorial_en_la_nube: PineconeVectorStore = PineconeVectorStore(
        index=cliente_de_pinecone.Index(NOMBRE_DEL_INDICE),
        embedding=obtener_modelo_de_embeddings_compartido(),
        namespace=NOMBRE_DEL_NAMESPACE,
    )
    base_vectorial_en_la_nube.add_documents(
        documents=fragmentos,
        ids=[fragmento.id for fragmento in fragmentos],
        batch_size=TAMANIO_DEL_LOTE_DE_SUBIDA,
    )
    registro.info("Subidos %d fragmentos (upsert, lotes de %d) al namespace '%s'.", len(fragmentos), TAMANIO_DEL_LOTE_DE_SUBIDA, NOMBRE_DEL_NAMESPACE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    subir_fragmentos_a_pinecone(forzar_resubida="--reindexar" in sys.argv)
