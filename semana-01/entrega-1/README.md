# Unified Async LLM Client

Un cliente asíncrono unificado para OpenAI, Anthropic y Gemini. Cambiás de
proveedor cambiando un solo campo de configuración — el resto del código no
se entera de la diferencia.

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
