import os
import discord
from discord.ext import commands
from discord import app_commands
import wavelink

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
LAVALINK_URI = "http://localhost:2333"
LAVALINK_PASS = "youshallnotpass"
GUILD_ID = discord.Object(id=1296888604697563238)

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
queue = {}

@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")
    await bot.tree.sync(guild=GUILD_ID)
    print("✅ Slash-Commands synchronisiert")

    # Lavalink Node verbinden (Wavelink 3.4.1 Style)
    await wavelink.NodePool.connect(client=bot, nodes=[
        wavelink.Node(uri=LAVALINK_URI, password=LAVALINK_PASS)
    ])
    print("✅ Lavalink verbunden")

def get_queue(guild_id):
    return queue.setdefault(guild_id, [])

@bot.tree.command(name="play", description="Spiele Musik")
@app_commands.describe(query="Titel oder YouTube-Link")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.followup.send("❌ Du bist nicht in einem Voice-Channel.")
        return

    vc: wavelink.Player = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect(cls=wavelink.Player)

    track = await wavelink.YouTubeTrack.search(query=query, return_first=True)
    if not vc.is_playing():
        await vc.play(track)
        await interaction.followup.send(f"▶️ Spiele: **{track.title}**")
    else:
        get_queue(interaction.guild.id).append(track)
        await interaction.followup.send(f"➕ Zur Queue hinzugefügt: **{track.title}**")

@bot.tree.command(name="skip", description="Überspringe aktuellen Song")
async def skip(interaction: discord.Interaction):
    vc: wavelink.Player = interaction.guild.voice_client
    if vc and vc.is_playing():
        await vc.stop()
        await interaction.response.send_message("⏭️ Song übersprungen.")
    else:
        await interaction.response.send_message("❌ Kein Song wird gerade gespielt.")

@bot.tree.command(name="stop", description="Stoppt die Wiedergabe und trennt den Bot")
async def stop(interaction: discord.Interaction):
    vc: wavelink.Player = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
        queue.pop(interaction.guild.id, None)
        await interaction.response.send_message("⏹️ Bot getrennt und Queue gelöscht.")
    else:
        await interaction.response.send_message("❌ Ich bin nicht verbunden.")

@bot.tree.command(name="queue", description="Zeigt die aktuelle Warteschlange")
async def queue_cmd(interaction: discord.Interaction):
    q = get_queue(interaction.guild.id)
    if not q:
        await interaction.response.send_message("📭 Keine Songs in der Warteschlange.")
    else:
        text = "\n".join([f"{i+1}. {track.title}" for i, track in enumerate(q)])
        await interaction.response.send_message(f"📃 Warteschlange:\n{text}")

@bot.event
async def on_wavelink_track_end(player: wavelink.Player, track, reason):
    q = get_queue(player.guild.id)
    if q:
        next_track = q.pop(0)
        await player.play(next_track)
        text_channel = discord.utils.get(player.guild.text_channels, name="musik") or player.guild.text_channels[0]
        await text_channel.send(f"▶️ Jetzt spielt: **{next_track.title}**")

bot.run(DISCORD_TOKEN)
