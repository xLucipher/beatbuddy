import discord
from discord.ext import commands
import wavelink
import os

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

class MusicBot(wavelink.Client):
    async def on_ready(self):
        print(f"✅ Bot ist bereit als {bot.user}")

    async def on_wavelink_node_ready(self, node: wavelink.Node):
        print(f"🎵 Lavalink Node verbunden: {node.id}")

# Starte den Wavelink-Client
@bot.event
async def on_ready():
    if not hasattr(bot, "wavelink"):
        bot.wavelink = MusicBot()
        await bot.wavelink.initiate(
            client=bot,
            nodes=[
                wavelink.Node(uri='http://localhost:2333', password='youshallnotpass')
            ]
        )

bot.run(os.environ["DISCORD_TOKEN"])
