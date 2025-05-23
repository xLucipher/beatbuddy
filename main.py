import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import os

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = discord.Object(id=1296888604697563238)


class BeatBuddy(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        try:
            cmds = await self.tree.fetch_commands(guild=GUILD_ID)
            for cmd in cmds:
                await self.tree.remove_command(cmd.name, guild=GUILD_ID)
            print("🧹 Alte Guild-Commands entfernt")
        except Exception as e:
            print(f"⚠️ Fehler beim Löschen der alten Guild-Commands: {e}")

        await self.tree.sync(guild=GUILD_ID)
        print("✅ Slash-Commands synchronisiert (guild-basiert)")

    async def on_ready(self):
        print(f"✅ Bot angemeldet als {self.user}")
        await wavelink.Pool.connect(
            client=self,
            nodes=[
                wavelink.Node(
                    uri='http://127.0.0.1:8081',
                    password='youshallnotpass'
                )
            ]
        )
        print("🎵 Lavalink verbunden")

        cmds = await self.tree.fetch_commands(guild=GUILD_ID)
        print("📋 Registrierte Slash-Commands:")
        for cmd in cmds:
            print(f" - {cmd.name}")


bot = BeatBuddy()


@bot.tree.command(name="play", description="Spielt ein Lied von YouTube", guild=GUILD_ID)
@app_commands.describe(query="Songtitel oder Link")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.followup.send("❌ Du musst in einem Voice-Channel sein, um Musik abzuspielen.")
        return

    vc: wavelink.Player = wavelink.Player.connected(interaction.guild)

    if not vc:
        vc = await interaction.user.voice.channel.connect(cls=wavelink.Player)
    else:
        if vc.channel != interaction.user.voice.channel:
            await vc.disconnect()
            vc = await interaction.user.voice.channel.connect(cls=wavelink.Player)

    track = await wavelink.Playable.search(query, source=wavelink.TrackSource.YOUTUBE)

    if not track:
        await interaction.followup.send("❌ Kein Track gefunden.")
        return

    await vc.play(track)
    await interaction.followup.send(f"🎶 Spiele: `{track.title}`")


@bot.tree.command(name="stop", description="Stoppt die Wiedergabe", guild=GUILD_ID)
async def stop(interaction: discord.Interaction):
    player: wavelink.Player = wavelink.Pool.get_node().get_player(interaction.guild)
    if not player:
        await interaction.response.send_message("❌ Kein Player aktiv.", ephemeral=True)
        return

    await player.disconnect()
    await interaction.response.send_message("⏹️ Wiedergabe gestoppt und getrennt.")


@bot.tree.command(name="skip", description="Überspringt den aktuellen Song", guild=GUILD_ID)
async def skip(interaction: discord.Interaction):
    player: wavelink.Player = wavelink.Pool.get_node().get_player(interaction.guild)
    if not player or not player.is_playing():
        await interaction.response.send_message("❌ Nichts läuft gerade.", ephemeral=True)
        return

    await player.stop()
    await interaction.response.send_message("⏭️ Übersprungen.")


bot.run(TOKEN)
