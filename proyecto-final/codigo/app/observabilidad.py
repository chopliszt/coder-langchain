import logging
import os

registro: logging.Logger = logging.getLogger("observabilidad")


def configurar_registro_de_la_aplicacion() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)-13s | %(message)s", datefmt="%H:%M:%S")
    for nombre_de_libreria_ruidosa in ("httpx", "google_genai", "openai", "anthropic", "redisvl", "chromadb", "sentence_transformers"):
        logging.getLogger(nombre_de_libreria_ruidosa).setLevel(logging.WARNING)


def verificar_trazas_en_langsmith() -> bool:
    trazas_activadas: bool = os.getenv("LANGSMITH_TRACING", "").lower() == "true" and bool(os.getenv("LANGSMITH_API_KEY"))
    if trazas_activadas:
        registro.info("Trazas activas en LangSmith, proyecto '%s'.", os.getenv("LANGSMITH_PROJECT", "default"))
    else:
        registro.warning("LangSmith desactivado: faltan LANGSMITH_TRACING=true y/o LANGSMITH_API_KEY en el .env.")
    return trazas_activadas
