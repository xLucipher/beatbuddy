import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="play", description="Spiele ein Lied ab")
    @app_commands.describe(query="YouTube URL oder Suchbegriff")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("❌ Du musst in einem Voice-Channel sein.")
            return

        vc: wavelink.Player = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect(cls=wavelink.Player)

        track = None
        try:
            tracks = await wavelink.YouTubeTrack.search(query, return_first=True)
            track = tracks
        except Exception as e:
            await interaction.followup.send("❌ Fehler beim Suchen des Tracks.")
            print(e)
            return

        await vc.play(track)
        await interaction.followup.send(f"▶️ **Jetzt spielt:** `{track.title}`")

    @app_commands.command(name="stop", description="Stoppt die Wiedergabe und verlässt den Channel")
    async def stop(self, interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("⏹️ Wiedergabe gestoppt und Voice-Channel verlassen.")
        else:
            await interaction.response.send_message("❌ Ich bin in keinem Voice-Channel.")

    @app_commands.command(name="pause", description="Pausiert die Wiedergabe")
    async def pause(self, interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc and vc.is_playing():
            await vc.pause()
            await interaction.response.send_message("⏸️ Wiedergabe pausiert.")
        else:
            await interaction.response.send_message("❌ Ich spiele gerade nichts.")

    @app_commands.command(name="resume", description="Setzt die Wiedergabe fort")
    async def resume(self, interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc and vc.is_paused():
            await vc.resume()
            await interaction.response.send_message("▶️ Wiedergabe fortgesetzt.")
        else:
            await interaction.response.send_message("❌ Nichts ist pausiert.")

    @app_commands.command(name="skip", description="Überspringt das aktuelle Lied")
    async def skip(self, interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc and vc.is_playing():
            await vc.stop()
            await interaction.response.send_message("⏭️ Lied übersprungen.")
        else:
            await interaction.response.send_message("❌ Ich spiele gerade nichts.")

@bot.event
async def on_ready():
    await wavelink.NodePool.create_node(bot=bot, host='localhost', port=2333, password='youshallnotpass')
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash-Commands synchronisiert: {[cmd.name for cmd in synced]}")
    except Exception as e:
        print(f"❌ Fehler beim Synchronisieren: {e}")

    print(f"🤖 Bot ist online als {bot.user}")

bot.tree.add_command(Music(bot).play)
bot.tree.add_command(Music(bot).stop)
bot.tree.add_command(Music(bot).pause)
bot.tree.add_command(Music(bot).resume)
bot.tree.add_command(Music(bot).skip)

bot.run(os.environ["DISCORD_TOKEN"])
