# AI Engineering · Pre-entregas 1 a 7

> **Para quien corrige:** las **7 pre-entregas están completas** en este repo, cada una en su carpeta
> `pre-entrega-N/codigo/`. Las carpetas antes se llamaban `semana-N/entrega-N`; se renombraron para coincidir con
> los nombres de la plataforma. Si una corrección menciona `semana-4/entrega-4`, se hizo sobre una copia vieja del repo.

## Índice

| # | Pre-entrega | Carpeta | Archivos que pide la consigna | Evidencia de ejecución |
|---|---|---|---|---|
| 1 | Cliente LLM async multi-proveedor | [`pre-entrega-1/codigo`](pre-entrega-1/codigo) | `clients.py`, `schemas.py`, `main.py` | `evidencia_de_ejecucion.log` |
| 2 | Pipeline validado (LCEL + Pydantic) | [`pre-entrega-2/codigo`](pre-entrega-2/codigo) | `chain.py` (`process_text`), `schemas.py` | `evidencia_de_ejecucion.log` |
| 3 | RAG local con ChromaDB | [`pre-entrega-3/codigo`](pre-entrega-3/codigo) | `ingest.py`, `rag_chain.py` (`get_rag_response`) | `evidencia_de_ejecucion.log` |
| 4 | RAG en la nube con Pinecone + búsqueda híbrida | [`pre-entrega-4/codigo`](pre-entrega-4/codigo) | `inicializar_indice.py`, `ingest.py`, `rag_system.py` (`RAGSystem` con `EnsembleRetriever` BM25 + Pinecone), `evaluate.py` (Recall@5 / Precision@5) | `salida_de_la_evaluacion.txt` |
| 5 | Agente ReAct con memoria (LangGraph) | [`pre-entrega-5/codigo`](pre-entrega-5/codigo) | `grafo.py` (`StateGraph` + `MessagesState` + `ToolNode` + `tools_condition` + `AsyncSqliteSaver` con `thread_id`), `herramientas.py` (`@tool`) | `traza_de_ejecucion.json` / `.log` |
| 6 | Orquestador multi-agente (Supervisor) | [`pre-entrega-6/codigo`](pre-entrega-6/codigo) | `state.py`, `agents/research_agent.py`, `agents/analyst_agent.py`, `graph.py` (Supervisor con `Literal`, Validador) | `demo_delegacion.ipynb`, `traza_de_delegacion.log` |
| 7 | API de producción (FastAPI + Redis + LangSmith + HITL) | [`pre-entrega-7/codigo`](pre-entrega-7/codigo) | `app/main.py` (FastAPI), `app/worker.py` (estados en Redis), `app/hitl.py` (aprobación humana), `app/observability.py` (LangSmith), `docker-compose.yml` (Redis) | `screenshots/`, `salida_prueba_de_carga.txt` |

Cada `codigo/README.md` tiene la **consigna oficial como checklist**, indicando qué archivo cumple cada punto, el diagrama
del grafo y los pasos para correrla.

## Cómo correrlo en un entorno limpio

Requiere **Python 3.12+**.

```bash
git clone https://github.com/chopliszt/coder-langchain && cd coder-langchain
uv sync                                    # o, por entrega: pip install -r pre-entrega-N/codigo/requirements.txt
cp pre-entrega-N/codigo/.env.example .env  # completar las keys (ver tabla)
uv run python pre-entrega-N/codigo/main.py
```

| Pre-entrega | Keys necesarias en `.env` | Comando principal (desde la raíz) |
|---|---|---|
| 1 | `GOOGLE_API_KEY` (y opcional `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) | `uv run python pre-entrega-1/codigo/main.py` |
| 2 | `GOOGLE_API_KEY` | `uv run python pre-entrega-2/codigo/main.py` |
| 3 | `GOOGLE_API_KEY` (los embeddings son locales y gratis) | `uv run python pre-entrega-3/codigo/main.py` |
| 4 | `PINECONE_API_KEY`, `INDEX_NAME` | `inicializar_indice.py` → `ingest.py` → `evaluate.py` |
| 5 | `GOOGLE_API_KEY` | `uv run python pre-entrega-5/codigo/main.py` |
| 6 | `GOOGLE_API_KEY` | `uv run python pre-entrega-6/codigo/main.py` |
| 7 | `GOOGLE_API_KEY`, `LANGSMITH_API_KEY`, `REDIS_URL` | `docker compose -f pre-entrega-7/codigo/docker-compose.yml up -d` (o `brew services start redis`) y luego `uvicorn` (ver su README) |

El proveedor de LLM se elige con `PROVEEDOR_LLM` = `gemini` (por defecto) | `openai` | `anthropic`.
**Ninguna API key está en el repo**: solo los `.env.example` vacíos.

## Estructura

| Carpeta / archivo | Qué contiene |
|---|---|
| `pre-entrega-N/codigo/` | La entrega: código, README con checklist, diagramas y evidencia |
| `pre-entrega-N/material-de-clase/` | Slides y notebook de la clase |
| `pre-entrega-N/GUIA_DE_ESTUDIO.md` | Las 5 ideas clave de la semana, con autoevaluación |
| `pyproject.toml` + `uv.lock` | Dependencias de todo el repo |

Extra: [`pre-entrega-3/tarea-opcional-similitud`](pre-entrega-3/tarea-opcional-similitud) (similitud coseno con scikit-learn, abre en Colab).
