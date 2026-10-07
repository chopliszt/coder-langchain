# Guía de estudio · Semana 3: Embeddings, chunking y RAG local

Cinco ideas. Si entendés estas, entendés la entrega 3.

---

## 1. Embedding: convertir significado en coordenadas

**Qué es:** un modelo transforma un texto en una lista de números (un vector), por ejemplo 384 números.
Textos con **significado parecido** quedan **cerca** en ese espacio, aunque usen palabras distintas.

**Analogía:** un mapa de la ciudad. "Letra más grande" y "tipografía ampliada" viven en el mismo barrio;
"diabetes" vive en otro barrio. Buscar = "¿qué textos viven cerca de mi pregunta?".

**Regla de oro:** **el mismo modelo** para guardar y para buscar. Dos modelos distintos = dos mapas de
ciudades distintas: las coordenadas no se pueden comparar.

---

## 2. Similitud coseno: medir el ángulo, no la distancia

**Qué es:** compara hacia **dónde apuntan** dos vectores. 1 = misma dirección (mismo tema), 0 = nada que ver.

**Por qué importa:** un texto largo y uno corto sobre el mismo tema apuntan hacia el mismo lado,
aunque tengan "largos" distintos.

---

## 3. Chunking + overlap: cortar sin perder el hilo

**Qué es:** dividir documentos largos en fragmentos de ~500 **tokens**, repitiendo ~50 tokens entre
fragmentos vecinos.

**Por qué en tokens:** el LLM cuenta en tokens. "500 caracteres" puede ser 90 o 160 tokens.

**Por qué overlap:** si una idea queda justo en el corte, el solapamiento hace que aparezca entera en al menos un fragmento.

**Analogía (Bjorn):** si cortaras un audio de práctica de idiomas cada 30 segundos exactos, partirías
frases a la mitad. Mejor cortar en pausas (`RecursiveCharacterTextSplitter` corta en párrafos → líneas → espacios)
y repetir el último segundo.

---

## 4. Base vectorial persistente: la memoria de largo plazo

**Qué es:** ChromaDB guarda los vectores **en disco** (`./vectorstore`). La segunda vez no hay que recalcular nada.

**Tres buenas prácticas de la entrega:**
- **Chequear si ya existe** antes de indexar → ahorra tiempo y dinero.
- **`upsert`** (insertar o reemplazar) en vez de `add` (siempre insertar → duplicados).
- **IDs determinísticos** (`archivo::índice::hash`): el mismo fragmento siempre tiene el mismo ID.

**Analogía (asistente docente):** el legajo de cada estudiante. No lo reescribís cada mañana: lo
abrís, y si cambió algo, reemplazás esa hoja (upsert), no agregás una copia.

---

## 5. RAG con grounding: "si no está en el contexto, no lo sé"

**Qué es:** Retrieval-Augmented Generation = **buscar** fragmentos relevantes y después **generar** una
respuesta usando **solo** esos fragmentos.

```
pregunta → embedding → top 4 fragmentos → prompt con CONTEXTO → LLM → respuesta + fuentes
```

**Por qué top_k 3–5:** pocos = falta información; muchos = el modelo se pierde ("lost in the middle") y gastás tokens.

**Por qué "No lo sé":** un LLM sin reglas completa con lo que "suena bien" (alucinación). La pregunta
trampa ("¿qué nota sacó Tomás?") prueba que el sistema prefiere admitir que no sabe.

**Analogía (Sirius):** Sirius no debería decir "este mensaje es seguro" si no tiene evidencia.
Mejor "no estoy seguro" que una tranquilidad falsa.

**Para tu proyecto final (agente de CVs):** tu CV, proyectos y experiencias en una base vectorial →
cuando el agente responde una pregunta de una postulación, busca *tus* datos reales y no inventa experiencia.

---

## Mini-autoevaluación

1. ¿Qué pasa si indexás con un modelo de embeddings y consultás con otro?
2. ¿Por qué `upsert` + IDs por hash evita duplicados?
3. ¿Por qué las fuentes las arma el código y no el LLM?
4. ¿Qué devuelve el `retriever` y qué devuelve la cadena completa?
5. ¿Para qué sirve el overlap?
