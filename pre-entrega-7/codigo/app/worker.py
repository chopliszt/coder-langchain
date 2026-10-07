import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from langchain_core.messages import BaseMessage
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot
from langsmith import traceable
from redis.asyncio import Redis

from graph import crear_estado_inicial
from hitl import crear_comando_para_reanudar

registro: logging.Logger = logging.getLogger("worker")

LIMITE_DE_PASOS_DEL_GRAFO: int = 25
SEGUNDOS_QUE_SE_GUARDA_UN_TRABAJO: int = 60 * 60 * 24


class EstadoDelTrabajo(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    DONE = "DONE"
    FAILED = "FAILED"


def crear_clave_del_trabajo(identificador_del_trabajo: str) -> str:
    return f"trabajo:{identificador_del_trabajo}"


def crear_configuracion_del_grafo(identificador_del_trabajo: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": identificador_del_trabajo}, "recursion_limit": LIMITE_DE_PASOS_DEL_GRAFO}


def hora_actual_en_texto() -> str:
    return datetime.now(timezone.utc).isoformat()


async def guardar_estado_del_trabajo(
    cliente_redis: Redis, identificador_del_trabajo: str, estado: EstadoDelTrabajo, **datos_extra: Any
) -> None:
    clave: str = crear_clave_del_trabajo(identificador_del_trabajo)
    campos: dict[str, str] = {"estado": estado.value, "actualizado_en": hora_actual_en_texto()}
    campos.update({nombre: json.dumps(valor, ensure_ascii=False, default=str) for nombre, valor in datos_extra.items()})
    await cliente_redis.hset(clave, mapping=campos)
    await cliente_redis.expire(clave, SEGUNDOS_QUE_SE_GUARDA_UN_TRABAJO)
    registro.info("Trabajo %s -> %s", identificador_del_trabajo, estado.value)


async def leer_estado_del_trabajo(cliente_redis: Redis, identificador_del_trabajo: str) -> dict[str, Any] | None:
    campos_guardados: dict[str, str] = await cliente_redis.hgetall(crear_clave_del_trabajo(identificador_del_trabajo))
    if not campos_guardados:
        return None
    return {nombre: (valor if nombre in ("estado", "actualizado_en", "creado_en") else json.loads(valor)) for nombre, valor in campos_guardados.items()}


def extraer_respuesta_final(mensajes: list[BaseMessage]) -> str:
    mensajes_de_la_sintesis: list[BaseMessage] = [mensaje for mensaje in mensajes if getattr(mensaje, "name", None) == "Sintesis"]
    return str(mensajes_de_la_sintesis[-1].content) if mensajes_de_la_sintesis else str(mensajes[-1].content)


async def actualizar_estado_segun_donde_quedo_el_grafo(
    cliente_redis: Redis, orquestador: CompiledStateGraph, identificador_del_trabajo: str
) -> None:
    foto_del_estado: StateSnapshot = await orquestador.aget_state(crear_configuracion_del_grafo(identificador_del_trabajo))
    respuesta_final: str = extraer_respuesta_final(foto_del_estado.values["messages"])
    if foto_del_estado.interrupts:
        await guardar_estado_del_trabajo(
            cliente_redis,
            identificador_del_trabajo,
            EstadoDelTrabajo.WAITING_APPROVAL,
            respuesta=respuesta_final,
            pedido_de_aprobacion=foto_del_estado.interrupts[0].value,
        )
        return
    await guardar_estado_del_trabajo(
        cliente_redis,
        identificador_del_trabajo,
        EstadoDelTrabajo.DONE,
        respuesta=respuesta_final,
        postulacion_enviada=foto_del_estado.values.get("postulacion_enviada", False),
        decision_humana=foto_del_estado.values.get("decision_humana"),
    )


@traceable(name="trabajo_del_orquestador", run_type="chain")
async def ejecutar_trabajo_en_segundo_plano(
    cliente_redis: Redis, orquestador: CompiledStateGraph, identificador_del_trabajo: str, pedido_del_usuario: str
) -> None:
    try:
        await guardar_estado_del_trabajo(cliente_redis, identificador_del_trabajo, EstadoDelTrabajo.RUNNING)
        await orquestador.ainvoke(crear_estado_inicial(pedido_del_usuario), config=crear_configuracion_del_grafo(identificador_del_trabajo))
        await actualizar_estado_segun_donde_quedo_el_grafo(cliente_redis, orquestador, identificador_del_trabajo)
    except Exception as error:
        registro.exception("Trabajo %s falló", identificador_del_trabajo)
        await guardar_estado_del_trabajo(cliente_redis, identificador_del_trabajo, EstadoDelTrabajo.FAILED, error=f"{type(error).__name__}: {error}")


@traceable(name="reanudacion_tras_aprobacion_humana", run_type="chain")
async def reanudar_trabajo_con_la_decision_humana(
    cliente_redis: Redis, orquestador: CompiledStateGraph, identificador_del_trabajo: str, aprobado: bool, comentario: str
) -> None:
    try:
        await guardar_estado_del_trabajo(cliente_redis, identificador_del_trabajo, EstadoDelTrabajo.RUNNING)
        await orquestador.ainvoke(crear_comando_para_reanudar(aprobado, comentario), config=crear_configuracion_del_grafo(identificador_del_trabajo))
        await actualizar_estado_segun_donde_quedo_el_grafo(cliente_redis, orquestador, identificador_del_trabajo)
    except Exception as error:
        registro.exception("Reanudación del trabajo %s falló", identificador_del_trabajo)
        await guardar_estado_del_trabajo(cliente_redis, identificador_del_trabajo, EstadoDelTrabajo.FAILED, error=f"{type(error).__name__}: {error}")
