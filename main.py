import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import os

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
volumes = {}

@bot.event
async def on_ready():
    for guild in bot.guilds:
        try:
            await bot.tree.sync(guild=guild)
        except Exception as e:
            print(f"Fehler beim Sync in {guild.name}: {e}")
    await wavelink.NodePool.create_node(
        bot=bot,
        host='localhost',
        port=2333,
        password='youshallnotpass',
        https=False
    )
    print(f"✅ Bot gestartet als {bot.user}")

class MusicControls(discord.ui.View):
    def __init__(self, track: wavelink.Playable):
        super().__init__(timeout=None)
        self.track = track

    @discord.ui.button(label="⏸ Pause", style=discord.ButtonStyle.gray)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc and vc.is_playing():
            await vc.pause()
            await interaction.response.send_message("⏸️ Pausiert", ephemeral=True)

    @discord.ui.button(label="▶ Resume", style=discord.ButtonStyle.gray)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc and vc.is_paused():
            await vc.resume()
            await interaction.response.send_message("▶ Fortgesetzt", ephemeral=True)

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.gray)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc:
            await vc.stop()
            await interaction.response.send_message("⏭ Übersprungen", ephemeral=True)

    @discord.ui.button(label="⏹ Stop", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("⏹ Gestoppt und getrennt", ephemeral=True)

@bot.tree.command(name="play", description="Spiele Musik oder Livestream von YouTube")
@app_commands.describe(query="Suchbegriff oder YouTube-Link")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    if interaction.user.voice is None:
        await interaction.followup.send("❌ Du bist in keinem Voice-Channel.")
        return

    vc: wavelink.Player = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect(cls=wavelink.Player)

    track = await wavelink.YouTubeTrack.search(query, return_first=True)
    volume = volumes.get(interaction.guild.id, 0.5)
    vc.volume = int(volume * 100)
    await vc.play(track)

    embed = discord.Embed(title="🎶 Now Playing", description=f"**{track.title}**", color=discord.Color.blurple())
    embed.add_field(name="Kanal", value=track.author, inline=True)
    embed.add_field(name="Dauer", value=str(track.length // 1000) + " Sek.", inline=True)
    embed.add_field(name="Lautstärke", value=f"{int(volume * 100)}%", inline=True)
    if track.uri:
        embed.add_field(name="🔗 Link", value=f"[Zum Video]({track.uri})", inline=False)
    embed.set_footer(text=f"Hinzugefügt von {interaction.user.display_name}")
    await interaction.followup.send(embed=embed, view=MusicControls(track))

bot.run(os.environ["DISCORD_TOKEN"])
