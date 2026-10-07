import logging
import time

from pinecone import Pinecone, ServerlessSpec

from configuracion import (
    METRICA_DE_SIMILITUD,
    NOMBRE_DEL_INDICE,
    NUBE_DEL_INDICE,
    REGION_DEL_INDICE,
    calcular_dimension_del_modelo_de_embeddings,
    leer_clave_de_pinecone,
)

registro: logging.Logger = logging.getLogger("inicializar_indice")

SEGUNDOS_ENTRE_CONSULTAS_DE_ESTADO: int = 2


def esperar_hasta_que_el_indice_este_listo(cliente_de_pinecone: Pinecone) -> None:
    while not cliente_de_pinecone.describe_index(NOMBRE_DEL_INDICE).status["ready"]:
        registro.info("Esperando a que el índice '%s' esté listo...", NOMBRE_DEL_INDICE)
        time.sleep(SEGUNDOS_ENTRE_CONSULTAS_DE_ESTADO)


def crear_indice_serverless_si_no_existe() -> None:
    cliente_de_pinecone: Pinecone = Pinecone(api_key=leer_clave_de_pinecone())
    dimension_de_los_embeddings: int = calcular_dimension_del_modelo_de_embeddings()

    if cliente_de_pinecone.has_index(NOMBRE_DEL_INDICE):
        dimension_del_indice_existente: int = cliente_de_pinecone.describe_index(NOMBRE_DEL_INDICE).dimension
        if dimension_del_indice_existente != dimension_de_los_embeddings:
            raise RuntimeError(
                f"El índice '{NOMBRE_DEL_INDICE}' tiene dimensión {dimension_del_indice_existente} "
                f"pero el modelo de embeddings genera {dimension_de_los_embeddings}. Borralo o usá otro INDEX_NAME."
            )
        registro.info("El índice '%s' ya existe (dimensión %d). No se vuelve a crear.", NOMBRE_DEL_INDICE, dimension_del_indice_existente)
    else:
        registro.info("Creando índice serverless '%s' (dimensión %d, %s)...", NOMBRE_DEL_INDICE, dimension_de_los_embeddings, METRICA_DE_SIMILITUD)
        cliente_de_pinecone.create_index(
            name=NOMBRE_DEL_INDICE,
            dimension=dimension_de_los_embeddings,
            metric=METRICA_DE_SIMILITUD,
            spec=ServerlessSpec(cloud=NUBE_DEL_INDICE, region=REGION_DEL_INDICE),
        )

    esperar_hasta_que_el_indice_este_listo(cliente_de_pinecone)
    registro.info("Índice '%s' listo.", NOMBRE_DEL_INDICE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    crear_indice_serverless_si_no_existe()
