from pathlib import Path

from langchain_core.runnables.graph_mermaid import draw_mermaid_png

CARPETA_DE_ESTA_ENTREGA: Path = Path(__file__).parent
RUTA_DEL_DIAGRAMA_DEL_SISTEMA: Path = CARPETA_DE_ESTA_ENTREGA / "diagrama_del_sistema_rag.png"

DIAGRAMA_DEL_SISTEMA_EN_MERMAID: str = """
graph TD;
    subgraph INGESTA["ingest.py (una sola vez)"]
        archivos([data/*.txt]) --> limpieza[limpiar_texto_crudo<br/>regex: espacios y basura];
        limpieza --> division[RecursiveCharacterTextSplitter<br/>500 tokens, 50 de solapamiento, tiktoken];
        division --> vectores_de_ingesta[Embeddings<br/>paraphrase-multilingual-MiniLM];
        vectores_de_ingesta --> chroma[(ChromaDB PersistentClient<br/>upsert con IDs por hash)];
    end
    subgraph CONSULTA["rag_chain.py (cada pregunta, async)"]
        pregunta([pregunta]) --> vectores_de_consulta[MISMO modelo de embeddings];
        vectores_de_consulta --> busqueda[a. busqueda por similitud<br/>top 4 fragmentos];
        chroma --> busqueda;
        busqueda --> contexto[b. armar CONTEXTO con fuentes];
        contexto --> cadena[c. prompt + ChatOpenAI<br/>PydanticOutputParser];
        cadena --> respuesta([d. RespuestaRAG<br/>respuesta + fuentes o 'No lo sé']);
    end
"""

RUTA_DEL_DIAGRAMA_DE_LA_CADENA_LCEL: Path = CARPETA_DE_ESTA_ENTREGA / "diagrama_cadena_lcel.png"


def generar_diagrama_de_la_cadena_lcel() -> None:
    from rag_chain import crear_cadena_rag_completa

    crear_cadena_rag_completa().get_graph().draw_mermaid_png(output_file_path=str(RUTA_DEL_DIAGRAMA_DE_LA_CADENA_LCEL))
    print(f"Diagrama guardado en {RUTA_DEL_DIAGRAMA_DE_LA_CADENA_LCEL}")


if __name__ == "__main__":
    generar_diagrama_de_la_cadena_lcel()
    draw_mermaid_png(DIAGRAMA_DEL_SISTEMA_EN_MERMAID, output_file_path=str(RUTA_DEL_DIAGRAMA_DEL_SISTEMA))
    print(f"Diagrama guardado en {RUTA_DEL_DIAGRAMA_DEL_SISTEMA}")
