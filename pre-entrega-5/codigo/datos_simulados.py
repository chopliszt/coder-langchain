EMPRESAS_POR_NOMBRE: dict[str, int] = {
    "pampa ai": 101,
    "nimbus edu": 102,
    "andes analytics": 103,
    "rio de la plata labs": 104,
}

POSTULACIONES_POR_EMPRESA: dict[int, list[dict[str, str]]] = {
    101: [
        {
            "puesto": "AI Engineer Jr.",
            "fecha_de_postulacion": "2026-09-02",
            "estado": "entrevista técnica agendada",
            "proximo_paso": "Entrevista técnica el 2026-10-09 a las 15:00 (live coding en Python + LangChain)",
            "contacto": "Recruiter: Sofía M.",
        },
    ],
    102: [
        {
            "puesto": "Product Manager de IA educativa",
            "fecha_de_postulacion": "2026-08-20",
            "estado": "rechazada",
            "proximo_paso": "Ninguno. Feedback recibido: buscaban más experiencia en métricas de producto.",
            "contacto": "Talent team",
        },
        {
            "puesto": "Learning Engineer",
            "fecha_de_postulacion": "2026-09-15",
            "estado": "en revisión de CV",
            "proximo_paso": "Esperar respuesta; hacer seguimiento por mail el 2026-10-06 si no hay novedades",
            "contacto": "Hiring manager: Diego R.",
        },
    ],
    103: [
        {
            "puesto": "Data Analyst",
            "fecha_de_postulacion": "2026-07-30",
            "estado": "oferta recibida",
            "proximo_paso": "Responder la oferta antes del 2026-10-10",
            "contacto": "HR: Carla P.",
        },
    ],
    104: [],
}
