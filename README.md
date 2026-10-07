# AI Engineering · Pre-entregas

| # | Pre-entrega | Carpeta |
|---|---|---|
| 1 | Cliente LLM async multi-proveedor | [`pre-entrega-1/codigo`](pre-entrega-1/codigo) |
| 2 | Pipeline de procesamiento validado (LCEL + Pydantic) | [`pre-entrega-2/codigo`](pre-entrega-2/codigo) |
| 3 | RAG local con ChromaDB | [`pre-entrega-3/codigo`](pre-entrega-3/codigo) |
| 4 | RAG escalable en la nube con Pinecone | [`pre-entrega-4/codigo`](pre-entrega-4/codigo) |
| 5 | Agente ReAct con memoria persistente (LangGraph) | [`pre-entrega-5/codigo`](pre-entrega-5/codigo) |
| 6 | Orquestador multi-agente (Supervisor) | [`pre-entrega-6/codigo`](pre-entrega-6/codigo) |
| 7 | API de producción (FastAPI + Redis + LangSmith + HITL) | [`pre-entrega-7/codigo`](pre-entrega-7/codigo) |

Cada `pre-entrega-N/` tiene:

| Carpeta / archivo | Qué contiene |
|---|---|
| `codigo/` | La entrega: código, `README.md` con la consigna como checklist, diagramas y evidencia de ejecución |
| `material-de-clase/` | Slides y notebook de la clase |
| `GUIA_DE_ESTUDIO.md` | Las 5 ideas clave de la semana, con analogías y autoevaluación |

Extra: [`pre-entrega-3/tarea-opcional-similitud`](pre-entrega-3/tarea-opcional-similitud) (similitud coseno con scikit-learn, abre en Colab).
Dependencias globales en `pyproject.toml` (`uv sync`). Las API keys van en `.env` (ver `.env.example` de cada entrega).
