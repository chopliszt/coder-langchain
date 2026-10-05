# Pre-entrega 7 · API de producción y monitoreo activo

API REST (**FastAPI**) que expone el orquestador multi-agente del Módulo 6 (evaluador de postulaciones laborales):
recibe la tarea, la **encola** y devuelve un `job_id` al instante; el trabajo corre en segundo plano, su estado y los
checkpoints de LangGraph viven en **Redis**, cada ejecución se traza en **LangSmith**, y antes de la única acción con
efectos externos (**enviar la postulación**) el grafo se **pausa hasta recibir aprobación humana**.

![Grafo con Human-in-the-loop](diagrama_del_grafo.png)

## Consigna (checklist oficial)

- [x] Endpoint asíncrono que encola y devuelve un `job_id` sin bloquear el event loop → `POST /tasks` (responde 202 en milisegundos)
- [x] Estado del job persistido en Redis, incluido el paso a `FAILED` ante una excepción → `worker.py`
- [x] Checkpoints de LangGraph en Redis → `AsyncRedisSaver`
- [x] Trazas visibles en el dashboard (LangSmith) con captura en `/screenshots`
- [x] Capturas del costo por ejecución y la latencia p95 de las 5 peticiones concurrentes en `/screenshots`
- [x] Nodo Human-in-the-loop que pausa la ejecución hasta recibir aprobación externa → `hitl.py` + `POST /tasks/{id}/approve`
- [x] README con pasos para inicializar Redis y la API, cómo lanzar las 5 peticiones concurrentes, y `requirements.txt`

## Estructura

```
entrega-7/
├── app/
│   ├── main.py            # FastAPI: POST /tasks, GET /tasks/{id}, POST /tasks/{id}/approve, GET /health
│   ├── graph.py           # orquestador del M6 + nodos HITL + compilación con checkpointer de Redis
│   ├── worker.py          # corre el grafo en segundo plano y guarda PENDING/RUNNING/WAITING_APPROVAL/DONE/FAILED en Redis
│   ├── observability.py   # configuración de LangSmith (las funciones del worker usan @traceable)
│   ├── hitl.py            # detecta la acción crítica, interrupt() y reanudación con Command(resume=...)
│   ├── state.py, agents/, data/, proveedor_de_modelos.py   # el sistema multi-agente del Módulo 6
├── lanzar_5_peticiones_concurrentes.py   # prueba de carga: 5 tareas a la vez, aprueba las pausas, mide p50/p95
├── requirements.txt
├── .env.example
└── screenshots/           # capturas del dashboard de LangSmith
```

## Estados de un trabajo

```
PENDING -> RUNNING -> WAITING_APPROVAL --(POST /approve)--> RUNNING -> DONE
                  \-> DONE (si no hay acción crítica)
cualquier excepción -> FAILED (con el error guardado en Redis, el cliente deja de esperar)
```

**¿Qué es "crítico"?** Si el perfil cumple ≥ 60% de los requisitos, el sistema propone **enviar la postulación**: es una
acción con efectos externos (no se puede deshacer), así que se pausa con `interrupt()` hasta que un humano apruebe o
rechace. Si se rechaza, termina sin enviar. Si la coincidencia es baja, no hay nada crítico que aprobar y termina en `DONE`.

## Cómo levantarlo (sin Docker)

1. **Redis** (la versión 8 ya incluye los módulos de búsqueda y JSON que necesita `AsyncRedisSaver`):
   ```bash
   brew install redis            # en Linux: apt install redis / o Redis Stack
   brew services start redis
   redis-cli ping                # -> PONG
   ```
2. **LangSmith**: crear una cuenta gratis en [smith.langchain.com](https://smith.langchain.com) → Settings → API Keys.
3. **Variables**: copiar `.env.example` a la raíz del repo como `.env` y completar `GOOGLE_API_KEY` y `LANGSMITH_API_KEY`.
4. **Dependencias y API**:
   ```bash
   uv sync                                   # o: pip install -r semana-7/entrega-7/requirements.txt
   cd semana-7/entrega-7/app
   uv run uvicorn main:aplicacion --port 8000
   ```
   Documentación interactiva: http://localhost:8000/docs

## Probar a mano

```bash
curl -X POST localhost:8000/tasks -H 'content-type: application/json' \
     -d '{"pedido": "Quiero postularme al puesto de AI Engineer en Pampa AI. ¿Qué tanto encaja mi perfil?"}'
# -> {"job_id": "...", "estado": "PENDING"}

curl localhost:8000/tasks/<job_id>               # RUNNING ... WAITING_APPROVAL (con el pedido de aprobación)
curl -X POST localhost:8000/tasks/<job_id>/approve -H 'content-type: application/json' \
     -d '{"aprobado": true, "comentario": "Enviala"}'
curl localhost:8000/tasks/<job_id>               # DONE, postulacion_enviada: true
```

## Prueba de carga: 5 peticiones concurrentes

Con la API corriendo, en otra terminal:

```bash
uv run python semana-7/entrega-7/lanzar_5_peticiones_concurrentes.py
```

Lanza 5 tareas a la vez con `asyncio.gather`, consulta su estado, aprueba automáticamente las pausas HITL y al final
imprime la latencia de cada una con p50 y p95. Después, en LangSmith → proyecto `orquestador-postulaciones`:
- **Traces**: una traza por ejecución, con cada nodo del grafo (Supervisor, Investigador, Analista...) y sus tokens.
- **Monitor**: latencia **p95** y **costo** por traza (LangSmith lo calcula con los tokens de entrada y salida).

## Decisiones de diseño (el "por qué")

- **Worker = `asyncio.create_task`** dentro del mismo proceso: simple y suficiente para esta etapa. Se guardan referencias
  a las tareas para que no las borre el recolector de basura. Para producción real: Arq o Celery en otro proceso.
- **Nada bloquea el event loop**: Redis con `redis.asyncio`, el grafo con `ainvoke`, el checkpointer async.
- **Dos usos de Redis**: hashes `trabajo:{job_id}` para el estado que consulta el cliente (con vencimiento de 24 h) y
  `AsyncRedisSaver` para los checkpoints del grafo (necesarios para pausar y reanudar el HITL).
- **El estado del grafo guarda dicts, no objetos Pydantic**: el checkpointer serializa a JSON; al leer se re-validan con
  Pydantic (`leer_oferta_investigada`). Sin esto, la reanudación después del HITL fallaba.
- **Límite de pedidos por minuto al LLM** (`PEDIDOS_POR_MINUTO_AL_LLM`): las 5 tareas comparten un limitador para no
  superar la cuota gratuita de Gemini; por eso la latencia de la prueba de carga incluye esperas.
- **LangSmith en lugar de Phoenix**: no requiere instalar nada (es un servicio web) y calcula costos solo.
