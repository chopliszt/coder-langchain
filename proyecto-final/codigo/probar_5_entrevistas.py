import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

DIRECCION_DE_LA_API: str = "http://localhost:8000"
RUTA_DE_LA_EVIDENCIA: Path = Path(__file__).parent / "evidencia_de_las_5_pruebas.json"
SEGUNDOS_DE_ESPERA_POR_PEDIDO: float = 300.0
MAXIMO_DE_RESPUESTAS_POR_PRUEBA: int = 12


class PruebaDeEntrevista(BaseModel):
    nombre: str
    empresa: str
    puesto: str
    preguntas_del_formulario: list[str]
    respuestas_guionadas_de_la_candidata: list[str]


PRUEBAS: list[PruebaDeEntrevista] = [
    PruebaDeEntrevista(
        nombre="1. Por qué la empresa, respuestas completas",
        empresa="nimbus-edu",
        puesto="Learning Engineer",
        preguntas_del_formulario=["¿Por qué querés trabajar en Nimbus Edu?"],
        respuestas_guionadas_de_la_candidata=[
            "Fui profesora de Física siete años en un colegio IB y vi de cerca cómo la IA podía ayudar o arruinar el pensamiento crítico de los alumnos. "
            "Me gusta que Nimbus diga que el alumno piensa primero y la IA ayuda después, porque es lo mismo que yo pedía en mis clases.",
            "En 2022 armé un taller donde los alumnos escribían su hipótesis a mano antes de usar un chatbot. Las notas de los informes de laboratorio subieron y dejaron de copiar.",
            "Quiero hacer eso a escala: en mi colegio llegué a 40 docentes y Nimbus llega a 120 colegios.",
        ],
    ),
    PruebaDeEntrevista(
        nombre="2. Respuestas vagas: el entrevistador tiene que repreguntar",
        empresa="nimbus-edu",
        puesto="Learning Engineer",
        preguntas_del_formulario=["Contanos de una vez que ayudaste a un grupo de docentes a adoptar una herramienta nueva."],
        respuestas_guionadas_de_la_candidata=[
            "Sí, eso lo hice varias veces en el colegio.",
            "Fue con la plataforma de aprendizaje nueva, en 2021. Al principio la mitad de los docentes no la usaba.",
            "Hice talleres cortos por departamento y nombré a un docente referente en cada uno. En seis meses 36 de los 40 docentes la usaban todas las semanas.",
        ],
    ),
    PruebaDeEntrevista(
        nombre="3. Otra empresa: el RAG tiene que filtrar por metadatos de Pampa AI",
        empresa="pampa-ai",
        puesto="AI Engineer Jr.",
        preguntas_del_formulario=["¿Por qué querés trabajar en Pampa AI?"],
        respuestas_guionadas_de_la_candidata=[
            "Porque el 60 por ciento de sus clientes son instituciones educativas y yo vengo de la educación. Entiendo cómo piensa un colegio cuando compra tecnología.",
            "En mi trabajo actual de Customer Success acompaño a 25 colegios y veo que los asistentes que fracasan son los que nadie pidió. Me gusta que Pampa hable con el usuario antes de escribir código.",
            "También me identifico con medir antes de opinar: en la startup armé un tablero de uso semanal para detectar colegios en riesgo de no renovar.",
        ],
    ),
    PruebaDeEntrevista(
        nombre="4. Proyecto técnico con LLMs",
        empresa="pampa-ai",
        puesto="AI Engineer Jr.",
        preguntas_del_formulario=["Contanos de un proyecto con LLMs que hayas construido: qué problema resolvía y qué aprendiste."],
        respuestas_guionadas_de_la_candidata=[
            "Construí un asistente con RAG que responde preguntas de docentes sobre el reglamento del colegio, con LangChain y Chroma.",
            "El problema era que los docentes mandaban las mismas preguntas por mail a coordinación. El asistente responde citando el artículo del reglamento y si no sabe dice no lo sé.",
            "Aprendí que el tamaño de los fragmentos cambia todo: con fragmentos muy grandes las respuestas mezclaban artículos.",
        ],
    ),
    PruebaDeEntrevista(
        nombre="5. Dos preguntas en la misma entrevista (avanza de pregunta y vuelve a investigar)",
        empresa="pampa-ai",
        puesto="AI Engineer Jr.",
        preguntas_del_formulario=[
            "¿Por qué querés trabajar en Pampa AI?",
            "Contanos de un proyecto con LLMs que hayas construido: qué problema resolvía y qué aprendiste.",
        ],
        respuestas_guionadas_de_la_candidata=[
            "Quiero trabajar en Pampa AI porque combina las dos cosas que sé hacer: educación y asistentes con IA.",
            "Me gusta que cada viernes alguien presente un error que cometió. En el colegio hacíamos algo parecido entre docentes y cambió cómo enseñábamos.",
            "Además trabajan en Uruguay y yo vivo en Montevideo, así que conozco a varios de sus clientes.",
            "Hice un asistente con RAG para el reglamento del colegio, con LangChain y Chroma.",
            "Resolvía que coordinación recibía cuarenta mails por semana con las mismas dudas. Bajaron a menos de diez.",
            "Aprendí a medir: armé diez preguntas de prueba y las corría cada vez que cambiaba algo.",
        ],
    ),
]


async def correr_una_prueba(cliente: httpx.AsyncClient, prueba: PruebaDeEntrevista) -> dict[str, Any]:
    inicio: float = time.perf_counter()
    respuesta_http: httpx.Response = await cliente.post(
        "/entrevistas",
        json={"empresa": prueba.empresa, "puesto": prueba.puesto, "preguntas_del_formulario": prueba.preguntas_del_formulario},
    )
    respuesta_http.raise_for_status()
    estado: dict[str, Any] = respuesta_http.json()
    identificador: str = estado["identificador_de_la_entrevista"]
    print(f"\n=== {prueba.nombre} ({identificador})")

    respuestas_enviadas: int = 0
    while estado["estado"] == "esperando_respuesta" and respuestas_enviadas < MAXIMO_DE_RESPUESTAS_POR_PRUEBA:
        indice_de_respuesta: int = min(respuestas_enviadas, len(prueba.respuestas_guionadas_de_la_candidata) - 1)
        respuesta_de_la_candidata: str = prueba.respuestas_guionadas_de_la_candidata[indice_de_respuesta]
        print(f"  Entrevistador: {estado['pregunta_pendiente']}\n  Candidata: {respuesta_de_la_candidata}")
        respuesta_http = await cliente.post(f"/entrevistas/{identificador}/respuestas", json={"texto": respuesta_de_la_candidata})
        respuesta_http.raise_for_status()
        estado = respuesta_http.json()
        respuestas_enviadas += 1

    for borrador in estado["borradores_aprobados"]:
        print(f"  BORRADOR ({borrador['pregunta_del_formulario']}):\n    {borrador['texto']}")
        if borrador["fragmentos_descartados"]:
            print(f"    Descartados por el validador: {borrador['fragmentos_descartados']}")
    detalle: dict[str, Any] = (await cliente.get(f"/entrevistas/{identificador}")).json()
    return {
        "prueba": prueba.nombre,
        "identificador_de_la_entrevista": identificador,
        "estado_final": estado["estado"],
        "respuestas_enviadas": respuestas_enviadas,
        "segundos": round(time.perf_counter() - inicio, 1),
        "transcripcion": detalle["transcripcion"],
        "borradores_aprobados": estado["borradores_aprobados"],
    }


async def correr_las_pruebas(indices_elegidos: list[int]) -> None:
    resultados: list[dict[str, Any]] = []
    async with httpx.AsyncClient(base_url=DIRECCION_DE_LA_API, timeout=SEGUNDOS_DE_ESPERA_POR_PEDIDO) as cliente:
        for indice in indices_elegidos:
            resultados.append(await correr_una_prueba(cliente, PRUEBAS[indice]))
    RUTA_DE_LA_EVIDENCIA.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nEvidencia guardada en {RUTA_DE_LA_EVIDENCIA.name}")
    for resultado in resultados:
        print(f"- {resultado['prueba']}: {resultado['estado_final']} en {resultado['segundos']} s, {resultado['respuestas_enviadas']} respuestas")


if __name__ == "__main__":
    indices_pedidos: list[int] = [int(argumento) - 1 for argumento in sys.argv[1:]] or list(range(len(PRUEBAS)))
    asyncio.run(correr_las_pruebas(indices_pedidos))
