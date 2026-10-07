import os
import asyncio
import time

import discord
from deep_translator import GoogleTranslator, MyMemoryTranslator
from deep_translator.exceptions import TooManyRequests

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
ITALIAN_USER_ID = int(os.getenv("ITALIAN_USER_ID", "0"))
SPANISH_USER_ID = int(os.getenv("SPANISH_USER_ID", "0"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

if not TOKEN:
    raise RuntimeError("Falta DISCORD_BOT_TOKEN")
if not ITALIAN_USER_ID:
    raise RuntimeError("Falta ITALIAN_USER_ID")
if not SPANISH_USER_ID:
    raise RuntimeError("Falta SPANISH_USER_ID")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

translation_lock = asyncio.Lock()
last_request_time = 0.0

SOURCE_CHUNK = 450

# MyMemory necesita códigos regionales.
MYMEMORY_LANG = {
    "es": "es-ES",
    "it": "it-IT",
}


def split_source(text: str, max_len: int = SOURCE_CHUNK):
    chunks = []
    remaining = text.strip()

    while len(remaining) > max_len:
        cut = remaining.rfind("\n", 0, max_len)

        if cut < max_len // 2:
            cut = remaining.rfind(" ", 0, max_len)

        if cut < max_len // 2:
            cut = max_len

        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks


def split_discord(text: str, max_len: int = 1850):
    chunks = []
    remaining = text.strip()

    while len(remaining) > max_len:
        cut = remaining.rfind("\n", 0, max_len)

        if cut < max_len // 2:
            cut = remaining.rfind(" ", 0, max_len)

        if cut < max_len // 2:
            cut = max_len

        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks


async def wait_for_rate_limit():
    global last_request_time

    now = time.monotonic()
    wait = 1.25 - (now - last_request_time)

    if wait > 0:
        await asyncio.sleep(wait)

    last_request_time = time.monotonic()


async def google_translate(text: str, source: str, target: str):
    await wait_for_rate_limit()

    return await asyncio.to_thread(
        lambda: GoogleTranslator(
            source=source,
            target=target
        ).translate(text)
    )


async def mymemory_translate(text: str, source: str, target: str):
    await wait_for_rate_limit()

    mm_source = MYMEMORY_LANG[source]
    mm_target = MYMEMORY_LANG[target]

    return await asyncio.to_thread(
        lambda: MyMemoryTranslator(
            source=mm_source,
            target=mm_target
        ).translate(text)
    )


async def translate_part(text: str, source: str, target: str) -> str:
    try:
        return await google_translate(text, source, target)

    except TooManyRequests:
        print("Google ha limitado la IP. Esperando 3 segundos...")
        await asyncio.sleep(3)

        try:
            return await google_translate(text, source, target)

        except TooManyRequests:
            print("Google sigue limitado. Usando MyMemory como respaldo.")

    except Exception as exc:
        print(f"GoogleTranslator error: {exc}")
        print("Usando MyMemory como respaldo.")

    return await mymemory_translate(text, source, target)


async def translate_text(text: str, source: str, target: str) -> str:
    async with translation_lock:
        translated_parts = []

        for part in split_source(text):
            translated = await translate_part(part, source, target)
            translated_parts.append(translated)

        return " ".join(translated_parts)


@client.event
async def on_ready():
    print("=" * 55)
    print(f"Conectado como {client.user}")
    print(f"IT -> ES: {ITALIAN_USER_ID}")
    print(f"ES -> IT: {SPANISH_USER_ID}")
    print(f"Canal: {CHANNEL_ID if CHANNEL_ID else 'TODOS'}")
    print("Traductor: Google + respaldo MyMemory")
    print("=" * 55)


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if CHANNEL_ID and message.channel.id != CHANNEL_ID:
        return

    text = message.content.strip()

    if not text:
        return

    if message.author.id == ITALIAN_USER_ID:
        source = "it"
        target = "es"
        flag = "🇪🇸"

    elif message.author.id == SPANISH_USER_ID:
        source = "es"
        target = "it"
        flag = "🇮🇹"

    else:
        return

    try:
        translated = await translate_text(text, source, target)

        if not translated:
            return

        for chunk in split_discord(translated):
            await message.channel.send(
                f"{flag} {chunk}",
                allowed_mentions=discord.AllowedMentions.none()
            )

    except Exception as exc:
        print(
            f"Error traduciendo mensaje {message.id}: "
            f"{type(exc).__name__}: {exc}"
        )


client.run(TOKEN)
