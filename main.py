import discord
from discord.ext import commands
from discord import FFmpegPCMAudio, app_commands
from yt_dlp import YoutubeDL
from discord import opus
import asyncio
import os

# === Opus laden ===
if not opus.is_loaded():
    opus.load_opus('libopus.so.0')

# === Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
queues = {}
volumes = {}

@bot.event
async def on_ready():
    for guild in bot.guilds:
        try:
            await bot.tree.sync(guild=guild)
        except Exception as e:
            print(f"Fehler beim Sync in {guild.name}: {e}")
    print(f"✅ Bot gestartet als {bot.user}")

class MusicControls(discord.ui.View):
    def __init__(self, embed: discord.Embed):
        super().__init__(timeout=None)
        self.embed = embed

    @discord.ui.button(label="⏸ Pause", style=discord.ButtonStyle.gray)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Pausiert", ephemeral=True)

    @discord.ui.button(label="▶ Resume", style=discord.ButtonStyle.gray)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶ Fortgesetzt", ephemeral=True)

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.gray)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            await interaction.response.send_message("⏭ Übersprungen", ephemeral=True)

    @discord.ui.button(label="⏹ Stop", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            queues[interaction.guild.id] = []
            vc.stop()
            await vc.disconnect()
            await interaction.response.send_message("⏹ Gestoppt und getrennt", ephemeral=True)

    @discord.ui.button(label="🔉 Leiser", style=discord.ButtonStyle.blurple, row=1)
    async def quieter(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        volumes[guild_id] = max(0.0, volumes.get(guild_id, 0.5) - 0.1)
        vc = interaction.guild.voice_client
        if vc and vc.source and isinstance(vc.source, discord.PCMVolumeTransformer):
            vc.source.volume = volumes[guild_id]
        await interaction.response.defer()
        await interaction.message.edit(embed=self._update_volume_field(), view=self)

    @discord.ui.button(label="🔊 Lauter", style=discord.ButtonStyle.blurple, row=1)
    async def louder(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        volumes[guild_id] = min(1.0, volumes.get(guild_id, 0.5) + 0.1)
        vc = interaction.guild.voice_client
        if vc and vc.source and isinstance(vc.source, discord.PCMVolumeTransformer):
            vc.source.volume = volumes[guild_id]
        await interaction.response.defer()
        await interaction.message.edit(embed=self._update_volume_field(), view=self)

    @discord.ui.button(label="📄 Queue", style=discord.ButtonStyle.gray, row=1)
    async def show_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        q = queues.get(interaction.guild.id, [])
        if not q:
            await interaction.response.send_message("📭 Keine Songs in der Warteschlange", ephemeral=True)
        else:
            msg = "\n".join([f"{i+1}. {t[1]}" for i, t in enumerate(q)])
            await interaction.response.send_message(f"📃 Warteschlange:\n{msg}", ephemeral=True)

    def _update_volume_field(self):
        for i, field in enumerate(self.embed.fields):
            if field.name == "Lautstärke":
                self.embed.set_field_at(i, name="Lautstärke", value=f"{int(volumes.get(self.embed.guild_id, 0.5)*100)}%", inline=True)
        return self.embed

@bot.tree.command(name="play", description="Spiele Musik oder Livestream von YouTube")
@app_commands.describe(query="Suchbegriff oder YouTube-Link")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    guild_id = interaction.guild.id

    if guild_id not in queues:
        queues[guild_id] = []

    if interaction.user.voice is None:
        await interaction.followup.send("❌ Du bist in keinem Voice-Channel.")
        return

    vc = interaction.guild.voice_client
    if vc is None:
        vc = await interaction.user.voice.channel.connect()

    ydl_opts = {
        'format': 'bestaudio[acodec=opus]/bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch1',
        'http_headers': {'User-Agent': 'Mozilla/5.0'},
        'cookiefile': 'cookies.txt'
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if "entries" in info:
                info = info['entries'][0]

            is_live = info.get("is_live", False)
            formats = info.get("formats", [])
            hls_url = next((f["url"] for f in formats if "m3u8" in f.get("ext", "") or "hls" in f.get("format", "").lower()), None)
            url = hls_url if is_live and hls_url else info["url"]
            title = info.get("title")
            channel = info.get("channel") or "Unbekannt"
            duration = info.get("duration_string") or "?"
            thumbnail = info.get("thumbnail")
            webpage_url = info.get("webpage_url")
    except Exception as e:
        await interaction.followup.send("❌ Fehler beim Laden.")
        print(e)
        return

    if not vc.is_playing() and not vc.is_paused():
        volume = volumes.get(guild_id, 0.5)
        ffmpeg_opts = "-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -protocol_whitelist file,http,https,tcp,tls,crypto,pipe"
        source = FFmpegPCMAudio(url, options='-vn -b:a 192k')
        source = discord.PCMVolumeTransformer(source, volume)
        vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(interaction, vc), bot.loop))

        embed = discord.Embed(title="🎶 Now Playing", description=f"**{title}**", color=discord.Color.blurple())
        embed.add_field(name="Kanal", value=channel, inline=True)
        embed.add_field(name="Dauer", value=duration, inline=True)
        embed.add_field(name="Lautstärke", value=f"{int(volume * 100)}%", inline=True)
        if is_live:
            embed.add_field(name="🔴 Livestream", value="Dieser Stream ist live!", inline=False)
        if webpage_url:
            embed.add_field(name="🔗 Link", value=f"[Zum Video]({webpage_url})", inline=False)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text=f"Hinzugefügt von {interaction.user.display_name}")

        await interaction.followup.send(embed=embed, view=MusicControls(embed))
    else:
        queues[guild_id].append((url, title))
        await interaction.followup.send(f"➕ In Warteschlange: **{title}**")

async def play_next(interaction, vc):
    guild_id = interaction.guild.id
    if guild_id not in queues or not queues[guild_id]:
        return

    url, title = queues[guild_id].pop(0)
    volume = volumes.get(guild_id, 0.5)
    ffmpeg_opts = "-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -protocol_whitelist file,http,https,tcp,tls,crypto,pipe"
    source = FFmpegPCMAudio(url, options='-vn -b:a 192k')
    source = discord.PCMVolumeTransformer(source, volume)
    vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(interaction, vc), bot.loop))

    embed = discord.Embed(title="🎶 Now Playing", description=f"**{title}**", color=discord.Color.blurple())
    embed.add_field(name="Lautstärke", value=f"{int(volume * 100)}%", inline=True)
    embed.set_footer(text="Automatisch gestartet")

    await interaction.channel.send(embed=embed, view=MusicControls(embed))

bot.run(os.environ["DISCORD_TOKEN"])
