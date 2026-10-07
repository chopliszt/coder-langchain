from pathlib import Path

from langchain_core.runnables import Runnable
from langchain_core.runnables.graph_mermaid import draw_mermaid_png

from chain import NOMBRE_DEL_MODELO_PRINCIPAL, crear_cadena_de_extraccion_sin_reintentos
from schemas import EntidadesTecnicas

CARPETA_DE_ESTA_ENTREGA: Path = Path(__file__).parent
RUTA_DEL_DIAGRAMA_DE_PASOS: Path = CARPETA_DE_ESTA_ENTREGA / "diagrama_pasos_de_la_cadena.png"
RUTA_DEL_DIAGRAMA_DE_RESILIENCIA: Path = CARPETA_DE_ESTA_ENTREGA / "diagrama_reintentos_y_respaldo.png"

DIAGRAMA_DE_RESILIENCIA_EN_MERMAID: str = """
graph TD;
    entrada([texto crudo]) --> principal[Cadena con modelo principal];
    principal --> verificacion{finish_reason OK<br/>y Pydantic valida?};
    verificacion -- si --> salida([EntidadesTecnicas validadas]);
    verificacion -- no --> reintento{quedan intentos?<br/>max 3, backoff exponencial};
    reintento -- si --> principal;
    reintento -- no --> respaldo[Cadena con modelo de respaldo<br/>tambien con 3 intentos];
    respaldo -- valida --> salida;
    respaldo -- falla --> error([log de error + None, sin crashear]);
"""


def generar_diagrama_de_pasos_de_la_cadena() -> None:
    cadena_sin_reintentos: Runnable[dict[str, str], EntidadesTecnicas] = crear_cadena_de_extraccion_sin_reintentos(
        NOMBRE_DEL_MODELO_PRINCIPAL
    )
    cadena_sin_reintentos.get_graph().draw_mermaid_png(output_file_path=str(RUTA_DEL_DIAGRAMA_DE_PASOS))
    print(f"Diagrama de pasos guardado en {RUTA_DEL_DIAGRAMA_DE_PASOS}")


def generar_diagrama_de_reintentos_y_respaldo() -> None:
    draw_mermaid_png(DIAGRAMA_DE_RESILIENCIA_EN_MERMAID, output_file_path=str(RUTA_DEL_DIAGRAMA_DE_RESILIENCIA))
    print(f"Diagrama de resiliencia guardado en {RUTA_DEL_DIAGRAMA_DE_RESILIENCIA}")


if __name__ == "__main__":
    generar_diagrama_de_pasos_de_la_cadena()
    generar_diagrama_de_reintentos_y_respaldo()
