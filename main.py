import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
queues = {}
volumes = {}

class MusicControls(discord.ui.View):
    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=None)
        self.player = player

    @discord.ui.button(label="⏸ Pause", style=discord.ButtonStyle.gray)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player.is_playing():
            await self.player.pause()
            await interaction.response.send_message("⏸️ Pausiert", ephemeral=True)

    @discord.ui.button(label="▶ Resume", style=discord.ButtonStyle.gray)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player.is_paused():
            await self.player.resume()
            await interaction.response.send_message("▶ Fortgesetzt", ephemeral=True)

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.gray)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.stop()
        await interaction.response.send_message("⏭ Übersprungen", ephemeral=True)

    @discord.ui.button(label="⏹ Stop", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.disconnect()
        queues[self.player.guild.id] = []
        await interaction.response.send_message("⏹ Gestoppt und getrennt", ephemeral=True)

    @discord.ui.button(label="🔉 Leiser", style=discord.ButtonStyle.blurple, row=1)
    async def quieter(self, interaction: discord.Interaction, button: discord.ui.Button):
        volumes[self.player.guild.id] = max(0.0, volumes.get(self.player.guild.id, 0.5) - 0.1)
        await self.player.set_volume(int(volumes[self.player.guild.id] * 100))
        await interaction.response.send_message(f"🔉 Lautstärke: {int(volumes[self.player.guild.id]*100)}%", ephemeral=True)

    @discord.ui.button(label="🔊 Lauter", style=discord.ButtonStyle.blurple, row=1)
    async def louder(self, interaction: discord.Interaction, button: discord.ui.Button):
        volumes[self.player.guild.id] = min(1.0, volumes.get(self.player.guild.id, 0.5) + 0.1)
        await self.player.set_volume(int(volumes[self.player.guild.id] * 100))
        await interaction.response.send_message(f"🔊 Lautstärke: {int(volumes[self.player.guild.id]*100)}%", ephemeral=True)

    @discord.ui.button(label="📄 Queue", style=discord.ButtonStyle.gray, row=1)
    async def show_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        q = queues.get(self.player.guild.id, [])
        if not q:
            await interaction.response.send_message("📭 Keine Songs in der Warteschlange", ephemeral=True)
        else:
            msg = "\n".join([f"{i+1}. {track.title}" for i, track in enumerate(q)])
            await interaction.response.send_message(f"📃 Warteschlange:\n{msg}", ephemeral=True)

@bot.event
async def on_ready():
    await wavelink.NodePool.create(host='localhost', port=2333, password='youshallnotpass')
    print(f"✅ Bot gestartet als {bot.user}")

@bot.tree.command(name="play", description="Spiele Musik über Lavalink")
@app_commands.describe(query="Suchbegriff oder YouTube-Link")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    vc = interaction.user.voice
    if not vc:
        await interaction.followup.send("❌ Du bist in keinem Voice-Channel.")
        return

    player: wavelink.Player = interaction.guild.voice_client or await vc.channel.connect(cls=wavelink.Player)
    volumes[interaction.guild.id] = volumes.get(interaction.guild.id, 0.5)
    
    track = await wavelink.YouTubeTrack.search(query, return_first=True)
    if not track:
        await interaction.followup.send("❌ Kein Track gefunden.")
        return

    q = queues.setdefault(interaction.guild.id, [])
    if not player.is_playing():
        await player.play(track)
        await player.set_volume(int(volumes[interaction.guild.id] * 100))
        embed = discord.Embed(title="🎶 Now Playing", description=track.title, color=discord.Color.blurple())
        embed.add_field(name="Kanal", value=track.author)
        embed.add_field(name="Dauer", value=str(track.duration))
        await interaction.followup.send(embed=embed, view=MusicControls(player))
    else:
        q.append(track)
        await interaction.followup.send(f"➕ In Warteschlange: **{track.title}**")

@bot.event
async def on_wavelink_track_end(player: wavelink.Player, track, reason):
    q = queues.get(player.guild.id, [])
    if q:
        next_track = q.pop(0)
        await player.play(next_track)
        channel = discord.utils.get(player.guild.text_channels, name="allgemein")
        if channel:
            embed = discord.Embed(title="🎶 Now Playing", description=next_track.title, color=discord.Color.blurple())
            embed.add_field(name="Kanal", value=next_track.author)
            embed.add_field(name="Dauer", value=str(next_track.duration))
            await channel.send(embed=embed, view=MusicControls(player))

bot.run(os.environ["DISCORD_TOKEN"])
