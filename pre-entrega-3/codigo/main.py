import asyncio
import logging
from pathlib import Path

from ingest import ejecutar_ingesta_si_hace_falta
from rag_chain import get_rag_response
from schemas import RespuestaRAG

RUTA_DEL_ARCHIVO_DE_EVIDENCIA: Path = Path(__file__).parent / "evidencia_de_ejecucion.log"

PREGUNTA_CON_RESPUESTA_EN_LOS_DOCUMENTOS: str = "¿Qué adecuaciones tengo que aplicar en el examen de Historia de Tomás Ferreyra de 3° A?"
PREGUNTA_TRAMPA_SIN_RESPUESTA_EN_LOS_DOCUMENTOS: str = "¿Qué nota sacó Tomás Ferreyra en el último examen de Matemática?"


def configurar_registro_en_consola_y_archivo() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(RUTA_DEL_ARCHIVO_DE_EVIDENCIA, mode="w", encoding="utf-8")],
    )
    for nombre_de_libreria_ruidosa in ("httpx", "openai", "httpcore", "sentence_transformers", "chromadb", "huggingface_hub"):
        logging.getLogger(nombre_de_libreria_ruidosa).setLevel(logging.WARNING)


def mostrar_respuesta(titulo: str, respuesta: RespuestaRAG) -> None:
    logging.getLogger("demo").info("========== %s ==========\n%s", titulo, respuesta.model_dump_json(indent=2))


async def ejecutar_las_dos_pruebas_en_paralelo() -> None:
    respuesta_con_contexto, respuesta_trampa = await asyncio.gather(
        get_rag_response(PREGUNTA_CON_RESPUESTA_EN_LOS_DOCUMENTOS),
        get_rag_response(PREGUNTA_TRAMPA_SIN_RESPUESTA_EN_LOS_DOCUMENTOS),
    )
    mostrar_respuesta("Prueba 1: la respuesta SÍ está en los documentos", respuesta_con_contexto)
    mostrar_respuesta("Prueba 2: pregunta trampa (NO está en los documentos)", respuesta_trampa)


if __name__ == "__main__":
    configurar_registro_en_consola_y_archivo()
    ejecutar_ingesta_si_hace_falta()
    asyncio.run(ejecutar_las_dos_pruebas_en_paralelo())
