import logging
from typing import Any

from langgraph.types import interrupt

from app.contratos_de_datos import RespuestaDelCandidato, TurnoDeLaEntrevista
from app.grafo.estado import VistaDelCandidato

registro: logging.Logger = logging.getLogger("candidato")


async def pausar_hasta_recibir_la_respuesta(estado: VistaDelCandidato) -> dict[str, Any]:
    numero_de_pregunta: int = estado["numero_de_pregunta_actual"]
    ultima_pregunta: TurnoDeLaEntrevista = TurnoDeLaEntrevista.model_validate(estado["transcripcion"][-1])
    texto_recibido: str = interrupt({"numero_de_pregunta": numero_de_pregunta, "pregunta": ultima_pregunta.texto})
    respuesta: RespuestaDelCandidato = RespuestaDelCandidato(texto=texto_recibido)
    registro.info("Respuesta recibida para la pregunta %d (%d caracteres).", numero_de_pregunta, len(respuesta.texto))
    turno: TurnoDeLaEntrevista = TurnoDeLaEntrevista(numero_de_pregunta=numero_de_pregunta, autor="candidato", texto=respuesta.texto)
    return {"transcripcion": [turno.model_dump()]}
