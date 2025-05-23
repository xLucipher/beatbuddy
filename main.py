import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import os

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1296888604697563238  # optional, für Debugzwecke

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)


# -- Slash-Commands registrieren (global) --
async def setup_hook():
    try:
        guild = discord.Object(id=GUILD_ID)
        cmds = await bot.tree.fetch_commands(guild=guild)
        for cmd in cmds:
            await bot.tree.remove_command(cmd.name, guild=guild)
        print("🧹 Alte Guild-Commands entfernt")
    except Exception as e:
        print(f"⚠️ Fehler beim Löschen der alten Guild-Commands: {e}")

    await bot.tree.sync()
    print("✅ Slash-Commands synchronisiert (global)")

bot.setup_hook = setup_hook


@bot.event
async def on_ready():
    print(f"✅ Bot angemeldet als {bot.user}")
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


# --- /play ---
@bot.tree.command(name="play", description="Spielt ein Lied von YouTube", guild=GUILD_ID)
@app_commands.describe(query="Songtitel oder Link")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    # Prüfen, ob der Nutzer in einem Voice-Channel ist
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.followup.send("❌ Du musst in einem Voice-Channel sein, um Musik abzuspielen.")
        return

    # Prüfen, ob der Bot bereits verbunden ist
    vc: wavelink.Player = wavelink.Player.connected(interaction.guild)

    if not vc:
        vc = await interaction.user.voice.channel.connect(cls=wavelink.Player)
    else:
        # Falls der Bot verbunden ist, prüfen ob er im gleichen Channel ist
        if vc.channel != interaction.user.voice.channel:
            await vc.disconnect()
            vc = await interaction.user.voice.channel.connect(cls=wavelink.Player)

    # Track suchen
    track = await wavelink.Playable.search(query, source=wavelink.TrackSource.YOUTUBE)

    if not track:
        await interaction.followup.send("❌ Kein Track gefunden.")
        return

    await vc.play(track)
    await interaction.followup.send(f"🎶 Spiele: `{track.title}`")

# --- /stop ---
@bot.tree.command(name="stop", description="Stoppt die Wiedergabe")
async def stop(interaction: discord.Interaction):
    player: wavelink.Player = wavelink.Pool.get_node().get_player(interaction.guild)

    if not player:
        await interaction.response.send_message("❌ Kein Player aktiv.", ephemeral=True)
        return

    await player.disconnect()
    await interaction.response.send_message("⏹️ Wiedergabe gestoppt und getrennt.")


# --- /skip ---
@bot.tree.command(name="skip", description="Überspringt den aktuellen Song")
async def skip(interaction: discord.Interaction):
    player: wavelink.Player = wavelink.Pool.get_node().get_player(interaction.guild)

    if not player or not player.is_playing():
        await interaction.response.send_message("❌ Nichts läuft gerade.", ephemeral=True)
        return

    await player.stop()
    await interaction.response.send_message("⏭️ Übersprungen.")


bot.run(TOKEN)
