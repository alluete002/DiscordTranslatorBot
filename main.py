import os
import asyncio
import discord
from deep_translator import GoogleTranslator

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

async def translate_text(text: str, source: str, target: str) -> str:
    return await asyncio.to_thread(
        lambda: GoogleTranslator(source=source, target=target).translate(text)
    )

def split_message(text: str, max_len: int = 1850):
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

@client.event
async def on_ready():
    print(f"Conectado como {client.user}")
    print(f"IT -> ES: {ITALIAN_USER_ID}")
    print(f"ES -> IT: {SPANISH_USER_ID}")
    print(f"Canal: {CHANNEL_ID if CHANNEL_ID else 'TODOS'}")

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
        source, target, flag = "it", "es", "🇪🇸"
    elif message.author.id == SPANISH_USER_ID:
        source, target, flag = "es", "it", "🇮🇹"
    else:
        return

    try:
        translated = await translate_text(text, source, target)
        if not translated:
            return

        for chunk in split_message(translated):
            await message.channel.send(
                f"{flag} {chunk}",
                allowed_mentions=discord.AllowedMentions.none()
            )
    except Exception as exc:
        print(f"Error traduciendo mensaje {message.id}: {exc}")

client.run(TOKEN)
