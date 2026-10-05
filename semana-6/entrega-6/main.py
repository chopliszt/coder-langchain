import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from langgraph.graph.state import CompiledStateGraph

from graph import construir_grafo_del_orquestador, crear_estado_inicial

CARPETA_DE_ESTA_ENTREGA: Path = Path(__file__).parent
RUTA_DEL_LOG: Path = CARPETA_DE_ESTA_ENTREGA / "traza_de_delegacion.log"
RUTA_DE_LA_TRAZA_EN_JSON: Path = CARPETA_DE_ESTA_ENTREGA / "traza_de_delegacion.json"
LIMITE_DE_PASOS_DEL_GRAFO: int = 25

PEDIDO_DE_PRUEBA: str = "Quiero postularme al puesto de AI Engineer en Pampa AI. ¿Qué tanto encaja mi perfil y qué me falta?"

registro: logging.Logger = logging.getLogger("demo")


def configurar_registro_en_consola_y_archivo() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)-12s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(RUTA_DEL_LOG, mode="w", encoding="utf-8")],
    )
    for nombre_de_libreria_ruidosa in ("httpx", "google_genai", "openai", "anthropic"):
        logging.getLogger(nombre_de_libreria_ruidosa).setLevel(logging.WARNING)


def resumir_actualizacion_de_un_nodo(nombre_del_nodo: str, actualizacion: dict[str, Any]) -> dict[str, Any]:
    resumen: dict[str, Any] = {"nodo": nombre_del_nodo}
    for mensaje in actualizacion.get("messages", []):
        resumen["mensaje"] = str(mensaje.content)
    for campo in ("siguiente_agente", "errores_de_validacion", "tarea_completada", "pasos"):
        if campo in actualizacion:
            resumen[campo] = actualizacion[campo]
    return resumen


async def ejecutar_orquestador_y_registrar_la_delegacion(pedido_del_usuario: str) -> list[dict[str, Any]]:
    orquestador: CompiledStateGraph = construir_grafo_del_orquestador().compile()
    registro.info("Pedido del usuario: %s", pedido_del_usuario)
    pasos_de_la_delegacion: list[dict[str, Any]] = []

    async for evento in orquestador.astream(
        crear_estado_inicial(pedido_del_usuario), config={"recursion_limit": LIMITE_DE_PASOS_DEL_GRAFO}, stream_mode="updates"
    ):
        for nombre_del_nodo, actualizacion in evento.items():
            resumen_del_paso: dict[str, Any] = resumir_actualizacion_de_un_nodo(nombre_del_nodo, actualizacion or {})
            pasos_de_la_delegacion.append(resumen_del_paso)
            registro.info("[%s] %s", nombre_del_nodo, resumen_del_paso.get("mensaje", {k: v for k, v in resumen_del_paso.items() if k != "nodo"}))

    recorrido: str = " -> ".join(paso["nodo"] for paso in pasos_de_la_delegacion)
    registro.info("Recorrido completo: START -> %s -> END", recorrido)
    return pasos_de_la_delegacion


async def ejecutar_demostracion() -> None:
    configurar_registro_en_consola_y_archivo()
    pasos_de_la_delegacion: list[dict[str, Any]] = await ejecutar_orquestador_y_registrar_la_delegacion(PEDIDO_DE_PRUEBA)
    RUTA_DE_LA_TRAZA_EN_JSON.write_text(
        json.dumps({"pedido": PEDIDO_DE_PRUEBA, "pasos": pasos_de_la_delegacion}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    asyncio.run(ejecutar_demostracion())
