import logging
from functools import lru_cache
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.contratos_de_datos import BorradorPropuesto, BorradorPropuestoGuardado
from app.grafo.estado import VistaDelRedactor, leer_respuestas_del_candidato
from app.proveedor_de_modelos import crear_cadena_con_salida_validada

registro: logging.Logger = logging.getLogger("redactor")

plantilla_del_redactor: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Armás el primer borrador de una respuesta de postulación usando SOLO fragmentos copiados literalmente "
            "de lo que dijo el candidato. No podés agregar, cambiar, corregir ni traducir ninguna palabra. "
            "Podés elegir qué fragmentos usar, dejar afuera lo que no responde la pregunta y ordenarlos para que se lean bien. "
            "Cada fragmento tiene que ser una o más frases contiguas, copiadas carácter por carácter.",
        ),
        (
            "human",
            "Pregunta del formulario: {pregunta_del_formulario}\n\nRespuestas del candidato:\n{respuestas_del_candidato}\n\n"
            "Errores de tu intento anterior (corregilos): {errores_de_validacion}",
        ),
    ]
)


@lru_cache(maxsize=1)
def obtener_cadena_del_redactor() -> Runnable:
    return crear_cadena_con_salida_validada(plantilla_del_redactor, BorradorPropuesto)


async def armar_borrador_con_las_frases_del_candidato(estado: VistaDelRedactor) -> dict[str, Any]:
    numero_de_pregunta: int = estado["numero_de_pregunta_actual"]
    respuestas_del_candidato: list[str] = leer_respuestas_del_candidato(estado["transcripcion"], numero_de_pregunta)
    borrador: BorradorPropuesto = await obtener_cadena_del_redactor().ainvoke(
        {
            "pregunta_del_formulario": estado["preguntas_del_formulario"][numero_de_pregunta],
            "respuestas_del_candidato": "\n\n".join(f"- {respuesta}" for respuesta in respuestas_del_candidato),
            "errores_de_validacion": estado["errores_de_validacion"] or "ninguno",
        }
    )
    registro.info("Redactor: borrador con %d fragmentos.", len(borrador.fragmentos_textuales))
    borrador_guardado: BorradorPropuestoGuardado = BorradorPropuestoGuardado(numero_de_pregunta=numero_de_pregunta, **borrador.model_dump())
    return {"borradores_propuestos": [borrador_guardado.model_dump()]}
