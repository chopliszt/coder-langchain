import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

from langchain_core.documents import Document

from configuracion import CANTIDAD_DE_DOCUMENTOS_A_DEVOLVER, CARPETA_DE_ESTA_ENTREGA, RUTA_DEL_GOLDEN_SET
from rag_system import RAGSystem
from schemas import CasoDelGoldenSet, ResultadoDeUnaPregunta

RUTA_DEL_REPORTE_EN_JSON: Path = CARPETA_DE_ESTA_ENTREGA / "resultado_de_la_evaluacion.json"

FuncionDeBusqueda = Callable[[str], Awaitable[list[Document]]]


def cargar_golden_set() -> list[CasoDelGoldenSet]:
    casos_en_crudo: list[dict[str, str]] = json.loads(RUTA_DEL_GOLDEN_SET.read_text(encoding="utf-8"))
    return [CasoDelGoldenSet(**caso) for caso in casos_en_crudo]


def calcular_recall_en_5(documento_id_esperado: str, documentos_recuperados: list[str]) -> float:
    return 1.0 if documento_id_esperado in documentos_recuperados else 0.0


def calcular_precision_en_5(documento_id_esperado: str, documentos_recuperados: list[str]) -> float:
    cantidad_de_documentos_utiles: int = sum(1 for documento_id in documentos_recuperados if documento_id == documento_id_esperado)
    return cantidad_de_documentos_utiles / CANTIDAD_DE_DOCUMENTOS_A_DEVOLVER


async def evaluar_una_estrategia_de_busqueda(
    funcion_de_busqueda: FuncionDeBusqueda, golden_set: list[CasoDelGoldenSet]
) -> list[ResultadoDeUnaPregunta]:
    resultados: list[ResultadoDeUnaPregunta] = []
    for caso in golden_set:
        fragmentos_recuperados: list[Document] = await funcion_de_busqueda(caso.pregunta)
        documentos_recuperados: list[str] = [fragmento.metadata["documento_id"] for fragmento in fragmentos_recuperados]
        resultados.append(
            ResultadoDeUnaPregunta(
                pregunta=caso.pregunta,
                documento_id_esperado=caso.documento_id_esperado,
                documentos_recuperados=documentos_recuperados,
                recall_en_5=calcular_recall_en_5(caso.documento_id_esperado, documentos_recuperados),
                precision_en_5=calcular_precision_en_5(caso.documento_id_esperado, documentos_recuperados),
            )
        )
    return resultados


def calcular_promedio(valores: list[float]) -> float:
    return sum(valores) / len(valores) if valores else 0.0


def imprimir_reporte_de_una_estrategia(nombre_de_la_estrategia: str, resultados: list[ResultadoDeUnaPregunta]) -> dict[str, float]:
    print(f"\n=== {nombre_de_la_estrategia} ===")
    for resultado in resultados:
        marca: str = "OK " if resultado.recall_en_5 == 1.0 else "MAL"
        print(f"[{marca}] {resultado.pregunta}")
        print(f"      esperado: {resultado.documento_id_esperado}")
        print(f"      top 5:    {resultado.documentos_recuperados}")
        print(f"      Recall@5 = {resultado.recall_en_5:.0%} | Precision@5 = {resultado.precision_en_5:.0%}")
    promedios: dict[str, float] = {
        "recall_en_5_promedio": calcular_promedio([resultado.recall_en_5 for resultado in resultados]),
        "precision_en_5_promedio": calcular_promedio([resultado.precision_en_5 for resultado in resultados]),
    }
    print(f"  >> Recall@5 promedio: {promedios['recall_en_5_promedio']:.0%} | Precision@5 promedio: {promedios['precision_en_5_promedio']:.0%}")
    return promedios


async def ejecutar_evaluacion_completa() -> None:
    golden_set: list[CasoDelGoldenSet] = cargar_golden_set()
    sistema_rag: RAGSystem = RAGSystem()

    estrategias_a_comparar: dict[str, FuncionDeBusqueda] = {
        "Solo palabras clave (BM25)": sistema_rag.recuperar_top_5_solo_por_palabras_clave,
        "Solo significado (Pinecone)": sistema_rag.recuperar_top_5_solo_por_significado,
        "Híbrido (EnsembleRetriever = BM25 + Pinecone)": sistema_rag.recuperar_top_5_documentos,
    }

    reporte_completo: dict[str, dict[str, object]] = {}
    for nombre_de_la_estrategia, funcion_de_busqueda in estrategias_a_comparar.items():
        resultados: list[ResultadoDeUnaPregunta] = await evaluar_una_estrategia_de_busqueda(funcion_de_busqueda, golden_set)
        promedios: dict[str, float] = imprimir_reporte_de_una_estrategia(nombre_de_la_estrategia, resultados)
        reporte_completo[nombre_de_la_estrategia] = {**promedios, "detalle": [resultado.model_dump() for resultado in resultados]}

    print("\n=== RESUMEN ===")
    for nombre_de_la_estrategia, datos in reporte_completo.items():
        print(f"{nombre_de_la_estrategia:<48} Recall@5 {datos['recall_en_5_promedio']:.0%}   Precision@5 {datos['precision_en_5_promedio']:.0%}")

    RUTA_DEL_REPORTE_EN_JSON.write_text(json.dumps(reporte_completo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReporte guardado en {RUTA_DEL_REPORTE_EN_JSON.name}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(ejecutar_evaluacion_completa())
