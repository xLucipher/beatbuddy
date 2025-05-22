import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="/", intents=intents)

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ Eingeloggt als {self.bot.user} (ID: {self.bot.user.id})")
        await bot.tree.sync()
        await wavelink.Node.connect(
            host="localhost",
            port=2333,
            password="youshallnotpass"
    )

    @app_commands.command(name="play", description="Spiele einen Song über YouTube")
    @app_commands.describe(search="Songtitel oder Link")
    async def play(self, interaction: discord.Interaction, search: str):
        await interaction.response.defer()

        vc: wavelink.Player = interaction.guild.voice_client

        if not vc:
            channel = interaction.user.voice.channel
            vc = await channel.connect(cls=wavelink.Player)

        track = await wavelink.YouTubeTrack.search(search, return_first=True)
        await vc.play(track)

        await interaction.followup.send(f"🎵 Spiele jetzt: **{track.title}**")

    @app_commands.command(name="pause", description="Pausiert die Wiedergabe")
    async def pause(self, interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc and vc.is_playing():
            await vc.pause()
            await interaction.response.send_message("⏸️ Pause")

    @app_commands.command(name="resume", description="Setzt die Wiedergabe fort")
    async def resume(self, interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc and vc.is_paused():
            await vc.resume()
            await interaction.response.send_message("▶ Fortgesetzt")

    @app_commands.command(name="skip", description="Überspringt den aktuellen Track")
    async def skip(self, interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc and vc.is_playing():
            await vc.stop()
            await interaction.response.send_message("⏭ Übersprungen")

    @app_commands.command(name="stop", description="Stoppt die Wiedergabe und verlässt den Channel")
    async def stop(self, interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("⏹ Gestoppt")

bot.add_cog(Music(bot))
bot.run(os.getenv("DISCORD_TOKEN"))
