# Unified Async LLM Client

Un cliente asíncrono unificado para OpenAI, Anthropic y Gemini. Cambiás de
proveedor cambiando un solo campo de configuración — el resto del código no
se entera de la diferencia.

## Consigna (checklist oficial)

- [x] Intercambiabilidad: OpenAI y Anthropic (y Gemini como extra) bajo una interfaz común (`BaseLLMClient`)
- [x] Asincronía: todas las llamadas usan `AsyncOpenAI`, `AsyncAnthropic` y el cliente async de Gemini con `await`
- [x] Streaming: `generate_stream()` es un generador asíncrono que hace `yield` de cada fragmento
- [x] Validación con Pydantic: `ChatMessage`, `ModelResponse` y `LLMConfig` (temperatura de 0 a 2, `max_tokens` > 0)
- [x] `AsyncLLMManager` elige el proveedor según un campo de configuración
- [x] Errores de red, cuota y API key inválida devuelven un error controlado, sin crash
- [x] `main.py` pregunta "¿Qué es la entropía?" en modo normal y en streaming
- [x] `.env.example` y este README

## Estructura

- `schemas.py` — modelos Pydantic (`ChatMessage`, `LLMConfig`, `ModelResponse`)
- `clients.py` — `BaseLLMClient` (contrato) + `OpenAIClient`, `AnthropicClient`,
  `GeminiClient` + `AsyncLLMManager` (factory)
- `main.py` — script de prueba: modo normal, streaming y resiliencia ante errores

## Setup

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install openai anthropic google-genai pydantic python-dotenv
```

Copiá `.env.example` a `.env` y completá tus API keys:

```bash
cp .env.example .env
```

## Ejecutar

```bash
python main.py
```

Vas a ver: validación de Pydantic rechazando un config inválido, respuestas
normales de los tres proveedores, streaming token a token, y una prueba de
resiliencia con una API key rota (el programa no crashea).

## Variables de entorno

| Variable | Requerida para |
|---|---|
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic |
| `GOOGLE_API_KEY` | Gemini |
| `MODELO_OPENAI` / `MODELO_ANTHROPIC` / `MODELO_GEMINI` | Opcional. Por defecto: `gpt-4.1-mini`, `claude-opus-5-5`, `gemini-flash-lite-latest` |

Si falta la key de un proveedor, `main.py` lo saltea con un aviso y sigue con los demás.

> **Nota sobre Anthropic:** los modelos actuales de Claude (como `claude-opus-5-5`) ya no aceptan `temperature`
> y siempre razonan antes de responder, así que la respuesta puede traer un bloque de razonamiento antes del texto.
> Por eso `AnthropicClient` no envía `temperature` y junta solo los bloques de texto. Por la misma razón, `max_tokens` es 1024
> (el razonamiento también consume tokens).
