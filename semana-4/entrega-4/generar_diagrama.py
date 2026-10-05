from pathlib import Path

from langchain_core.runnables.graph_mermaid import draw_mermaid_png

RUTA_DEL_DIAGRAMA: Path = Path(__file__).parent / "diagrama_del_sistema.png"

DIAGRAMA_EN_MERMAID: str = """
graph TD;
    existe{indice existe?} -- no --> crear[create_index serverless, cosine];
    existe -- si --> dimension[verificar dimension];
    archivos([data/*.md]) --> dividir[chunks de 500 tokens + metadatos];
    dividir --> pinecone[(Pinecone namespace)];
    pregunta([pregunta]) --> bm25[BM25: palabras exactas];
    pregunta --> vectorial[Pinecone: significado];
    pinecone --> vectorial;
    bm25 --> fusion[EnsembleRetriever RRF];
    vectorial --> fusion;
    fusion --> top5([top 5]);
    golden([golden_set.json]) --> metricas[Recall y Precision en top 5];
    top5 --> metricas;
"""

if __name__ == "__main__":
    draw_mermaid_png(DIAGRAMA_EN_MERMAID.strip(), output_file_path=str(RUTA_DEL_DIAGRAMA))
    print(f"Diagrama guardado en {RUTA_DEL_DIAGRAMA}")
