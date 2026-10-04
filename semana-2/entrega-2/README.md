# Pre-entrega 2 · Pipeline de extracción de entidades técnicas

Texto crudo (un log de error o una descripción de arquitectura) → **objeto Pydantic validado** con
`tecnologias`, `nivel_de_criticidad` y `resumen_tecnico`.

Construido con **LangChain LCEL** + **Pydantic** + **async**, con reintentos, modelo de respaldo
y detección de respuestas truncadas (`finish_reason`).

## Cómo fluye un texto

![Pasos de la cadena](diagrama_pasos_de_la_cadena.png)

![Reintentos y respaldo](diagrama_reintentos_y_respaldo.png)

## Estructura

| Archivo | Qué contiene |
|---|---|
| `schemas.py` | `NivelDeCriticidad` (Enum baja/media/alta) y `EntidadesTecnicas` (modelo Pydantic con validador: la lista de tecnologías no puede quedar vacía, se limpian espacios y duplicados) |
| `chain.py` | `ChatPromptTemplate` (roles system + human, variables `{texto}` e `{instrucciones_de_formato}`), modelo `ChatOpenAI` con `temperature=0`, cadena LCEL `prompt \| modelo.with_structured_output(EntidadesTecnicas)`, `.with_retry()`, `.with_fallbacks()` y la función async `extraer_entidades_tecnicas_desde_texto()` |
| `main.py` | Script de prueba async (4 escenarios, ver abajo). Guarda los logs en `evidencia_de_ejecucion.log` |
| `generar_diagrama.py` | Genera los dos diagramas PNG con `get_graph().draw_mermaid_png()` |

> La consigna llama a la función `process_text`. Acá se llama `extraer_entidades_tecnicas_desde_texto`
> (nombre descriptivo en español: dice qué entra y qué sale). Hace exactamente lo mismo: `await cadena.ainvoke(...)`.

## Setup

Desde la raíz del repo (usa `uv`):

```bash
uv sync
cp semana-2/entrega-2/.env.example .env   # y completá OPENAI_API_KEY
```

O con pip: `pip install -r requirements.txt`.

| Variable | Para qué |
|---|---|
| `OPENAI_API_KEY` | Clave de OpenAI (nunca se commitea) |
| `MODELO_PRINCIPAL_OPENAI` | Modelo principal (default `gpt-4.1-mini`) |
| `MODELO_DE_RESPALDO_OPENAI` | Modelo de respaldo para `.with_fallbacks()` (default `gpt-4o-mini`) |

## Ejecutar

```bash
uv run python semana-2/entrega-2/main.py
uv run python semana-2/entrega-2/generar_diagrama.py   # opcional, regenera los PNG
```

## Escenarios de la prueba

1. **Validador Pydantic** sin llamar al modelo: una lista de tecnologías vacía es rechazada; los duplicados se limpian.
2. **Dos textos limpios en paralelo** con `asyncio.gather` (un log de producción y la arquitectura de un detector de estafas).
3. **Prueba de estrés**: un texto ambiguo sin tecnologías claras. O el modelo se recupera, o el validador rechaza y se reintenta; el programa nunca crashea.
4. **Respuesta truncada**: el modelo principal tiene solo 15 tokens → `finish_reason=length` → se detecta, se reintenta 3 veces y el **modelo de respaldo** rescata la respuesta.

## Decisiones de diseño (el "por qué")

- **`with_structured_output(..., include_raw=True)`**: además del objeto parseado, devuelve el mensaje crudo. Así se puede leer `finish_reason` y detectar respuestas cortadas *antes* de usar el objeto.
- **El paso `verificar_que_la_respuesta_este_completa_y_validada` lanza una excepción** si la respuesta está truncada o no cumple el esquema. Esa excepción es la que dispara `.with_retry()`.
- **Solo se reintentan errores que pueden arreglarse reintentando** (truncado, mal formado, rate limit, conexión, timeout). Un error de autenticación no se reintenta: reintentarlo 3 veces no lo arregla.
- **`max_retries=0` en `ChatOpenAI`**: el SDK de OpenAI reintenta en silencio por su cuenta. Lo apagamos para que los reintentos los maneje la cadena y queden en los logs.
- **`temperature=0`**: para extraer datos queremos respuestas estables, no creatividad.
- **`timeout=30`**: ninguna llamada puede quedar colgada para siempre.
- **Sin f-strings en la cadena**: el prompt es un `ChatPromptTemplate`; las instrucciones de formato entran como variable con `.partial()`.

## Evidencia de ejecución

Ver [`evidencia_de_ejecucion.log`](evidencia_de_ejecucion.log).
