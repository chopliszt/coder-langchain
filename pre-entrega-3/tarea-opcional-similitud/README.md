# Tarea opcional · Clase 3: ¿los embeddings entienden el significado?

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/chopliszt/coder-langchain/blob/main/pre-entrega-3/tarea-opcional-similitud/similitud_coseno_con_embeddings.ipynb)

Compara **TF-IDF** (palabras compartidas) contra **embeddings** (significado) sobre 5 oraciones que hablan del
despliegue de microservicios con vocabulario distinto y 2 oraciones trampa que comparten palabras clave.
La similitud se calcula con `cosine_similarity` de **scikit-learn**.

| Archivo | Qué es |
|---|---|
| `similitud_coseno_con_embeddings.ipynb` | El notebook (ya ejecutado, con gráficos). Se abre en Colab con el botón de arriba |
| `tarea_similitud_coseno.pdf` | **Entregable**: análisis de las oraciones, código de similitud y diagrama de flujo |
| `diagrama_busqueda_semantica.png` | Diagrama de flujo de una búsqueda semántica |

## Resultado principal

| Método | Similitud entre las 5 reales | Reales vs trampas |
|---|---|---|
| TF-IDF (palabras) | 0,08 | 0,11 |
| Embeddings (`paraphrase-multilingual-mpnet-base-v2`) | **0,45** | **0,24** |

TF-IDF no ve que las 5 reales hablan de lo mismo; los embeddings sí. Pero con una consulta que es solo una lista de
palabras clave, los embeddings también se tientan con las trampas: por eso existe la búsqueda híbrida (clase 4).

## Correrlo localmente

```bash
uv run --with ipykernel jupyter notebook pre-entrega-3/tarea-opcional-similitud/similitud_coseno_con_embeddings.ipynb
```
