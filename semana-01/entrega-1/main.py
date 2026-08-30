"""Entry point. Run this file directly: `python main.py`

This is the ONLY file that should ever call asyncio.run(). schemas.py and
clients.py just define reusable stuff — they don't DO anything on their own.
"""

import asyncio
import os

from dotenv import load_dotenv
from pydantic import SecretStr, ValidationError

from clients import AsyncLLMManager
from schemas import ChatMessage, LLMConfig, Provider

load_dotenv()  # reads .env into os.environ, so getpass() prompts become a relic of the past


async def demo_validacion() -> None:
    """Muestra que Pydantic frena datos inválidos ANTES de gastar una sola llamada a la API."""
    print("--- Validación con Pydantic ---")
    try:
        LLMConfig(provider=Provider.OPENAI, model="gpt-4o-mini", temperature=5)
    except ValidationError as e:
        print("❌ Se detectó ANTES de llamar a la API:\n", e)


async def demo_generate(manager: AsyncLLMManager, pregunta: list[ChatMessage], nombre: str, emoji: str) -> None:
    resultado = await manager.generate(pregunta)
    contenido = resultado.content if not resultado.error else f"❌ {resultado.error}"
    print(f"{emoji} {nombre}:", contenido)


async def demo_stream(manager: AsyncLLMManager, pregunta: list[ChatMessage], nombre: str, emoji: str) -> None:
    print(f"\n{emoji} Streaming {nombre}:")
    async for chunk in manager.generate_stream(pregunta):
        print(chunk, end="", flush=True)
    print()


async def demo_resiliencia() -> None:
    """Prueba que una API key inválida no tira abajo el programa entero."""
    config_rota = LLMConfig(
        provider=Provider.OPENAI,
        model="gpt-4o-mini",
        openai_api_key=SecretStr("sk-key-invalida-a-proposito"),
    )
    manager_roto = AsyncLLMManager(config_rota)
    pregunta = [ChatMessage(role="user", content="¿Qué es la entropía?")]
    resultado = await manager_roto.generate(pregunta)

    print("\n--- Prueba de resiliencia ---")
    print("¿El programa siguió vivo?: ✅ Sí")
    print("Error capturado (sin crash):", resultado.error)


async def main() -> None:
    await demo_validacion()

    pregunta = [ChatMessage(role="user", content="¿Qué es la entropía? Respondé en 2 líneas.")]

    # Solo se arman los proveedores cuya API key esté realmente en el .env:
    # sin key, se saltea con un aviso en vez de romper todo el programa.
    proveedores = [
        (Provider.OPENAI, "gpt-4o-mini", "OPENAI_API_KEY", "openai_api_key", "OpenAI", "🟢"),
        (Provider.ANTHROPIC, "claude-sonnet-5", "ANTHROPIC_API_KEY", "anthropic_api_key", "Anthropic", "🟣"),
        (Provider.GEMINI, "gemini-flash-latest", "GOOGLE_API_KEY", "google_api_key", "Gemini", "🔵"),
    ]

    activos = []
    for provider, modelo, env_var, campo_key, nombre, emoji in proveedores:
        api_key = os.environ.get(env_var)
        if not api_key:
            print(f"⏭️  {nombre}: falta {env_var} en el .env, se saltea.")
            continue
        config = LLMConfig(**{
            "provider": provider,
            "model": modelo,
            campo_key: SecretStr(api_key),
            "max_tokens": 200,
        })
        activos.append((AsyncLLMManager(config), nombre, emoji))

    if not activos:
        print("\n⚠️  No hay ninguna API key configurada. Agregá al menos una al .env.")
        return

    print("\n--- Modo normal ---")
    for manager, nombre, emoji in activos:
        await demo_generate(manager, pregunta, nombre, emoji)

    print("\n--- Modo streaming ---")
    for manager, nombre, emoji in activos:
        await demo_stream(manager, pregunta, nombre, emoji)

    await demo_resiliencia()


if __name__ == "__main__":
    asyncio.run(main())
