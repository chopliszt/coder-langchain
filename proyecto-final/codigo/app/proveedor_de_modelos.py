import os
from enum import Enum

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from app.configuracion import leer_variable_de_entorno_obligatoria


class ProveedorDeModelos(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


PROVEEDOR_ELEGIDO: ProveedorDeModelos = ProveedorDeModelos(os.getenv("PROVEEDOR_LLM", "gemini").lower())
NOMBRE_DEL_MODELO_PRINCIPAL: str = leer_variable_de_entorno_obligatoria("MODELO_PRINCIPAL")
NOMBRE_DEL_MODELO_DE_RESPALDO: str = leer_variable_de_entorno_obligatoria("MODELO_DE_RESPALDO")
PEDIDOS_POR_MINUTO_PERMITIDOS: int = int(os.getenv("PEDIDOS_POR_MINUTO_AL_LLM", "12"))

limitador_de_pedidos_compartido: InMemoryRateLimiter = InMemoryRateLimiter(
    requests_per_second=PEDIDOS_POR_MINUTO_PERMITIDOS / 60,
    check_every_n_seconds=0.1,
    max_bucket_size=2,
)


def crear_modelo_de_chat(
    nombre_del_modelo: str = NOMBRE_DEL_MODELO_PRINCIPAL,
    temperatura: float = 0,
    limite_de_tokens_de_respuesta: int = 2000,
    reintentos_de_red_del_proveedor: int = 2,
) -> BaseChatModel:
    if PROVEEDOR_ELEGIDO is ProveedorDeModelos.GEMINI:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=nombre_del_modelo,
            temperature=temperatura,
            max_output_tokens=limite_de_tokens_de_respuesta,
            timeout=60,
            max_retries=reintentos_de_red_del_proveedor,
            rate_limiter=limitador_de_pedidos_compartido,
        )
    if PROVEEDOR_ELEGIDO is ProveedorDeModelos.OPENAI:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=nombre_del_modelo,
            temperature=temperatura,
            max_tokens=limite_de_tokens_de_respuesta,
            timeout=60,
            max_retries=reintentos_de_red_del_proveedor,
            rate_limiter=limitador_de_pedidos_compartido,
        )
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=nombre_del_modelo,
        temperature=temperatura,
        max_tokens=limite_de_tokens_de_respuesta,
        timeout=60,
        max_retries=reintentos_de_red_del_proveedor,
        rate_limiter=limitador_de_pedidos_compartido,
    )


def crear_cadena_con_salida_validada(
    plantilla: ChatPromptTemplate, esquema_de_salida: type[BaseModel], temperatura: float = 0
) -> Runnable:
    cadena_principal: Runnable = plantilla | crear_modelo_de_chat(NOMBRE_DEL_MODELO_PRINCIPAL, temperatura).with_structured_output(
        esquema_de_salida
    )
    cadena_de_respaldo: Runnable = plantilla | crear_modelo_de_chat(NOMBRE_DEL_MODELO_DE_RESPALDO, temperatura).with_structured_output(
        esquema_de_salida
    )
    return cadena_principal.with_fallbacks([cadena_de_respaldo])
