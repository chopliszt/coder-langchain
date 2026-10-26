import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, status
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, StateSnapshot

from app.api.esquemas import DetalleDeLaEntrevista, EstadoPublicoDeLaEntrevista, PedidoDeNuevaEntrevista
from app.configuracion import DIRECCION_DE_REDIS, LIMITE_DE_PASOS_POR_INVOCACION_DEL_GRAFO
from app.contratos_de_datos import BorradorAprobado, RespuestaDelCandidato, TurnoDeLaEntrevista
from app.grafo.construccion import compilar_grafo_con_persistencia
from app.grafo.estado import crear_estado_inicial
from app.observabilidad import configurar_registro_de_la_aplicacion, verificar_trazas_en_langsmith

configurar_registro_de_la_aplicacion()
registro: logging.Logger = logging.getLogger("api")


@asynccontextmanager
async def ciclo_de_vida_de_la_api(aplicacion: FastAPI) -> AsyncIterator[None]:
    verificar_trazas_en_langsmith()
    async with AsyncRedisSaver.from_conn_string(DIRECCION_DE_REDIS) as guardador_de_checkpoints:
        await guardador_de_checkpoints.asetup()
        aplicacion.state.grafo_de_la_entrevista = compilar_grafo_con_persistencia(guardador_de_checkpoints)
        registro.info("Grafo compilado con checkpointer en Redis (%s).", DIRECCION_DE_REDIS)
        yield


aplicacion: FastAPI = FastAPI(
    title="Entrevistador de postulaciones",
    description="Te entrevista sobre las preguntas largas de un formulario de postulación y arma el borrador SOLO con tus frases.",
    lifespan=ciclo_de_vida_de_la_api,
)


def obtener_grafo() -> CompiledStateGraph:
    return aplicacion.state.grafo_de_la_entrevista


def crear_configuracion_de_la_ejecucion(identificador_de_la_entrevista: str) -> RunnableConfig:
    return {
        "configurable": {"thread_id": identificador_de_la_entrevista},
        "recursion_limit": LIMITE_DE_PASOS_POR_INVOCACION_DEL_GRAFO,
        "run_name": "entrevista",
        "metadata": {"thread_id": identificador_de_la_entrevista},
    }


def armar_estado_publico(identificador_de_la_entrevista: str, foto_del_estado: StateSnapshot) -> dict[str, Any]:
    valores: dict[str, Any] = foto_del_estado.values
    pausa_pendiente: dict[str, Any] | None = foto_del_estado.interrupts[0].value if foto_del_estado.interrupts else None
    return {
        "identificador_de_la_entrevista": identificador_de_la_entrevista,
        "estado": "esperando_respuesta" if pausa_pendiente else "terminada",
        "numero_de_pregunta_del_formulario": pausa_pendiente["numero_de_pregunta"] if pausa_pendiente else None,
        "pregunta_pendiente": pausa_pendiente["pregunta"] if pausa_pendiente else None,
        "borradores_aprobados": [BorradorAprobado.model_validate(borrador) for borrador in valores.get("borradores_aprobados", [])],
    }


async def leer_foto_del_estado_o_fallar(identificador_de_la_entrevista: str) -> StateSnapshot:
    foto_del_estado: StateSnapshot = await obtener_grafo().aget_state(crear_configuracion_de_la_ejecucion(identificador_de_la_entrevista))
    if not foto_del_estado.values:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe una entrevista con ese identificador.")
    return foto_del_estado


async def ejecutar_el_grafo_hasta_la_proxima_pausa(identificador_de_la_entrevista: str, entrada_del_grafo: Any) -> EstadoPublicoDeLaEntrevista:
    configuracion: RunnableConfig = crear_configuracion_de_la_ejecucion(identificador_de_la_entrevista)
    try:
        await obtener_grafo().ainvoke(entrada_del_grafo, configuracion)
    except Exception as error:
        registro.exception("Falló la ejecución del grafo de la entrevista %s", identificador_de_la_entrevista)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falló el proveedor del LLM o una validación: {error}. Lo ya respondido quedó guardado en el checkpoint.",
        ) from error
    foto_del_estado: StateSnapshot = await obtener_grafo().aget_state(configuracion)
    return EstadoPublicoDeLaEntrevista.model_validate(armar_estado_publico(identificador_de_la_entrevista, foto_del_estado))


@aplicacion.post("/entrevistas", status_code=status.HTTP_201_CREATED, response_model=EstadoPublicoDeLaEntrevista)
async def empezar_entrevista(pedido: PedidoDeNuevaEntrevista) -> EstadoPublicoDeLaEntrevista:
    identificador_de_la_entrevista: str = str(uuid.uuid4())
    registro.info("Nueva entrevista %s: %s en %s", identificador_de_la_entrevista, pedido.puesto, pedido.empresa)
    estado_inicial: dict[str, Any] = crear_estado_inicial(pedido.empresa, pedido.puesto, pedido.preguntas_del_formulario)
    return await ejecutar_el_grafo_hasta_la_proxima_pausa(identificador_de_la_entrevista, estado_inicial)


@aplicacion.post("/entrevistas/{identificador_de_la_entrevista}/respuestas", response_model=EstadoPublicoDeLaEntrevista)
async def responder_pregunta_pendiente(identificador_de_la_entrevista: str, respuesta: RespuestaDelCandidato) -> EstadoPublicoDeLaEntrevista:
    foto_del_estado: StateSnapshot = await leer_foto_del_estado_o_fallar(identificador_de_la_entrevista)
    if not foto_del_estado.interrupts:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta entrevista no está esperando una respuesta.")
    return await ejecutar_el_grafo_hasta_la_proxima_pausa(identificador_de_la_entrevista, Command(resume=respuesta.texto))


@aplicacion.get("/entrevistas/{identificador_de_la_entrevista}", response_model=DetalleDeLaEntrevista)
async def consultar_entrevista(identificador_de_la_entrevista: str) -> DetalleDeLaEntrevista:
    foto_del_estado: StateSnapshot = await leer_foto_del_estado_o_fallar(identificador_de_la_entrevista)
    valores: dict[str, Any] = foto_del_estado.values
    return DetalleDeLaEntrevista(
        **armar_estado_publico(identificador_de_la_entrevista, foto_del_estado),
        empresa=valores["empresa"],
        puesto=valores["puesto"],
        preguntas_del_formulario=valores["preguntas_del_formulario"],
        transcripcion=[TurnoDeLaEntrevista.model_validate(turno) for turno in valores.get("transcripcion", [])],
    )


@aplicacion.get("/salud")
async def verificar_salud() -> dict[str, str]:
    return {"estado": "ok"}
