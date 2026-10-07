import asyncio
import logging
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field
from redis.asyncio import Redis

load_dotenv()

from graph import compilar_grafo_con_persistencia  # noqa: E402
from observability import verificar_trazas_en_langsmith  # noqa: E402
from worker import (  # noqa: E402
    EstadoDelTrabajo,
    ejecutar_trabajo_en_segundo_plano,
    guardar_estado_del_trabajo,
    leer_estado_del_trabajo,
    reanudar_trabajo_con_la_decision_humana,
)

DIRECCION_DE_REDIS: str = os.getenv("REDIS_URL", "redis://localhost:6379")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)-12s | %(message)s", datefmt="%H:%M:%S")
for nombre_de_libreria_ruidosa in ("httpx", "google_genai", "openai", "anthropic", "redisvl"):
    logging.getLogger(nombre_de_libreria_ruidosa).setLevel(logging.WARNING)

tareas_en_segundo_plano: set[asyncio.Task[None]] = set()


class PedidoDeNuevaTarea(BaseModel):
    pedido: str = Field(min_length=5, examples=["Quiero postularme al puesto de AI Engineer en Pampa AI. ¿Qué tanto encaja mi perfil?"])


class RespuestaDeTareaCreada(BaseModel):
    job_id: str
    estado: EstadoDelTrabajo


class DecisionDeAprobacion(BaseModel):
    aprobado: bool
    comentario: str = ""


def lanzar_en_segundo_plano(corrutina: Any) -> None:
    tarea: asyncio.Task[None] = asyncio.create_task(corrutina)
    tareas_en_segundo_plano.add(tarea)
    tarea.add_done_callback(tareas_en_segundo_plano.discard)


@asynccontextmanager
async def ciclo_de_vida_de_la_api(aplicacion: FastAPI) -> AsyncIterator[None]:
    verificar_trazas_en_langsmith()
    aplicacion.state.cliente_redis = Redis.from_url(DIRECCION_DE_REDIS, decode_responses=True)
    async with AsyncRedisSaver.from_conn_string(DIRECCION_DE_REDIS) as guardador_de_checkpoints:
        await guardador_de_checkpoints.asetup()
        aplicacion.state.orquestador = compilar_grafo_con_persistencia(guardador_de_checkpoints)
        yield
    await aplicacion.state.cliente_redis.aclose()


aplicacion: FastAPI = FastAPI(title="API del orquestador de postulaciones", lifespan=ciclo_de_vida_de_la_api)


@aplicacion.post("/tasks", status_code=status.HTTP_202_ACCEPTED, response_model=RespuestaDeTareaCreada)
async def crear_tarea(pedido_de_nueva_tarea: PedidoDeNuevaTarea) -> RespuestaDeTareaCreada:
    identificador_del_trabajo: str = str(uuid.uuid4())
    cliente_redis: Redis = aplicacion.state.cliente_redis
    orquestador: CompiledStateGraph = aplicacion.state.orquestador
    await guardar_estado_del_trabajo(cliente_redis, identificador_del_trabajo, EstadoDelTrabajo.PENDING, pedido=pedido_de_nueva_tarea.pedido)
    lanzar_en_segundo_plano(ejecutar_trabajo_en_segundo_plano(cliente_redis, orquestador, identificador_del_trabajo, pedido_de_nueva_tarea.pedido))
    return RespuestaDeTareaCreada(job_id=identificador_del_trabajo, estado=EstadoDelTrabajo.PENDING)


@aplicacion.get("/tasks/{job_id}")
async def consultar_tarea(job_id: str) -> dict[str, Any]:
    estado_del_trabajo: dict[str, Any] | None = await leer_estado_del_trabajo(aplicacion.state.cliente_redis, job_id)
    if estado_del_trabajo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe un trabajo con ese job_id.")
    return {"job_id": job_id, **estado_del_trabajo}


@aplicacion.post("/tasks/{job_id}/approve", status_code=status.HTTP_202_ACCEPTED)
async def aprobar_o_rechazar_tarea(job_id: str, decision: DecisionDeAprobacion) -> dict[str, str]:
    cliente_redis: Redis = aplicacion.state.cliente_redis
    estado_del_trabajo: dict[str, Any] | None = await leer_estado_del_trabajo(cliente_redis, job_id)
    if estado_del_trabajo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe un trabajo con ese job_id.")
    if estado_del_trabajo["estado"] != EstadoDelTrabajo.WAITING_APPROVAL.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"El trabajo está en {estado_del_trabajo['estado']}, no espera aprobación.")
    lanzar_en_segundo_plano(
        reanudar_trabajo_con_la_decision_humana(cliente_redis, aplicacion.state.orquestador, job_id, decision.aprobado, decision.comentario)
    )
    return {"job_id": job_id, "estado": "RUNNING", "decision": "aprobado" if decision.aprobado else "rechazado"}


@aplicacion.get("/health")
async def verificar_salud() -> dict[str, str]:
    return {"estado": "ok"}
