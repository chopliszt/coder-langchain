import logging
import os

registro: logging.Logger = logging.getLogger("observabilidad")

NOMBRE_DEL_PROYECTO_EN_LANGSMITH: str = os.getenv("LANGSMITH_PROJECT", "orquestador-postulaciones")


def verificar_trazas_en_langsmith() -> bool:
    os.environ.setdefault("LANGSMITH_PROJECT", NOMBRE_DEL_PROYECTO_EN_LANGSMITH)
    trazas_activadas: bool = os.getenv("LANGSMITH_TRACING", "").lower() == "true" and bool(os.getenv("LANGSMITH_API_KEY"))
    if trazas_activadas:
        registro.info("Trazas activas en LangSmith, proyecto '%s'.", os.environ["LANGSMITH_PROJECT"])
    else:
        registro.warning("LangSmith desactivado: faltan LANGSMITH_TRACING=true y/o LANGSMITH_API_KEY en el .env.")
    return trazas_activadas
