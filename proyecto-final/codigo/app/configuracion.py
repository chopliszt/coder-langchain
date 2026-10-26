import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CARPETA_DEL_PROYECTO: Path = Path(__file__).resolve().parent.parent
CARPETA_DE_DOCUMENTOS_DEL_PUESTO: Path = CARPETA_DEL_PROYECTO / "data" / "documentos_del_puesto"
CARPETA_DE_LA_BASE_VECTORIAL: Path = CARPETA_DEL_PROYECTO / "base_vectorial"


def leer_variable_de_entorno_obligatoria(nombre_de_la_variable: str) -> str:
    valor: str | None = os.getenv(nombre_de_la_variable)
    if not valor:
        raise RuntimeError(f"Falta la variable {nombre_de_la_variable} en el .env de la raíz del repo (ver .env.example).")
    return valor


def resolver_ruta_del_perfil_del_candidato() -> Path:
    ruta_configurada: Path = Path(os.getenv("RUTA_DEL_PERFIL_DEL_CANDIDATO", "data/perfil_ficticio.md"))
    return ruta_configurada if ruta_configurada.is_absolute() else CARPETA_DEL_PROYECTO / ruta_configurada


DIRECCION_DE_REDIS: str = os.getenv("REDIS_URL", "redis://localhost:6379")
NOMBRE_DE_LA_COLECCION: str = os.getenv("NOMBRE_DE_LA_COLECCION", "documentos_del_puesto")
NOMBRE_DEL_MODELO_DE_EMBEDDINGS: str = leer_variable_de_entorno_obligatoria("MODELO_DE_EMBEDDINGS")
RUTA_DEL_PERFIL_DEL_CANDIDATO: Path = resolver_ruta_del_perfil_del_candidato()

TOKENS_POR_FRAGMENTO: int = 300
TOKENS_DE_SOLAPAMIENTO: int = 40
CODIFICACION_DE_TIKTOKEN: str = "cl100k_base"
CANTIDAD_DE_FRAGMENTOS_A_RECUPERAR: int = 4

MAXIMO_DE_PREGUNTAS_DEL_FORMULARIO: int = 5
MAXIMO_DE_PREGUNTAS_DEL_ENTREVISTADOR_POR_PREGUNTA: int = 3
MAXIMO_DE_INTENTOS_DE_REDACCION: int = 2
LIMITE_DE_PASOS_POR_INVOCACION_DEL_GRAFO: int = 40
