# Guía de estudio · Semana 2: LCEL, salida estructurada y resiliencia

Cinco ideas. Si entendés estas, entendés la entrega 2.

---

## 1. Runnable: el "enchufe universal"

**Qué es:** en LangChain, *todo* (prompt, modelo, parser, tu propia función) es un `Runnable`.
Todos tienen los mismos botones: `invoke`, `ainvoke`, `batch`, `stream`.

**Por qué importa:** como todos tienen el mismo enchufe, se pueden conectar entre sí sin pegamento.

**Analogía (Bjorn):** en tu tutor de idiomas, el audio de Telegram pasa por *transcribir → responder → convertir a voz*.
Si cada paso fuera un `Runnable`, podrías cambiar el transcriptor sin tocar los otros dos pasos.

---

## 2. LCEL y el operador `|`: una línea de montaje

**Qué es:** `prompt | modelo | parser`. La salida de cada paso es la entrada del siguiente.

```
dict {"texto": ...} → ChatPromptTemplate → mensajes → ChatOpenAI → AIMessage → parser → objeto limpio
```

**Por qué importa:** es *declarativo*: describís **qué** pasos hay, y LangChain se encarga del **cómo**
(async, streaming, reintentos, trazas).

**Analogía:** una cinta de fábrica. Cada estación hace una sola cosa y le pasa la pieza a la siguiente.

**Para probar:** en la entrega, `generar_diagrama.py` dibuja la cinta → `diagrama_pasos_de_la_cadena.png`.

---

## 3. Salida estructurada: un contrato, no una conversación

**Qué es:** `modelo.with_structured_output(MiModeloPydantic)` obliga al LLM a devolver
un objeto con campos y tipos fijos (usa *tool calling* por debajo).

**Por qué importa:** tu código no puede trabajar con "texto lindo". Necesita `criticidad == "alta"`, no
"es bastante grave, diría yo".

**Dos niveles de validación:**
- **De forma:** ¿están los campos? ¿tienen el tipo correcto? → lo resuelve `with_structured_output`.
- **De sentido:** ¿la lista de tecnologías no está vacía? → lo resuelve tu `@field_validator`.

**Analogía (Sirius):** en vez de que el LLM te diga "este mensaje parece raro…", te devuelve
`{es_estafa: true, tipo: "phishing", señales: ["link acortado", "urgencia"]}`. Con eso podés
*hacer algo* (bloquear, avisar, guardar estadística).

**Para tu proyecto final (agente de CVs):** cada oferta de trabajo scrapeada → un `OfertaDeTrabajo`
validado con `empresa`, `rol`, `requisitos: list[str]`, `idioma`. Es exactamente esta entrega.

---

## 4. Resiliencia: reintento, respaldo y `finish_reason`

**Dos tipos de error:**
| Tipo | Ejemplo | ¿Reintentar sirve? |
|---|---|---|
| Transitorio | rate limit 429, red caída, JSON cortado | **Sí** → `.with_retry()` con espera exponencial |
| Permanente | API key mala, prompt mal diseñado | **No** → fallar rápido y loguear |

- **`.with_retry()`**: probá de nuevo, esperando cada vez un poco más (1s, 2s, 4s…).
- **`.with_fallbacks([otra_cadena])`**: si el plan A falla todas las veces, usá el plan B (otro modelo).
- **`finish_reason == "length"`**: el modelo se quedó sin tokens y **cortó la respuesta a la mitad**.
  Si no lo chequeás, usás un objeto incompleto sin darte cuenta.

**Analogía (asistente docente):** mandás un mail a la secretaría y no responde. *Retry* = volver a mandar
mañana. *Fallback* = si después de 3 intentos nada, llamás a dirección. `finish_reason=length` =
te contestaron pero el mensaje se cortó a la mitad: no actúes sobre media respuesta.

**Para probar:** el escenario 4 de `main.py` fuerza un corte con 15 tokens y mirás en el log cómo
el sistema se da cuenta, reintenta y el modelo de respaldo rescata.

---

## 5. Async: no quedarse mirando la pava

**Qué es:** `await cadena.ainvoke(...)` libera al programa mientras espera al LLM.
`asyncio.gather(a, b)` lanza varias llamadas a la vez.

**Por qué importa:** una llamada a un LLM tarda segundos. Con 2 textos en paralelo tardás ~lo que tarda 1.

**Analogía:** ponés la pava y, mientras se calienta, preparás el mate. No te quedás mirando la pava.

**Error clásico:** olvidarse el `await` → recibís una *coroutine* en vez del resultado.

---

## Mini-autoevaluación

1. ¿Qué devuelve `prompt.invoke({"texto": "hola"})`? ¿Y `(prompt | modelo).invoke(...)`?
2. ¿Por qué `nivel_de_criticidad` es un `Enum` y no un `str`?
3. ¿Qué pasaría si el nombre de la variable en el prompt es `{texto}` pero llamás con `{"text": ...}`?
4. ¿Por qué *no* conviene reintentar un error de autenticación?
5. ¿Para qué sirve `include_raw=True`?
