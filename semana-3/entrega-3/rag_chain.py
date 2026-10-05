import logging
from functools import lru_cache
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel, RunnablePassthrough
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_openai import ChatOpenAI

from configuracion import (
    CANTIDAD_DE_FRAGMENTOS_A_RECUPERAR,
    CARPETA_DE_LA_BASE_VECTORIAL,
    NOMBRE_DE_LA_COLECCION,
    NOMBRE_DEL_MODELO_DE_CHAT,
    obtener_modelo_de_embeddings_compartido,
)
from schemas import FRASE_CUANDO_NO_HAY_INFORMACION, FuenteConsultada, RespuestaGeneradaPorElModelo, RespuestaRAG

registro: logging.Logger = logging.getLogger("rag")

convertidor_de_texto_a_pydantic: PydanticOutputParser[RespuestaGeneradaPorElModelo] = PydanticOutputParser(
    pydantic_object=RespuestaGeneradaPorElModelo
)

plantilla_de_prompt_fundamentado: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Sos un asistente para docentes de una escuela secundaria. Ayudás a consultar qué adecuaciones "
            "pedagógicas necesita cada estudiante.\n"
            "Reglas estrictas:\n"
            "1. Respondé ÚNICAMENTE con información que esté en el CONTEXTO.\n"
            "2. Si la respuesta no está en el CONTEXTO, respondé exactamente: \"{frase_cuando_no_hay_informacion}\". "
            "No uses conocimiento general, no completes, no supongas.\n"
            "3. Respondé en español, de forma breve y clara.\n\n"
            "{instrucciones_de_formato}",
        ),
        ("human", "CONTEXTO:\n{contexto}\n\nPREGUNTA: {pregunta}"),
    ]
).partial(
    frase_cuando_no_hay_informacion=FRASE_CUANDO_NO_HAY_INFORMACION,
    instrucciones_de_formato=convertidor_de_texto_a_pydantic.get_format_instructions(),
)


def unir_fragmentos_en_un_solo_contexto(fragmentos: list[Document]) -> str:
    return "\n\n---\n\n".join(
        f"[Fuente: {fragmento.metadata['fuente']} | fragmento {fragmento.metadata['indice_del_fragmento']}]\n{fragmento.page_content}"
        for fragmento in fragmentos
    )


def preparar_variables_del_prompt(fragmentos_y_pregunta: dict[str, Any]) -> dict[str, str]:
    fragmentos_recuperados: list[Document] = fragmentos_y_pregunta["fragmentos_recuperados"]
    registro.info("Recuperados %d fragmentos: %s", len(fragmentos_recuperados), [fragmento.metadata["fuente"] for fragmento in fragmentos_recuperados])
    return {"contexto": unir_fragmentos_en_un_solo_contexto(fragmentos_recuperados), "pregunta": fragmentos_y_pregunta["pregunta"]}


def convertir_fragmentos_en_fuentes(fragmentos: list[Document]) -> list[FuenteConsultada]:
    return [
        FuenteConsultada(archivo=fragmento.metadata["fuente"], indice_del_fragmento=fragmento.metadata["indice_del_fragmento"])
        for fragmento in fragmentos
    ]


@lru_cache(maxsize=1)
def obtener_buscador_de_fragmentos_en_chroma() -> VectorStoreRetriever:
    base_vectorial: Chroma = Chroma(
        collection_name=NOMBRE_DE_LA_COLECCION,
        embedding_function=obtener_modelo_de_embeddings_compartido(),
        persist_directory=str(CARPETA_DE_LA_BASE_VECTORIAL),
    )
    return base_vectorial.as_retriever(search_type="similarity", search_kwargs={"k": CANTIDAD_DE_FRAGMENTOS_A_RECUPERAR})


@lru_cache(maxsize=1)
def crear_cadena_rag_completa() -> Runnable[str, dict[str, Any]]:
    modelo_de_chat: ChatOpenAI = ChatOpenAI(model=NOMBRE_DEL_MODELO_DE_CHAT, temperature=0, timeout=30, max_retries=0)

    cadena_de_generacion_fundamentada: Runnable[dict[str, Any], RespuestaGeneradaPorElModelo] = (
        RunnableLambda(preparar_variables_del_prompt)
        | plantilla_de_prompt_fundamentado
        | modelo_de_chat
        | convertidor_de_texto_a_pydantic
    ).with_retry(stop_after_attempt=3, wait_exponential_jitter=True)

    return RunnableParallel(
        fragmentos_recuperados=obtener_buscador_de_fragmentos_en_chroma(),
        pregunta=RunnablePassthrough(),
    ) | RunnablePassthrough.assign(respuesta_del_modelo=cadena_de_generacion_fundamentada)


async def responder_pregunta_usando_solo_documentos_locales(pregunta: str) -> RespuestaRAG:
    resultado_de_la_cadena: dict[str, Any] = await crear_cadena_rag_completa().ainvoke(pregunta)

    fragmentos_recuperados: list[Document] = resultado_de_la_cadena["fragmentos_recuperados"]
    respuesta_del_modelo: RespuestaGeneradaPorElModelo = resultado_de_la_cadena["respuesta_del_modelo"]

    fuentes_que_respaldan_la_respuesta: list[FuenteConsultada] = (
        convertir_fragmentos_en_fuentes(fragmentos_recuperados) if respuesta_del_modelo.la_respuesta_esta_en_el_contexto else []
    )
    return RespuestaRAG(
        pregunta=pregunta,
        respuesta=respuesta_del_modelo.respuesta,
        la_respuesta_esta_en_el_contexto=respuesta_del_modelo.la_respuesta_esta_en_el_contexto,
        fuentes=fuentes_que_respaldan_la_respuesta,
        cantidad_de_fragmentos_recuperados=len(fragmentos_recuperados),
    )


async def get_rag_response(query: str) -> RespuestaRAG:
    return await responder_pregunta_usando_solo_documentos_locales(query)
