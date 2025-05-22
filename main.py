import os
import discord
from discord.ext import commands
from discord import app_commands
import wavelink

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
GUILD_ID = discord.Object(id=1296888604697563238)  # Deine Guild-ID

@bot.event
async def on_ready():
    print(f"✅ Bot gestartet als {bot.user}")
    await bot.tree.sync(guild=GUILD_ID)
    print("✅ Slash-Commands synchronisiert")

    if not wavelink.NodePool.get_node():
        node = wavelink.Node(uri="http://localhost:2333", password="youshallnotpass")
        await wavelink.NodePool.connect(client=bot, nodes=[node])
        print("✅ Lavalink verbunden")

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = {}

    def get_queue(self, guild_id):
        return self.queue.setdefault(guild_id, [])

    @app_commands.command(name="play", description="Spiele einen Song oder Stream")
    async def play(self, interaction: discord.Interaction, query: str):
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
            await interaction.followup.send(f"🎶 Jetzt spielt: **{track.title}**")
        else:
            self.get_queue(interaction.guild.id).append(track)
            await interaction.followup.send(f"➕ Zur Warteschlange hinzugefügt: **{track.title}**")

    @app_commands.command(name="skip", description="Überspringe den aktuellen Song")
    async def skip(self, interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc and vc.is_playing():
            await vc.stop()
            await interaction.response.send_message("⏭️ Übersprungen.")
        else:
            await interaction.response.send_message("❌ Kein Song wird gespielt.")

    @app_commands.command(name="stop", description="Stoppt Musik und trennt den Bot")
    async def stop(self, interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            self.queue.pop(interaction.guild.id, None)
            await interaction.response.send_message("⏹️ Bot getrennt.")
        else:
            await interaction.response.send_message("❌ Ich bin nicht verbunden.")

    @app_commands.command(name="pause", description="Pausiert die Wiedergabe")
    async def pause(self, interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc and vc.is_playing():
            await vc.pause()
            await interaction.response.send_message("⏸️ Pausiert.")
        else:
            await interaction.response.send_message("❌ Kein Song läuft.")

    @app_commands.command(name="resume", description="Setzt die Wiedergabe fort")
    async def resume(self, interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client
        if vc and vc.is_paused():
            await vc.resume()
            await interaction.response.send_message("▶️ Fortgesetzt.")
        else:
            await interaction.response.send_message("❌ Ich bin nicht pausiert.")

    @app_commands.command(name="queue", description="Zeigt die Warteschlange")
    async def queue_(self, interaction: discord.Interaction):
        q = self.get_queue(interaction.guild.id)
        if not q:
            await interaction.response.send_message("📭 Keine Songs in der Warteschlange.")
        else:
            text = "\n".join([f"{i+1}. {track.title}" for i, track in enumerate(q)])
            await interaction.response.send_message(f"📃 Warteschlange:\n{text}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player: wavelink.Player, track, reason):
        q = self.get_queue(player.guild.id)
        if q:
            next_track = q.pop(0)
            await player.play(next_track)
            channel = discord.utils.get(player.guild.text_channels, name="musik") or player.guild.text_channels[0]
            await channel.send(f"🎶 Jetzt spielt: **{next_track.title}**")

# Setup
bot.tree.add_command(Music(bot).play, guild=GUILD_ID)
bot.tree.add_command(Music(bot).skip, guild=GUILD_ID)
bot.tree.add_command(Music(bot).stop, guild=GUILD_ID)
bot.tree.add_command(Music(bot).pause, guild=GUILD_ID)
bot.tree.add_command(Music(bot).resume, guild=GUILD_ID)
bot.tree.add_command(Music(bot).queue_, guild=GUILD_ID)
bot.add_cog(Music(bot))

bot.run(DISCORD_TOKEN)
