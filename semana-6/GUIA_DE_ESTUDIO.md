# Guía de estudio · Semana 6: Sistemas multi-agente (Supervisor)

Cinco ideas. Si entendés estas, entendés la entrega 6.

---

## 1. Por qué varios agentes y no uno solo

Un agente con 15 herramientas y un prompt gigante se confunde. Varios agentes **especializados**, cada uno con
2 o 3 herramientas y un rol claro, se equivocan menos y se pueden probar por separado.

**Analogía (asistente docente):** en el colegio no hay una sola persona que haga todo: secretaría busca el legajo,
orientación lo analiza, dirección decide. Cada uno con su función.

---

## 2. Topología jerárquica: el Supervisor es un director de orquesta

- El **Supervisor** no toca ningún instrumento (no hace el trabajo): decide **quién toca ahora**.
- Los **especialistas** siempre vuelven al Supervisor al terminar.
- Su decisión es **estructurada** (`Literal["Investigador", "Analista", "FINALIZAR"]`): no puede inventar un nodo que no existe.

**Alternativa colaborativa:** los agentes se pasan el trabajo entre ellos sin jefe. Más flexible, más difícil de controlar.

---

## 3. Estado compartido sin pisarse

- **Una clave por agente** (`oferta_investigada`, `analisis_de_coincidencia`): cada uno escribe en su cajón.
- **Reducer `operator.add`** en `contribuciones`: las entradas se **suman**, no se reemplazan → historial de quién aportó qué.
- **Pydantic** valida lo que entra al estado: datos con forma garantizada.

**Analogía (Bjorn):** el agente de pronunciación y el de gramática escriben cada uno en su propia sección del
reporte del alumno; nadie borra lo del otro.

---

## 4. Validar con código, no con opiniones

El Validador **recalcula** el porcentaje y revisa que no falte ningún requisito. Un LLM puede "opinar" que está bien;
el código **verifica**. Si falla → **bucle de reparación**: se le devuelve al especialista **el error exacto** para que lo corrija.

**Analogía (Sirius):** el LLM dice "este link es seguro"; el código verifica el dominio contra una lista real.
Si no coincide, se vuelve a analizar.

---

## 5. Frenos: pasos máximos y contexto mínimo

- **Supervisor infinito:** sin un máximo de pasos, puede mandar a corregir para siempre. Acá: 6 pasos + `recursion_limit`.
  Si se agotan, se **escala a un humano** (esto es la base del *human-in-the-loop* de la semana 7).
- **Contaminación de contexto:** cada especialista recibe **solo lo que necesita**, no todo el historial.

**Para tu proyecto final (agente de CVs):** este orquestador **es** el corazón del proyecto: Investigador (lee la oferta) →
Analista (compara con tu CV) → un tercer especialista "Redactor" que escribe la carta o adapta el CV.

---

## Mini-autoevaluación

1. ¿Por qué el Supervisor devuelve un `Literal` y no texto libre?
2. ¿Qué pasaría si los dos agentes escribieran en la misma clave del estado?
3. ¿Qué verifica el Validador que el LLM no puede garantizar?
4. ¿Qué recibe el Analista como contexto y por qué no todo el historial?
5. ¿Qué pasa si se alcanzan los 6 pasos con errores pendientes?
