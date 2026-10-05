import os
from enum import Enum

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()


class ProveedorDeModelos(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


MODELOS_PRINCIPALES_POR_PROVEEDOR: dict[ProveedorDeModelos, str] = {
    ProveedorDeModelos.GEMINI: "gemini-flash-latest",
    ProveedorDeModelos.OPENAI: "gpt-4.1-mini",
    ProveedorDeModelos.ANTHROPIC: "claude-haiku-4-5",
}

MODELOS_DE_RESPALDO_POR_PROVEEDOR: dict[ProveedorDeModelos, str] = {
    ProveedorDeModelos.GEMINI: "gemini-flash-lite-latest",
    ProveedorDeModelos.OPENAI: "gpt-4o-mini",
    ProveedorDeModelos.ANTHROPIC: "claude-sonnet-4-5",
}

MOTIVOS_DE_FINALIZACION_POR_LIMITE_DE_TOKENS: set[str] = {"length", "MAX_TOKENS", "max_tokens"}

PROVEEDOR_ELEGIDO: ProveedorDeModelos = ProveedorDeModelos(os.getenv("PROVEEDOR_LLM", "gemini").lower())
NOMBRE_DEL_MODELO_PRINCIPAL: str = os.getenv("MODELO_PRINCIPAL", MODELOS_PRINCIPALES_POR_PROVEEDOR[PROVEEDOR_ELEGIDO])
NOMBRE_DEL_MODELO_DE_RESPALDO: str = os.getenv("MODELO_DE_RESPALDO", MODELOS_DE_RESPALDO_POR_PROVEEDOR[PROVEEDOR_ELEGIDO])


def crear_modelo_de_chat(
    nombre_del_modelo: str = NOMBRE_DEL_MODELO_PRINCIPAL,
    limite_de_tokens_de_respuesta: int = 2000,
    reintentos_de_red_del_proveedor: int = 2,
) -> BaseChatModel:
    if PROVEEDOR_ELEGIDO is ProveedorDeModelos.GEMINI:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=nombre_del_modelo,
            temperature=0,
            max_output_tokens=limite_de_tokens_de_respuesta,
            timeout=30,
            max_retries=reintentos_de_red_del_proveedor,
        )
    if PROVEEDOR_ELEGIDO is ProveedorDeModelos.OPENAI:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=nombre_del_modelo,
            temperature=0,
            max_tokens=limite_de_tokens_de_respuesta,
            timeout=30,
            max_retries=reintentos_de_red_del_proveedor,
        )
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=nombre_del_modelo,
        temperature=0,
        max_tokens=limite_de_tokens_de_respuesta,
        timeout=30,
        max_retries=reintentos_de_red_del_proveedor,
    )
