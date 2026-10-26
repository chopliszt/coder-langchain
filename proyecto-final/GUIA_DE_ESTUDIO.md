# Guía de estudio · Proyecto final: el Entrevistador de postulaciones

Para salir del "modo piloto automático". Primero **qué construimos** en 30 segundos, después **5 ideas**, después
**LangSmith explicado desde cero** y al final una autoevaluación.

---

## 0. Qué construimos, en 30 segundos

Un sistema que te **entrevista** sobre una pregunta de un formulario ("¿Por qué Pampa AI?"), te **repregunta** sobre lo
que dijiste y al final arma un borrador **solo con tus frases**.

**Analogía:** un programa de radio.

| En la radio | En el sistema | Archivo |
|---|---|---|
| El **productor** decide qué pasa ahora ("otra pregunta", "a la tanda") | **Supervisor** | `app/agentes/supervisor.py` |
| El **investigador** de producción lee sobre la empresa antes de la nota | **Investigador** (con RAG) | `app/agentes/investigador.py` |
| El **periodista** hace las preguntas | **Entrevistador** | `app/agentes/entrevistador.py` |
| El **invitado** habla (y el programa espera) | **EsperarRespuestaDelCandidato** (vos) | `app/agentes/candidato.py` |
| El **editor** corta la grabación y arma el audio final, sin agregar palabras | **Redactor** | `app/agentes/redactor.py` |
| El **control de calidad** escucha que no haya nada que el invitado no dijo | **Validador** (código, sin IA) | `app/agentes/validador.py` |

Todo eso vive detrás de una **API** (FastAPI): vos mandás tu respuesta por HTTP y la API te devuelve la siguiente pregunta.

---

## 1. El Supervisor solo decide: reglas de código primero, LLM después

El Supervisor **no hace trabajo**: solo elige quién sigue. Y la mayoría de las decisiones **no necesitan IA**:

| Situación | Quién decide | Por qué |
|---|---|---|
| ¿No hay contexto de esta pregunta? → Investigador | Código (`if`) | Es un hecho, no una opinión |
| ¿Ya hice 3 preguntas? → Redactor | Código | Un límite en el prompt se puede ignorar; un `if`, no |
| ¿El validador rechazó el borrador? → Redactor | Código | Es un hecho |
| ¿Tu respuesta es vaga o ya alcanza? | **LLM** | Esto **sí** es un juicio |

**Idea clave:** usá el LLM solo donde hace falta **juicio**. Es más barato, más rápido y falla menos.

**Analogía (Sirius):** para detectar estafas, "el link apunta a un dominio raro" lo chequea el código; "este mensaje
suena manipulador" lo juzga el LLM.

---

## 2. Estado compartido + aislamiento de nodos

El **estado** es el cuaderno de la entrevista: todos los nodos escriben ahí. Pero cada nodo recibe solo **las páginas
que necesita** (una "vista", `input_schema` en `app/grafo/construccion.py`).

```python
grafo.add_node("Redactor", armar_borrador_con_las_frases_del_candidato, input_schema=VistaDelRedactor)
```

| Nodo | Ve tu perfil | Por qué |
|---|---|---|
| Entrevistador | **Sí** (lo lee del disco) | Para hacer preguntas más inteligentes ("tu perfil dice X, ¿cómo...?") |
| Redactor | **No** | Si no lo ve, **no puede** copiarlo. Tu borrador sale solo de tus respuestas |

**Dos ideas más del estado:**
- **Registros que solo crecen** (`operator.add`): la transcripción nunca se borra, solo se le agregan turnos. Cada turno lleva su `numero_de_pregunta`. Así no hay que "limpiar" nada al pasar a la siguiente pregunta.
- **Cada nodo escribe solo su clave:** el Redactor escribe `borradores_propuestos` y nada más. Si algo sale mal, sabés exactamente quién lo escribió.

**Analogía:** un examen. El entrevistador tiene apuntes; el redactor solo tiene tu hoja de respuestas.

---

## 3. `interrupt()` + checkpointer: pausar y reanudar (aunque se apague todo)

Una entrevista es un ida y vuelta con un **humano** que tarda lo que quiera. El grafo no puede quedarse "esperando"
en memoria. Entonces:

1. El nodo `EsperarRespuestaDelCandidato` llama a `interrupt({...pregunta...})` → el grafo **se congela**.
2. El **checkpointer** (`AsyncRedisSaver`) guarda una foto de todo el estado en **Redis**, bajo un `thread_id`.
3. La API te devuelve la pregunta.
4. Mañana mandás tu respuesta → `Command(resume=tu_texto)` → el grafo **se descongela** justo donde estaba.

Como la foto vive en Redis y no en la memoria de Python, **podés reiniciar el servidor** y la entrevista sigue.

**Analogía (Bjorn):** mandás una nota de voz, cerrás Telegram, volvés a la noche y el tutor se acuerda de todo.
Eso es un checkpointer con un `thread_id` por alumno.

---

## 4. No confiar en el LLM: el Validador es código

La regla más importante del producto ("el borrador tiene solo tus frases") **no se le pide al LLM: se verifica**.

```
Redactor (LLM) propone fragmentos ──► Validador (código) busca cada fragmento, literal, en tus respuestas
                                        ├─ todos están → aprobado
                                        └─ alguno inventado → vuelve al Redactor con el error (máx. 2 intentos),
                                           y si sigue mal, se descarta ese fragmento
```

Esto cubre el punto de la rúbrica "los agentes **corrigen sus errores**": el error vuelve como dato y el Redactor
lo arregla.

**Idea clave:** "pedírselo amablemente en el prompt" ≠ "garantizarlo". Lo que importa de verdad se verifica con código.

---

## 5. RAG como herramienta del Investigador (con metadatos)

En la semana 3 el RAG era una cadena fija: pregunta → buscar → responder. Acá es una **tool** que un **agente** decide
cuándo y cómo usar (`buscar_contexto_del_puesto_en_los_documentos`).

- **Chroma local** guarda fragmentos de la oferta y de los valores de cada empresa.
- Cada fragmento tiene **metadatos**: `empresa`, `tipo_de_documento`, `fuente`.
- La búsqueda filtra por `empresa`, para no mezclar Pampa AI con Nimbus Edu (eso prueba el test 3).
- La entrada de la tool está validada con **Pydantic** (`ConsultaALosDocumentosDelPuesto`): si el LLM inventa una empresa, recibe un error claro y reintenta.

**Analogía (asistente docente):** no le das al asistente el reglamento entero en cada pregunta; le das un buscador
y él decide qué buscar.

---

## 6. LangSmith, desde cero

### ¿Qué es?

Una **caja negra de avión** para tu app de IA. Cada vez que el sistema corre, LangSmith graba **todo lo que pasó adentro**:
qué agente corrió, qué le mandó al LLM, qué le contestó, cuánto tardó y cuánto costó.

**¿Cómo llegan los datos ahí?** Solo por 3 variables del `.env` (`LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`,
`LANGSMITH_PROJECT`). LangChain y LangGraph ya traen "micrófonos" (*callbacks*) adentro: si ven esas variables, mandan
todo solos. **No escribimos ni una línea de código de trazas.** Lo único que agregamos fue el `thread_id` como
metadato y el nombre `entrevista`, en `app/api/principal.py`.

### El vocabulario (lo que viste en las pantallas)

| Palabra | Qué es | En nuestro sistema |
|---|---|---|
| **Project / Agent** | La carpeta donde caen todas las trazas de una app | `orquestador-postulaciones` |
| **Trace** (traza) | **Una** ejecución completa, de punta a punta | Un pedido a la API (`entrevista`): las 5 pruebas generaron 23 |
| **Run / Span** | Un **paso** dentro de la traza. Se anidan como un árbol | Supervisor, Investigador, ChatGoogle..., `buscar_contexto...` |
| **Thread** (hilo) | Varias trazas de **la misma conversación** juntas | Una entrevista entera, agrupada por `thread_id` |
| **Turn** (turno) | Cada traza dentro de un thread | Cada vez que mandaste una respuesta |
| **Tokens** | Pedacitos de texto que el LLM lee y escribe; se cobran | 26.1K tokens en total |
| **Cost** | Tokens × precio del modelo | USD 0,015 las 5 pruebas |
| **Latency P50** | La **mitad** de los pedidos tardó menos que esto | 9,9 s |
| **Latency P99** | El 99 % tardó menos que esto: mide **los peores casos** | 19,2 s |
| **Error rate** | % de trazas que fallaron | 0 % |

### Leyendo tu captura 4 (el árbol), línea por línea

```
entrevista 15.08s · 2.05K tokens · $0.0011      ← la traza: tu POST /entrevistas
├─ Supervisor 0.00s                             ← decidió por regla de código (0 s = no llamó al LLM)
├─ Investigador 10.16s                          ← un agente ReAct adentro de nuestro grafo
│   ├─ model 4.93s → ChatGoogle (428 tokens)     ← el LLM decide: "voy a buscar en los documentos"
│   ├─ tools 0.04s → buscar_contexto_d...        ← el RAG: Chroma respondió en 40 milisegundos
│   └─ model 5.17s → ChatGoogle (1.023K tokens)  ← el LLM lee los fragmentos y arma el contexto
├─ Supervisor 0.00s                             ← regla de código: "ahora el Entrevistador"
└─ Entrevistador ...                            ← formula tu primera pregunta
```

**Lo que te enseña ese árbol, sin leer código:**
- El cuello de botella es **el LLM** (5 s por llamada), no el RAG (0,04 s). Si quisieras ir más rápido, ahí atacás.
- El Supervisor casi nunca gasta: las reglas de código hacen su trabajo.
- El Investigador es **un agente adentro de otro**: tiene su propio mini-ciclo (`model` → `tools` → `model`). Eso es el patrón ReAct de la semana 5, metido como un nodo en el grafo de la semana 6.

Las pestañas de la derecha: **Input** (qué recibió ese paso; ahí viste el estado inicial con las listas vacías),
**Output** (qué devolvió), **Attributes** (metadatos, como el `thread_id`), **Feedback** (notas que le pone un humano
o un evaluador: "esta pregunta estuvo buena / mala").

### ¿En qué se diferencia de otras cosas?

| Herramienta | Qué ve | Diferencia con LangSmith |
|---|---|---|
| `print` / `logging` | Líneas de texto sueltas | No ves el **árbol**, ni tokens, ni costo, ni qué prompt exacto se mandó. Sirve para vos en la terminal |
| **Arize Phoenix** | Lo mismo que LangSmith | Es la alternativa **open source** que podés correr en tu compu. La consigna aceptaba cualquiera de las dos |
| Datadog / Grafana | Servidores: CPU, memoria, errores HTTP | No entienden qué es un prompt o un token. Miden la "máquina", no el "razonamiento" |
| LangGraph Studio | El grafo **mientras lo diseñás** | Es para depurar en desarrollo; LangSmith es para **mirar lo que ya pasó** |

**En una frase:** los logs te dicen *que* algo pasó; LangSmith te muestra *por qué* el agente hizo lo que hizo.

### ¿Y Langfuse? La alternativa open source

**Langfuse** hace lo mismo que LangSmith (trazas, árbol de pasos, tokens, costo, datasets, evaluadores, prompts), pero es
**open source**: lo podés usar en su nube o **instalarlo en tu propio servidor** con Docker.

| | LangSmith | Langfuse | Arize Phoenix |
|---|---|---|---|
| Quién lo hace | LangChain (los mismos de LangGraph) | Empresa independiente | Arize |
| Código abierto | No | **Sí** | **Sí** |
| ¿Lo podés instalar en tu servidor? | Solo en el plan empresa | **Sí, gratis** | **Sí** (corre hasta en tu compu) |
| Cómo se conecta a LangChain/LangGraph | **Solo con variables de entorno** | Un `CallbackHandler` que pasás en la config | OpenTelemetry + un instrumentador |
| Cuándo elegirlo | Ya usás LangChain y querés cero configuración | Datos sensibles que no pueden salir de tu servidor, o no querés depender de LangChain | Querés todo local y estándar (OpenTelemetry) |

**Cómo lo habríamos usado acá** (no está en el código, es para entender la diferencia):

```python
from langfuse.langchain import CallbackHandler

manejador_de_trazas_de_langfuse: CallbackHandler = CallbackHandler()

def crear_configuracion_de_la_ejecucion(identificador_de_la_entrevista: str) -> RunnableConfig:
    return {
        "configurable": {"thread_id": identificador_de_la_entrevista},
        "callbacks": [manejador_de_trazas_de_langfuse],
        ...
    }
```

Más las keys de Langfuse en el `.env` (una pública, una secreta y la dirección del servidor). La diferencia de fondo:
LangSmith se "enchufa solo" porque LangChain lo trae de fábrica. Langfuse lo **enchufás vos** pasando un *callback*,
que es como colgarle un micrófono a cada paso del grafo.

**Analogía (asistente docente con datos de alumnos):** con datos reales de menores, Langfuse instalado en un servidor del
colegio te deja tener trazas **sin que los datos salgan del colegio**. Con LangSmith en la nube, los prompts (y lo que
tengan adentro) viajan a sus servidores.

### El resto del menú: qué es y si te importa

| Sección | Qué es | ¿Ahora? |
|---|---|---|
| **Tracing** | Lo que usamos: trazas, árboles, threads | ✅ Sí |
| **Monitoring / Dashboards** | Gráficos de latencia, costo y errores en el tiempo | ✅ Lo que viste en la captura 2 |
| **Datasets & Experiments** | Guardás preguntas de prueba (un golden set) y comparás versiones de tu sistema | ⭐ Siguiente paso natural: es la semana 4 (Recall@k), pero para agentes |
| **Evaluators / Online Evaluators** | Un LLM o código que **califica** cada traza solo ("¿el entrevistador sugirió contenido?") | ⭐ Ideal para tu regla "nunca sugiere contenido" |
| **Annotation Queues** | Una cola para que un humano revise trazas y les ponga nota | Más adelante |
| **Prompts / Playground** | Guardar versiones de prompts y probarlos sin tocar código | Útil, opcional |
| **Deployments, Engine, LLM Gateway, Sandboxes** | Hosting y servicios pagos ("Plus") | ❌ No para este curso |

---

## 7. El recorrido completo de un pedido (para explicarlo en una entrevista de trabajo)

1. `POST /entrevistas` → **Pydantic** valida la empresa y las preguntas (`app/api/esquemas.py`).
2. La API crea un `thread_id` y corre el grafo con `ainvoke` (**async**).
3. **Supervisor** → no hay contexto → **Investigador** busca en **Chroma** (RAG como tool) → **Supervisor** → **Entrevistador** pregunta.
4. **EsperarRespuestaDelCandidato** llama a `interrupt()` → el **checkpointer** guarda todo en **Redis** → la API te devuelve la pregunta.
5. Respondés → `Command(resume=...)` → **Supervisor** (LLM: "¿alcanza?") → repregunta o **Redactor** → **Validador**.
6. Cada paso queda en **LangSmith** como un árbol, agrupado por `thread_id`.

Si podés contar estos 6 pasos con tus palabras, entendiste el proyecto.

---

## Autoevaluación

1. ¿Por qué el Supervisor decide "¿no hay contexto? → Investigador" con un `if` y no con el LLM?
2. ¿Qué pasaría si el Redactor recibiera tu perfil? ¿Qué dos "candados" lo impiden?
3. ¿Qué guarda exactamente el checkpointer y por qué sobrevive a un reinicio del servidor?
4. ¿Cuál es la diferencia entre una **traza**, un **run** y un **thread** en LangSmith?
5. En tu captura, el Investigador tardó 10 s. ¿Cuánto fue el RAG y cuánto el LLM? ¿Qué optimizarías primero?
6. ¿Por qué P99 te importa más que el promedio cuando hay usuarios reales?
7. ¿Qué agregarías con **Datasets & Experiments** para medir si el Entrevistador "nunca sugiere contenido"?

<details>
<summary>Respuestas cortas</summary>

1. Es un hecho, no un juicio: el código es gratis, instantáneo y no se equivoca.
2. Podría copiar datos de tu perfil que no dijiste. Candado 1: el aislamiento (no lo recibe). Candado 2: el Validador (descarta lo que no está literal en tus respuestas).
3. Una foto del estado completo por `thread_id` en cada paso. Vive en Redis, no en la memoria de Python.
4. Traza = una ejecución completa. Run = un paso adentro de la traza. Thread = varias trazas de la misma conversación.
5. RAG 0,04 s; LLM ~10 s. Primero el LLM: modelo más rápido, menos llamadas o prompts más cortos.
6. Porque el promedio esconde a los usuarios que esperaron 20 s; esos son los que se van.
7. Un dataset de conversaciones de prueba + un evaluador (LLM o código) que marque si la pregunta propone una experiencia que el candidato no mencionó.

</details>
