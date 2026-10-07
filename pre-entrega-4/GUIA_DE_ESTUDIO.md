# Guía de estudio · Semana 4: RAG en la nube, búsqueda híbrida y métricas

Cinco ideas. Si entendés estas, entendés la entrega 4.

---

## 1. Base vectorial en la nube (Pinecone Serverless)

**Qué es:** lo mismo que ChromaDB de la semana 3, pero en un servidor de Pinecone. "Serverless" = no administrás
máquinas: pagás (o usás gratis) por lo que guardás y consultás.

**Por qué importa:** ChromaDB vive en tu notebook. Si tu bot del colegio lo usan 200 docentes desde sus celulares,
necesitás que la base viva en la nube.

**La regla que más rompe cosas:** la **dimensión** del índice tiene que ser igual a la del modelo de embeddings
(384 acá; 1536 en OpenAI). Es como un enchufe: si tiene 3 patas, no entra en uno de 2.

---

## 2. Namespaces y metadatos: cajones y etiquetas

- **Namespace** = un **cajón** separado dentro del mismo índice. Lo que está en un cajón no aparece al buscar en otro.
- **Metadatos** = **etiquetas** en cada ficha (fuente, página, categoría). Permiten filtrar *dentro* de un cajón.

**Analogía (asistente docente):** un cajón por colegio o por programa (IB, nacional). Dentro del cajón IB, filtrás por
etiqueta "TOK" si la pregunta es de TOK.

**Esquema estricto:** si una ficha dice `fuente` y otra `source`, el filtro falla en silencio. Por eso validamos la
metadata con Pydantic antes de subir (*schema drift* = las claves se van desordenando con el tiempo).

---

## 3. Búsqueda híbrida: palabras exactas + significado

| BM25 (léxica) | Vectorial (semántica) |
|---|---|
| Busca **las mismas palabras** | Busca **el mismo significado** |
| Genial con siglas y nombres: "RPPF", "TOK", "Tomás Ferreyra" | Genial con paráfrasis: "¿cuánto puedo escribir?" ≈ "máximo de palabras" |
| No entiende sinónimos | Se confunde con siglas raras |

**Híbrido = lo mejor de los dos.** El `EnsembleRetriever` los combina.

**Analogía (Bjorn):** si un alumno dice la palabra exacta en alemán, BM25 la encuentra. Si la dice con otras
palabras, el vectorial entiende la intención.

---

## 4. RRF: combinar por posición, no por puntaje

BM25 da puntajes tipo 7.3; la similitud coseno da 0.82. **No se pueden sumar** (distintas escalas, como sumar
grados Celsius con kilómetros).

**Reciprocal Rank Fusion** mira **en qué puesto** quedó cada resultado en cada lista: salir 1° en las dos listas vale
mucho; salir 1° en una y no aparecer en la otra, menos.

**Analogía:** dos jurados con escalas distintas (uno puntúa de 1 a 10, otro de 1 a 100). En vez de sumar puntajes,
mirás el ranking de cada jurado.

---

## 5. Medir antes de opinar: Recall@5 y Precision@5

- **Golden set** = examen con respuestas conocidas: preguntas + "el documento correcto es X".
- **Recall@5** = ¿encontró el documento correcto entre los 5? → **¿se le escapó algo?**
- **Precision@5** = de los 5 que trajo, ¿cuántos sirven? → **¿cuánta basura trajo?**

**Analogía (Sirius):** recall = de todas las estafas reales, ¿cuántas detectó? Precision = de todo lo que marcó como
estafa, ¿cuánto era realmente estafa?

**Para tu proyecto final (agente de CVs):** armá un golden set con 10 preguntas típicas de postulaciones y el
fragmento de tu CV que debería responderlas. Así sabés si el agente encuentra *tu* experiencia correcta.

---

## Mini-autoevaluación

1. ¿Qué pasa si subís vectores de 1536 dimensiones a un índice de 384?
2. ¿Cuándo usarías un namespace y cuándo un filtro de metadata?
3. ¿Por qué no se pueden sumar los puntajes de BM25 y del vectorial?
4. En este dataset la Precision@5 máxima es 40%. ¿Por qué?
5. ¿Qué pregunta del golden set debería ganar BM25? ¿Cuál el vectorial?
