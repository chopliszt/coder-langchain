# Guía de estudio · Semana 5: Agentes con LangGraph (ReAct + memoria)

Cinco ideas. Si entendés estas, entendés la entrega 5.

---

## 1. Cadena vs. agente: receta fija vs. cocinero

- **Cadena (semanas 2–4):** pasos fijos, siempre en el mismo orden. Una receta.
- **Agente:** el LLM **decide** qué hacer en cada momento. Un cocinero que mira la heladera y decide.

**Analogía (asistente docente):** una cadena es "leer mail → clasificar → responder". Un agente es "leer mail → *¿necesito
mirar el calendario? ¿el legajo del alumno? ¿las dos cosas?* → responder".

---

## 2. Grafo = nodos + aristas + estado

- **Nodo:** una función que hace algo (llamar al modelo, ejecutar una herramienta).
- **Arista:** por dónde sigue el flujo. Una **arista condicional** elige el camino según el estado.
- **Estado:** la "mochila" que viaja por el grafo. Acá: la lista de mensajes.

```
START → modelo → ¿pidió una herramienta?  sí → herramientas → modelo (vuelve)
                                          no → END
```

**Para verlo:** `diagrama_del_grafo.png` en la entrega (generado con `get_graph().draw_mermaid_png()`).

---

## 3. ReAct: razonar → actuar → observar → repetir

1. **Razonar:** "no tengo el ID de Pampa AI".
2. **Actuar:** llamar a `buscar_empresa_por_nombre`.
3. **Observar:** "empresa_id=101".
4. **Repetir** hasta tener todo → responder.

**El docstring es la interfaz:** el LLM elige herramientas **solo** leyendo su descripción. Docstring vago = herramienta mal usada.

**Analogía (Bjorn):** un tutor que no sabe tu nivel primero consulta tu historial (actúa), ve que sos A2 (observa) y recién
ahí elige el ejercicio (razona → responde).

---

## 4. Reducers: el estado se **acumula**, no se pisa

`MessagesState` usa el reducer `add_messages`: cada nodo devuelve mensajes **nuevos** y LangGraph los **agrega** a la lista.
Sin reducer, cada nodo borraría la conversación anterior.

**Riesgo: "estado sucio".** La lista crece para siempre → más tokens, más costo. Solución: recortar (`trim_messages`) o resumir lo que se le envía al modelo.

---

## 5. Checkpointer + thread_id = memoria

- **Checkpointer** (`SqliteSaver`): guarda una "foto" del estado después de cada paso en un archivo.
- **thread_id:** el número de conversación. Mismo `thread_id` = el agente recupera la foto y "se acuerda".
- **recursion_limit:** techo de pasos. Sin él, un agente confundido puede dar vueltas y gastar plata.

**Analogía (Sirius / Telegram):** cada chat de Telegram tiene su `chat_id`. Usarlo como `thread_id` hace que el bot
recuerde lo que hablaste con él, sin mezclarlo con otros usuarios.

**Para tu proyecto final (agente de CVs):** un `thread_id` por postulación. Así el agente recuerda qué ya respondiste para
esa empresa cuando volvés al día siguiente.

---

## Mini-autoevaluación

1. ¿Qué hace `tools_condition`?
2. ¿Por qué la herramienta devuelve `"ERROR: ..."` en vez de lanzar una excepción?
3. ¿Qué pasaría sin el reducer `add_messages`?
4. ¿Qué diferencia hay entre el estado guardado y lo que se le envía al modelo?
5. ¿Para qué sirve `recursion_limit`?
