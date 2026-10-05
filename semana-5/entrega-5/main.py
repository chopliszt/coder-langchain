import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from grafo import construir_grafo_react

CARPETA_DE_ESTA_ENTREGA: Path = Path(__file__).parent
RUTA_DE_LA_BASE_DE_CHECKPOINTS: Path = CARPETA_DE_ESTA_ENTREGA / "checkpoints.sqlite"
RUTA_DE_LA_TRAZA_EN_JSON: Path = CARPETA_DE_ESTA_ENTREGA / "traza_de_ejecucion.json"
RUTA_DEL_LOG: Path = CARPETA_DE_ESTA_ENTREGA / "traza_de_ejecucion.log"
LIMITE_DE_PASOS_DEL_GRAFO: int = 10

registro: logging.Logger = logging.getLogger("demo")


def crear_configuracion_de_la_conversacion(identificador_de_la_conversacion: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": identificador_de_la_conversacion}, "recursion_limit": LIMITE_DE_PASOS_DEL_GRAFO}


def extraer_texto_del_mensaje(mensaje: BaseMessage) -> str:
    if isinstance(mensaje.content, str):
        return mensaje.content
    return "".join(bloque.get("text", "") for bloque in mensaje.content if isinstance(bloque, dict))


def convertir_mensaje_en_paso_de_la_traza(mensaje: BaseMessage) -> dict[str, Any]:
    paso: dict[str, Any] = {"tipo": type(mensaje).__name__, "contenido": extraer_texto_del_mensaje(mensaje)}
    if isinstance(mensaje, AIMessage) and mensaje.tool_calls:
        paso["decide_llamar_a"] = [{"herramienta": llamada["name"], "argumentos": llamada["args"]} for llamada in mensaje.tool_calls]
    if isinstance(mensaje, ToolMessage):
        paso["herramienta"] = mensaje.name
    return paso


def registrar_paso_en_el_log(paso: dict[str, Any]) -> None:
    if "decide_llamar_a" in paso:
        for llamada in paso["decide_llamar_a"]:
            registro.info("  -> El agente decide usar: %s(%s)", llamada["herramienta"], llamada["argumentos"])
    elif paso["tipo"] == "ToolMessage":
        registro.info("  <- %s devuelve: %s", paso["herramienta"], paso["contenido"])
    elif paso["tipo"] == "AIMessage":
        registro.info("  Respuesta: %s", paso["contenido"])


async def ejecutar_un_turno(
    agente: CompiledStateGraph, identificador_de_la_conversacion: str, pregunta_del_usuario: str
) -> list[dict[str, Any]]:
    registro.info("Usuario [%s]: %s", identificador_de_la_conversacion, pregunta_del_usuario)
    cantidad_de_mensajes_previos: int = len((await agente.aget_state(crear_configuracion_de_la_conversacion(identificador_de_la_conversacion))).values.get("messages", []))

    estado_final: dict[str, Any] = await agente.ainvoke(
        {"messages": [HumanMessage(content=pregunta_del_usuario)]},
        config=crear_configuracion_de_la_conversacion(identificador_de_la_conversacion),
    )
    pasos_de_este_turno: list[dict[str, Any]] = [
        convertir_mensaje_en_paso_de_la_traza(mensaje) for mensaje in estado_final["messages"][cantidad_de_mensajes_previos:]
    ]
    for paso in pasos_de_este_turno:
        registrar_paso_en_el_log(paso)
    cantidad_de_llamadas_a_herramientas: int = sum(1 for paso in pasos_de_este_turno if paso["tipo"] == "ToolMessage")
    registro.info("  (herramientas llamadas en este turno: %d | mensajes acumulados en el hilo: %d)\n", cantidad_de_llamadas_a_herramientas, len(estado_final["messages"]))
    return pasos_de_este_turno


def configurar_registro_en_consola_y_archivo() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(RUTA_DEL_LOG, mode="w", encoding="utf-8")],
    )
    for nombre_de_libreria_ruidosa in ("httpx", "google_genai", "openai", "anthropic", "aiosqlite"):
        logging.getLogger(nombre_de_libreria_ruidosa).setLevel(logging.WARNING)


async def ejecutar_demostracion_completa() -> None:
    configurar_registro_en_consola_y_archivo()
    RUTA_DE_LA_BASE_DE_CHECKPOINTS.unlink(missing_ok=True)

    async with AsyncSqliteSaver.from_conn_string(str(RUTA_DE_LA_BASE_DE_CHECKPOINTS)) as guardador_de_checkpoints:
        agente: CompiledStateGraph = construir_grafo_react().compile(checkpointer=guardador_de_checkpoints)

        traza_completa: dict[str, list[dict[str, Any]]] = {
            "1_razonamiento_multi_paso": await ejecutar_un_turno(
                agente, "postulaciones-demo", "¿En qué estado está mi postulación a Pampa AI y cuál es el próximo paso?"
            ),
            "2_memoria_mismo_thread_id": await ejecutar_un_turno(agente, "postulaciones-demo", "¿Y quién es mi contacto ahí?"),
            "3_error_y_segundo_intento": await ejecutar_un_turno(agente, "postulaciones-reintento", "¿Cómo van mis postulaciones en Nimbus?"),
            "4_error_y_pedido_de_aclaracion": await ejecutar_un_turno(agente, "postulaciones-aclaracion", "¿Me respondieron de Globant?"),
        }

    RUTA_DE_LA_TRAZA_EN_JSON.write_text(json.dumps(traza_completa, ensure_ascii=False, indent=2), encoding="utf-8")
    registro.info("Traza guardada en %s y %s", RUTA_DE_LA_TRAZA_EN_JSON.name, RUTA_DEL_LOG.name)


if __name__ == "__main__":
    asyncio.run(ejecutar_demostracion_completa())
