import logging
import re
from typing import Any

from app.configuracion import MAXIMO_DE_INTENTOS_DE_REDACCION
from app.contratos_de_datos import BorradorAprobado, BorradorPropuestoGuardado
from app.grafo.estado import VistaDelValidador, leer_borradores_propuestos_de_la_pregunta, leer_respuestas_del_candidato

registro: logging.Logger = logging.getLogger("validador")

SIGNOS_A_IGNORAR_EN_LOS_BORDES: str = " .,;:!?¡¿\"'«»“”…-—"


def normalizar_texto_para_comparar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.lower()).strip(SIGNOS_A_IGNORAR_EN_LOS_BORDES)


def el_fragmento_esta_en_las_respuestas(fragmento: str, respuestas_normalizadas: str) -> bool:
    fragmento_normalizado: str = normalizar_texto_para_comparar(fragmento)
    return bool(fragmento_normalizado) and fragmento_normalizado in respuestas_normalizadas


async def descartar_frases_que_no_estan_en_la_transcripcion(estado: VistaDelValidador) -> dict[str, Any]:
    numero_de_pregunta: int = estado["numero_de_pregunta_actual"]
    borradores_de_la_pregunta: list[BorradorPropuestoGuardado] = leer_borradores_propuestos_de_la_pregunta(
        estado["borradores_propuestos"], numero_de_pregunta
    )
    ultimo_borrador: BorradorPropuestoGuardado = borradores_de_la_pregunta[-1]
    respuestas_normalizadas: str = normalizar_texto_para_comparar(" \n ".join(leer_respuestas_del_candidato(estado["transcripcion"], numero_de_pregunta)))

    fragmentos_validos: list[str] = [
        fragmento for fragmento in ultimo_borrador.fragmentos_textuales if el_fragmento_esta_en_las_respuestas(fragmento, respuestas_normalizadas)
    ]
    fragmentos_inventados: list[str] = [fragmento for fragmento in ultimo_borrador.fragmentos_textuales if fragmento not in fragmentos_validos]
    quedan_intentos: bool = len(borradores_de_la_pregunta) < MAXIMO_DE_INTENTOS_DE_REDACCION

    if fragmentos_inventados and quedan_intentos:
        registro.warning("Validador: %d fragmentos no son textuales. Vuelve al Redactor.", len(fragmentos_inventados))
        return {"errores_de_validacion": [f"Este fragmento no aparece literal en las respuestas: «{fragmento}»" for fragmento in fragmentos_inventados]}

    borrador_aprobado: BorradorAprobado = BorradorAprobado(
        numero_de_pregunta=numero_de_pregunta,
        pregunta_del_formulario=estado["preguntas_del_formulario"][numero_de_pregunta],
        texto=" ".join(fragmentos_validos),
        fragmentos_descartados=fragmentos_inventados,
    )
    registro.info("Validador: borrador aprobado (%d fragmentos descartados).", len(fragmentos_inventados))
    return {"errores_de_validacion": [], "borradores_aprobados": [borrador_aprobado.model_dump()]}
