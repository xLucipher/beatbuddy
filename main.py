import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import os

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = discord.Object(id=1296888604697563238)

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot angemeldet als {bot.user}")

    # Lavalink verbinden
    await wavelink.Pool.connect(
        client=bot,
        nodes=[
            wavelink.Node(
                uri='http://127.0.0.1:8081',
                password='youshallnotpass'
            )
        ]
    )
    print("🎵 Lavalink verbunden")

@bot.tree.command(name="play", description="Spielt ein Lied von YouTube", guild=GUILD_ID)
@app_commands.describe(query="Songtitel oder Link")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.followup.send("❌ Du musst in einem Voice-Channel sein!")
        return

    vc: wavelink.Player = await wavelink.Pool.get_node().connect(interaction.user.voice.channel)

    tracks = await wavelink.Pool.get_node().get_tracks(query)
    if not tracks:
        await interaction.followup.send("❌ Kein Track gefunden.")
        return

    track = tracks[0]
    await vc.play(track)

    embed = discord.Embed(
        title="🎶 Now Playing",
        description=f"[{track.title}]({track.uri})",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Dauer", value=track.length)
    embed.set_footer(text=f"Angefordert von {interaction.user.display_name}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="stop", description="Stoppt die Wiedergabe", guild=GUILD_ID)
async def stop(interaction: discord.Interaction):
    vc: wavelink.Player = wavelink.Pool.get_node().get_player(interaction.guild)
    if not vc:
        await interaction.response.send_message("❌ Kein Player aktiv.", ephemeral=True)
        return
    await vc.disconnect()
    await interaction.response.send_message("⏹️ Wiedergabe gestoppt und getrennt.")

@bot.tree.command(name="skip", description="Überspringt den aktuellen Song", guild=GUILD_ID)
async def skip(interaction: discord.Interaction):
    vc: wavelink.Player = wavelink.Pool.get_node().get_player(interaction.guild)
    if not vc or not vc.is_playing():
        await interaction.response.send_message("❌ Nichts läuft gerade.", ephemeral=True)
        return
    await vc.stop()
    await interaction.response.send_message("⏭️ Übersprungen.")

# Kommandos registrieren NACH Bot-Start
@bot.event
async def setup_hook():
    await bot.tree.sync(guild=GUILD_ID)
    print("✅ Slash-Commands synchronisiert")

bot.run(TOKEN)
