# Guía de estudio · Semana 7: Del notebook a producción

Cinco ideas. Si entendés estas, entendés la entrega 7.

---

## 1. API asíncrona: "tomamos tu pedido, te avisamos"

Un agente tarda minutos. Si la API esperara a que termine, el cliente se quedaría colgado y el servidor no podría
atender a nadie más. Solución: `POST /tasks` **encola** y devuelve un `job_id` al instante; el cliente pregunta con
`GET /tasks/{id}` (*polling*).

**Analogía:** el ticket de la panadería. No esperás parado frente al horno: te dan un número y vas mirando la pantalla.

---

## 2. Redis: la pizarra compartida

Redis es una base de datos en memoria, muy rápida. Acá guarda dos cosas:
- **El estado del trabajo** (PENDING, RUNNING, DONE, FAILED) para que el cliente lo consulte.
- **Los checkpoints del grafo**, para poder **pausar** y **reanudar** (aunque se reinicie la API).

**Error clásico:** si el worker falla y no escribe `FAILED`, el cliente pregunta para siempre. Por eso todo el worker
está dentro de un `try/except` que guarda el error.

---

## 3. Human-in-the-loop: el botón de "¿estás seguro?"

Algunas acciones no se pueden deshacer (mandar un mail, pagar, **enviar una postulación**). `interrupt()` congela el grafo
y guarda todo en Redis; `Command(resume=...)` lo descongela con la decisión del humano.

**Analogía (asistente docente):** el agente puede **redactar** el mail a las familias, pero **vos** apretás "enviar".

**Para tu proyecto final (agente de CVs):** el agente adapta el CV y la carta, pero nunca envía nada sin tu OK.

---

## 4. Observabilidad: ver adentro de la caja negra

Una **traza** es la radiografía de una ejecución: qué nodo corrió, cuánto tardó, cuántos tokens usó, cuánto costó.
**LangSmith** la arma sola con 3 variables de entorno.

**Dos métricas clave:**
- **Latencia p95:** el 95% de las ejecuciones tarda menos que esto. Importa más que el promedio, porque mide la experiencia de los usuarios con peor suerte.
- **Costo por ejecución:** tokens de entrada × precio + tokens de salida × precio.

**Analogía (Bjorn):** si un alumno se queja de que el bot "tarda", la traza muestra si fue la transcripción, el LLM o la voz.

---

## 5. No bloquear el event loop

Todo lo que espera (red, base de datos, LLM) se hace con `await` y librerías async (`redis.asyncio`, `ainvoke`). Una sola
llamada síncrona dentro de un endpoint frena **toda** la API para **todos** los usuarios.

**Analogía:** un mozo que se queda parado en la cocina esperando un plato deja a todas las mesas sin atender.

---

## Mini-autoevaluación

1. ¿Por qué `POST /tasks` devuelve 202 y no el resultado?
2. ¿Qué pasaría si el worker falla y no escribe `FAILED` en Redis?
3. ¿Qué guarda Redis para que el HITL pueda reanudar?
4. ¿Qué diferencia hay entre latencia promedio y p95?
5. ¿Por qué enviar la postulación es "crítico" y analizarla no?
