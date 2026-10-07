import asyncio
import math
import os
import time
from typing import Any

import httpx

DIRECCION_DE_LA_API: str = os.getenv("DIRECCION_DE_LA_API", "http://localhost:8000")
SEGUNDOS_ENTRE_CONSULTAS: float = 3.0
SEGUNDOS_MAXIMOS_DE_ESPERA: float = 900.0
ESTADOS_FINALES: set[str] = {"DONE", "FAILED"}

PEDIDOS_DE_PRUEBA: list[str] = [
    "Quiero postularme al puesto de AI Engineer en Pampa AI. ¿Qué tanto encaja mi perfil y qué me falta?",
    "¿Encajo en la oferta de Learning Engineer de Nimbus Edu?",
    "Analizá si me conviene postularme a Data Analyst en Andes Analytics.",
    "¿Qué me falta para el puesto de AI Engineer Jr. de Pampa AI?",
    "Evaluá mi perfil para el puesto de Learning Engineer en Nimbus Edu.",
]


def calcular_percentil(valores: list[float], percentil: float) -> float:
    valores_ordenados: list[float] = sorted(valores)
    posicion: int = max(0, math.ceil(percentil / 100 * len(valores_ordenados)) - 1)
    return valores_ordenados[posicion]


async def ejecutar_una_peticion_completa(cliente: httpx.AsyncClient, numero: int, pedido: str) -> dict[str, Any]:
    inicio: float = time.perf_counter()
    respuesta_de_creacion: httpx.Response = await cliente.post("/tasks", json={"pedido": pedido})
    identificador_del_trabajo: str = respuesta_de_creacion.json()["job_id"]
    print(f"[{numero}] creado {identificador_del_trabajo} en {time.perf_counter() - inicio:.2f}s (la API no se bloquea)")

    while time.perf_counter() - inicio < SEGUNDOS_MAXIMOS_DE_ESPERA:
        await asyncio.sleep(SEGUNDOS_ENTRE_CONSULTAS)
        estado_del_trabajo: dict[str, Any] = (await cliente.get(f"/tasks/{identificador_del_trabajo}")).json()
        if estado_del_trabajo["estado"] == "WAITING_APPROVAL":
            print(f"[{numero}] pausa HITL: {estado_del_trabajo['pedido_de_aprobacion']} -> se aprueba")
            await cliente.post(f"/tasks/{identificador_del_trabajo}/approve", json={"aprobado": True, "comentario": "Aprobado en la prueba de carga"})
        if estado_del_trabajo["estado"] in ESTADOS_FINALES:
            duracion_total: float = time.perf_counter() - inicio
            print(f"[{numero}] {estado_del_trabajo['estado']} en {duracion_total:.1f}s")
            return {"numero": numero, "job_id": identificador_del_trabajo, "estado": estado_del_trabajo["estado"], "segundos": duracion_total}
    return {"numero": numero, "job_id": identificador_del_trabajo, "estado": "TIMEOUT", "segundos": SEGUNDOS_MAXIMOS_DE_ESPERA}


async def lanzar_peticiones_concurrentes() -> None:
    async with httpx.AsyncClient(base_url=DIRECCION_DE_LA_API, timeout=30) as cliente:
        resultados: list[dict[str, Any]] = await asyncio.gather(
            *(ejecutar_una_peticion_completa(cliente, numero, pedido) for numero, pedido in enumerate(PEDIDOS_DE_PRUEBA, start=1))
        )
    duraciones: list[float] = [resultado["segundos"] for resultado in resultados]
    print("\n=== Resumen de la prueba de carga (medido desde el cliente) ===")
    for resultado in resultados:
        print(f"  [{resultado['numero']}] {resultado['estado']:<8} {resultado['segundos']:6.1f}s  job_id={resultado['job_id']}")
    print(f"  Latencia p50: {calcular_percentil(duraciones, 50):.1f}s | p95: {calcular_percentil(duraciones, 95):.1f}s")
    print("  Costo por ejecución y latencia p95: ver el proyecto en https://smith.langchain.com")


if __name__ == "__main__":
    asyncio.run(lanzar_peticiones_concurrentes())
