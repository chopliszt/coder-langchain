import asyncio
import logging
from pathlib import Path

from langchain_core.runnables import Runnable
from pydantic import ValidationError

from chain import (
    crear_cadena_resiliente_con_modelo_de_respaldo,
    extraer_entidades_tecnicas_desde_texto,
    process_text,
)
from schemas import EntidadesTecnicas

RUTA_DEL_ARCHIVO_DE_EVIDENCIA: Path = Path(__file__).parent / "evidencia_de_ejecucion.log"

TEXTO_LIMPIO_LOG_DE_ERROR: str = """
Nuestra API en FastAPI está devolviendo timeouts intermitentes. El caché en Redis
se satura en picos de tráfico y las conexiones a PostgreSQL se agotan porque el pool
está mal dimensionado. Esto está afectando a usuarios en producción.
"""

TEXTO_DE_ARQUITECTURA_DETECTOR_DE_ESTAFAS: str = """
Arquitectura de Sirius, un detector de estafas: un bot de Telegram recibe mensajes
sospechosos y los envía a un backend en Python con FastAPI. Una cadena de LangChain
con Gemini clasifica el mensaje como phishing o legítimo, y los resultados se guardan
en Firestore. Todo corre en contenedores Docker sobre Google Cloud Run.
"""

TEXTO_AMBIGUO_Y_DESORDENADO: str = "el sistema anda medio raro desde ayer, a veces tarda y otras no... ni idea q pasa"


def configurar_registro_en_consola_y_archivo() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(RUTA_DEL_ARCHIVO_DE_EVIDENCIA, mode="w", encoding="utf-8"),
        ],
    )
    for nombre_de_libreria_ruidosa in ("httpx", "openai", "httpcore"):
        logging.getLogger(nombre_de_libreria_ruidosa).setLevel(logging.WARNING)


def mostrar_titulo(titulo: str) -> None:
    logging.getLogger("demo").info("========== %s ==========", titulo)


def mostrar_resultado(entidades: EntidadesTecnicas | None) -> None:
    if entidades is None:
        logging.getLogger("demo").info("Resultado: sin objeto validado (el pipeline no crasheó).")
        return
    logging.getLogger("demo").info("Resultado:\n%s", entidades.model_dump_json(indent=2))


def probar_validador_de_pydantic_sin_llamar_al_modelo() -> None:
    mostrar_titulo("1. Validador Pydantic: lista de tecnologías vacía")
    try:
        EntidadesTecnicas(tecnologias=["   ", ""], nivel_de_criticidad="alta", resumen_tecnico="Texto de prueba suficientemente largo.")
    except ValidationError as error_de_validacion:
        logging.getLogger("demo").info("El validador rechazó el objeto, como esperábamos:\n%s", error_de_validacion)

    entidades_con_duplicados: EntidadesTecnicas = EntidadesTecnicas(
        tecnologias=[" Redis", "Redis", "FastAPI "],
        nivel_de_criticidad="media",
        resumen_tecnico="Prueba de limpieza de duplicados y espacios.",
    )
    logging.getLogger("demo").info("Limpieza de duplicados y espacios: %s", entidades_con_duplicados.tecnologias)


async def probar_dos_textos_limpios_en_paralelo() -> None:
    mostrar_titulo("2. Dos textos limpios procesados en paralelo (asyncio.gather)")
    resultados: list[EntidadesTecnicas | None] = await asyncio.gather(
        process_text(TEXTO_LIMPIO_LOG_DE_ERROR),
        extraer_entidades_tecnicas_desde_texto(TEXTO_DE_ARQUITECTURA_DETECTOR_DE_ESTAFAS),
    )
    for entidades in resultados:
        mostrar_resultado(entidades)


async def probar_texto_ambiguo() -> None:
    mostrar_titulo("3. Prueba de estrés: texto ambiguo y desordenado")
    mostrar_resultado(await extraer_entidades_tecnicas_desde_texto(TEXTO_AMBIGUO_Y_DESORDENADO))


async def probar_respuesta_truncada_y_rescate_con_modelo_de_respaldo() -> None:
    mostrar_titulo("4. Respuesta truncada (finish_reason=length) -> reintentos -> modelo de respaldo")
    cadena_con_modelo_principal_sin_tokens_suficientes: Runnable[dict[str, str], EntidadesTecnicas] = crear_cadena_resiliente_con_modelo_de_respaldo(
        limite_de_tokens_del_modelo_principal=15
    )
    mostrar_resultado(
        await extraer_entidades_tecnicas_desde_texto(TEXTO_LIMPIO_LOG_DE_ERROR, cadena_con_modelo_principal_sin_tokens_suficientes)
    )


async def ejecutar_demostracion_completa() -> None:
    configurar_registro_en_consola_y_archivo()
    probar_validador_de_pydantic_sin_llamar_al_modelo()
    await probar_dos_textos_limpios_en_paralelo()
    await probar_texto_ambiguo()
    await probar_respuesta_truncada_y_rescate_con_modelo_de_respaldo()


if __name__ == "__main__":
    asyncio.run(ejecutar_demostracion_completa())
