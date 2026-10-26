import logging
from functools import lru_cache
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.configuracion import RUTA_DEL_PERFIL_DEL_CANDIDATO
from app.contratos_de_datos import ContextoDelPuestoGuardado, PreguntaDelEntrevistador, TurnoDeLaEntrevista
from app.grafo.estado import VistaDelEntrevistador, convertir_turnos_en_texto, leer_contexto_de_la_pregunta, leer_turnos_de_la_pregunta
from app.proveedor_de_modelos import crear_cadena_con_salida_validada

registro: logging.Logger = logging.getLogger("entrevistador")

plantilla_del_entrevistador: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Sos un entrevistador que ayuda a un candidato a encontrar SUS PROPIAS palabras para responder una pregunta "
            "de un formulario de postulación. Reglas:\n"
            "1. Hacés UNA sola pregunta, corta y abierta.\n"
            "2. Nunca proponés contenido, ejemplos ni respuestas. Prohibido: 'podrías contar que...', 'por ejemplo, cuando...'.\n"
            "3. Si ya hay respuestas, repreguntá apoyándote en una frase textual del candidato (citala entre comillas) "
            "para profundizar: un ejemplo concreto, un resultado medible, qué cambió o por qué.\n"
            "4. Usá el perfil y el contexto del puesto solo para elegir QUÉ explorar (un hueco, una conexión con lo que pide el puesto), "
            "siempre formulado como pregunta abierta.\n"
            "5. Escribí en el mismo idioma que la pregunta del formulario.",
        ),
        (
            "human",
            "Puesto: {puesto} en {empresa}\nPregunta del formulario: {pregunta_del_formulario}\n\n"
            "Contexto del puesto (de los documentos de la empresa):\n{contexto_del_puesto}\n\n"
            "Perfil del candidato:\n{perfil_del_candidato}\n\nConversación hasta ahora:\n{conversacion}",
        ),
    ]
)


@lru_cache(maxsize=1)
def leer_perfil_del_candidato() -> str:
    return RUTA_DEL_PERFIL_DEL_CANDIDATO.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def obtener_cadena_del_entrevistador() -> Runnable:
    return crear_cadena_con_salida_validada(plantilla_del_entrevistador, PreguntaDelEntrevistador, temperatura=0.4)


async def formular_la_siguiente_pregunta_al_candidato(estado: VistaDelEntrevistador) -> dict[str, Any]:
    numero_de_pregunta: int = estado["numero_de_pregunta_actual"]
    contexto: ContextoDelPuestoGuardado | None = leer_contexto_de_la_pregunta(estado["contextos_del_puesto"], numero_de_pregunta)
    pregunta: PreguntaDelEntrevistador = await obtener_cadena_del_entrevistador().ainvoke(
        {
            "puesto": estado["puesto"],
            "empresa": estado["empresa"],
            "pregunta_del_formulario": estado["preguntas_del_formulario"][numero_de_pregunta],
            "contexto_del_puesto": "\n".join(f"- {punto}" for punto in contexto.puntos_clave) if contexto else "(sin contexto)",
            "perfil_del_candidato": leer_perfil_del_candidato(),
            "conversacion": convertir_turnos_en_texto(leer_turnos_de_la_pregunta(estado["transcripcion"], numero_de_pregunta)),
        }
    )
    registro.info("Entrevistador pregunta: %s", pregunta.pregunta)
    turno: TurnoDeLaEntrevista = TurnoDeLaEntrevista(numero_de_pregunta=numero_de_pregunta, autor="entrevistador", texto=pregunta.pregunta)
    return {"transcripcion": [turno.model_dump()]}
