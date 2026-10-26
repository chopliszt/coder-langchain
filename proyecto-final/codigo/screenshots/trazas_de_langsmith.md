# Trazas de LangSmith de las 5 pruebas (exportadas con el SDK)

Proyecto de LangSmith: `orquestador-postulaciones` · 23 ejecuciones raíz `entrevista` (cada pedido a la API es una ejecución; una entrevista tiene varias).

| Hora (UTC) | thread_id de la entrevista | Estado | Latencia (s) | Tokens totales | Costo (USD) |
|---|---|---|---|---|---|
| 23:14:36 | `5c0c1085` | success | 19.1 | 2018 | 0.0010542 |
| 23:14:55 | `5c0c1085` | success | 9.0 | 858 | 0.0004598 |
| 23:15:04 | `5c0c1085` | success | 10.1 | 1009 | 0.0005117 |
| 23:15:14 | `5c0c1085` | success | 5.2 | 294 | 0.0002752 |
| 23:15:29 | `a7c62bdb` | success | 6.1 | 2141 | 0.0012517 |
| 23:15:35 | `a7c62bdb` | success | 10.7 | 507 | 0.0004271 |
| 23:15:46 | `e3cdf6b7` | success | 14.6 | 2026 | 0.0010566 |
| 23:16:00 | `e3cdf6b7` | success | 9.7 | 840 | 0.000428 |
| 23:16:10 | `e3cdf6b7` | success | 10.1 | 973 | 0.0004877 |
| 23:16:20 | `e3cdf6b7` | success | 5.2 | 294 | 0.0002752 |
| 23:16:25 | `dcfdf52c` | success | 15.9 | 2050 | 0.0010924 |
| 23:16:41 | `dcfdf52c` | success | 9.2 | 430 | 0.0003622 |
| 23:16:50 | `17d2d186` | success | 15.2 | 2043 | 0.0010573 |
| 23:17:06 | `17d2d186` | success | 10.2 | 884 | 0.0004544 |
| 23:17:16 | `17d2d186` | success | 9.6 | 1054 | 0.0005406 |
| 23:17:26 | `17d2d186` | success | 5.3 | 325 | 0.0003329 |
| 23:17:31 | `604b049b` | success | 15.1 | 2050 | 0.001088 |
| 23:17:46 | `604b049b` | success | 10.0 | 860 | 0.0004516 |
| 23:17:56 | `604b049b` | success | 10.0 | 1011 | 0.0005343 |
| 23:18:06 | `604b049b` | success | 20.4 | 2270 | 0.0012354 |
| 23:18:26 | `604b049b` | success | 9.9 | 858 | 0.0004862 |
| 23:18:36 | `604b049b` | success | 10.2 | 999 | 0.0005263 |
| 23:18:47 | `604b049b` | success | 5.1 | 292 | 0.0002856 |

## Árbol de spans de una ejecución (la más larga, 20.4 s)

```
└─ entrevista [chain] 20.45s · 2270 tokens
  └─ EsperarRespuestaDelCandidato [chain] 0.00s
  └─ Supervisor [chain] 0.00s
    └─ elegir_ruta_despues_del_supervisor [chain] 0.00s
  └─ Redactor [chain] 5.36s · 276 tokens
    └─ RunnableWithFallbacks [chain] 5.35s · 276 tokens
      └─ RunnableSequence [chain] 5.35s · 276 tokens
        └─ ChatPromptTemplate [prompt] 0.00s
        └─ ChatGoogleGenerativeAI [llm] 5.35s · 276 tokens
        └─ PydanticOutputParser [parser] 0.00s
  └─ Validador [chain] 0.00s
  └─ Supervisor [chain] 0.00s
    └─ elegir_ruta_despues_del_supervisor [chain] 0.00s
  └─ Investigador [chain] 10.09s · 1425 tokens
    └─ LangGraph [chain] 10.09s · 1425 tokens
      └─ model [chain] 5.14s · 435 tokens
        └─ ChatGoogleGenerativeAI [llm] 5.14s · 435 tokens
      └─ tools [chain] 0.04s
        └─ buscar_contexto_del_puesto_en_los_documentos [tool] 0.04s
      └─ model [chain] 4.90s · 990 tokens
        └─ ChatGoogleGenerativeAI [llm] 4.90s · 990 tokens
  └─ Supervisor [chain] 0.00s
    └─ elegir_ruta_despues_del_supervisor [chain] 0.00s
  └─ Entrevistador [chain] 4.97s · 569 tokens
    └─ RunnableWithFallbacks [chain] 4.97s · 569 tokens
      └─ RunnableSequence [chain] 4.97s · 569 tokens
        └─ ChatPromptTemplate [prompt] 0.00s
        └─ ChatGoogleGenerativeAI [llm] 4.96s · 569 tokens
        └─ PydanticOutputParser [parser] 0.00s
  └─ EsperarRespuestaDelCandidato [chain] 0.00s
```
