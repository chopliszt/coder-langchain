import logging
import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_openai import ChatOpenAI
from openai import APIConnectionError, APITimeoutError, RateLimitError

from schemas import EntidadesTecnicas

load_dotenv()

registro: logging.Logger = logging.getLogger("pipeline_de_extraccion")

NOMBRE_DEL_MODELO_PRINCIPAL: str = os.getenv("MODELO_PRINCIPAL_OPENAI", "gpt-4.1-mini")
NOMBRE_DEL_MODELO_DE_RESPALDO: str = os.getenv("MODELO_DE_RESPALDO_OPENAI", "gpt-4o-mini")
LIMITE_DE_TOKENS_POR_DEFECTO: int = 1000
CANTIDAD_MAXIMA_DE_INTENTOS: int = 3
SEGUNDOS_DE_ESPERA_MAXIMA_POR_LLAMADA: int = 30

INSTRUCCIONES_DE_FORMATO: str = """\
- tecnologias: solo nombres de tecnologías mencionadas explícitamente (lenguajes, frameworks, bases de datos, servicios cloud, herramientas). No inventes ninguna.
- nivel_de_criticidad:
    * "alta" si afecta producción, usuarios reales, datos o seguridad.
    * "media" si degrada el rendimiento o afecta un entorno no productivo.
    * "baja" si es una descripción de arquitectura, una mejora o algo sin impacto.
- resumen_tecnico: una o dos oraciones en español, concretas y técnicas."""

plantilla_de_prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Sos un analista técnico senior. Tu tarea es extraer entidades técnicas "
            "del texto que te envía el usuario.\n\n"
            "Reglas de formato:\n{instrucciones_de_formato}",
        ),
        ("human", "Texto a analizar:\n\n{texto}"),
    ]
).partial(instrucciones_de_formato=INSTRUCCIONES_DE_FORMATO)


class RespuestaTruncadaError(Exception):
    pass


class RespuestaMalFormadaError(Exception):
    pass


ERRORES_QUE_VALE_LA_PENA_REINTENTAR: tuple[type[Exception], ...] = (
    RespuestaTruncadaError,
    RespuestaMalFormadaError,
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
)


def registrar_inicio_de_intento(datos_de_entrada: dict[str, str]) -> dict[str, str]:
    registro.info("Intento de extracción: enviando %d caracteres al modelo.", len(datos_de_entrada["texto"]))
    return datos_de_entrada


def verificar_que_la_respuesta_este_completa_y_validada(respuesta_del_modelo: dict[str, Any]) -> EntidadesTecnicas:
    mensaje_crudo: AIMessage = respuesta_del_modelo["raw"]
    nombre_del_modelo_usado: str = mensaje_crudo.response_metadata.get("model_name", "desconocido")
    motivo_de_finalizacion: str | None = mensaje_crudo.response_metadata.get("finish_reason")

    if motivo_de_finalizacion == "length":
        registro.warning("[%s] Respuesta cortada por límite de tokens (finish_reason=length). Se reintenta.", nombre_del_modelo_usado)
        raise RespuestaTruncadaError("El modelo cortó la respuesta antes de terminar el objeto.")

    error_de_validacion: Exception | None = respuesta_del_modelo["parsing_error"]
    if error_de_validacion is not None:
        registro.warning("[%s] La respuesta no cumple el esquema Pydantic: %s. Se reintenta.", nombre_del_modelo_usado, error_de_validacion)
        raise RespuestaMalFormadaError(str(error_de_validacion))

    entidades_validadas: EntidadesTecnicas | None = respuesta_del_modelo["parsed"]
    if entidades_validadas is None:
        registro.warning("[%s] El modelo no devolvió ningún objeto. Se reintenta.", nombre_del_modelo_usado)
        raise RespuestaMalFormadaError("El modelo no devolvió ningún objeto estructurado.")

    registro.info("[%s] Validación OK (finish_reason=%s).", nombre_del_modelo_usado, motivo_de_finalizacion)
    return entidades_validadas


def crear_modelo_de_chat(nombre_del_modelo: str, limite_de_tokens_de_respuesta: int) -> ChatOpenAI:
    return ChatOpenAI(
        model=nombre_del_modelo,
        temperature=0,
        max_tokens=limite_de_tokens_de_respuesta,
        timeout=SEGUNDOS_DE_ESPERA_MAXIMA_POR_LLAMADA,
        max_retries=0,
    )


def crear_cadena_de_extraccion_sin_reintentos(
    nombre_del_modelo: str,
    limite_de_tokens_de_respuesta: int = LIMITE_DE_TOKENS_POR_DEFECTO,
) -> Runnable[dict[str, str], EntidadesTecnicas]:
    modelo_de_chat: ChatOpenAI = crear_modelo_de_chat(nombre_del_modelo, limite_de_tokens_de_respuesta)
    modelo_con_salida_estructurada: Runnable = modelo_de_chat.with_structured_output(EntidadesTecnicas, include_raw=True)

    return (
        RunnableLambda(registrar_inicio_de_intento)
        | plantilla_de_prompt
        | modelo_con_salida_estructurada
        | RunnableLambda(verificar_que_la_respuesta_este_completa_y_validada)
    )


def crear_cadena_de_extraccion_con_reintentos(
    nombre_del_modelo: str,
    limite_de_tokens_de_respuesta: int = LIMITE_DE_TOKENS_POR_DEFECTO,
) -> Runnable[dict[str, str], EntidadesTecnicas]:
    cadena_de_extraccion: Runnable[dict[str, str], EntidadesTecnicas] = crear_cadena_de_extraccion_sin_reintentos(
        nombre_del_modelo, limite_de_tokens_de_respuesta
    )
    return cadena_de_extraccion.with_retry(
        retry_if_exception_type=ERRORES_QUE_VALE_LA_PENA_REINTENTAR,
        stop_after_attempt=CANTIDAD_MAXIMA_DE_INTENTOS,
        wait_exponential_jitter=True,
    )


def crear_cadena_resiliente_con_modelo_de_respaldo(
    limite_de_tokens_del_modelo_principal: int = LIMITE_DE_TOKENS_POR_DEFECTO,
) -> Runnable[dict[str, str], EntidadesTecnicas]:
    cadena_principal: Runnable[dict[str, str], EntidadesTecnicas] = crear_cadena_de_extraccion_con_reintentos(
        NOMBRE_DEL_MODELO_PRINCIPAL, limite_de_tokens_del_modelo_principal
    )
    cadena_de_respaldo: Runnable[dict[str, str], EntidadesTecnicas] = crear_cadena_de_extraccion_con_reintentos(
        NOMBRE_DEL_MODELO_DE_RESPALDO
    )
    return cadena_principal.with_fallbacks([cadena_de_respaldo])


async def extraer_entidades_tecnicas_desde_texto(
    texto: str,
    cadena: Runnable[dict[str, str], EntidadesTecnicas] | None = None,
) -> EntidadesTecnicas | None:
    cadena_a_ejecutar: Runnable[dict[str, str], EntidadesTecnicas] = cadena or crear_cadena_resiliente_con_modelo_de_respaldo()
    try:
        entidades_extraidas: EntidadesTecnicas = await cadena_a_ejecutar.ainvoke({"texto": texto})
        registro.info("Extracción final: %s", entidades_extraidas.model_dump_json())
        return entidades_extraidas
    except (RespuestaTruncadaError, RespuestaMalFormadaError) as error_de_validacion:
        registro.error("La salida no se pudo validar ni con reintentos ni con el modelo de respaldo: %s", error_de_validacion)
        return None
    except Exception as error_inesperado:
        registro.error("Error no recuperable (%s): %s", type(error_inesperado).__name__, error_inesperado)
        return None


async def process_text(text: str) -> EntidadesTecnicas | None:
    return await extraer_entidades_tecnicas_desde_texto(text)
