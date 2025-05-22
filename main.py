import discord
from discord.ext import commands
import wavelink
import asyncio
import os

# === Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")
    await wavelink.NodePool.create_node(
        bot=bot,
        host='localhost',
        port=2333,
        password='youshallnotpass'
    )
    print("🎶 Lavalink verbunden!")

@bot.tree.command(name="play", description="Spiele Musik von YouTube")
@discord.app_commands.describe(query="YouTube-Link oder Suchbegriff")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    # Voicechannel verbinden
    if not interaction.user.voice:
        await interaction.followup.send("❌ Du bist in keinem Voicechannel.")
        return

    channel = interaction.user.voice.channel
    guild = interaction.guild
    
    if not guild.voice_client:
        vc: wavelink.Player = await channel.connect(cls=wavelink.Player)
    else:
        vc: wavelink.Player = guild.voice_client

    # Track suchen und abspielen
    tracks = await wavelink.YouTubeTrack.search(query)
    if not tracks:
        await interaction.followup.send("❌ Keine Ergebnisse gefunden.")
        return

    track = tracks[0]
    await vc.play(track)

    embed = discord.Embed(title="🎶 Now Playing", description=f"**{track.title}**", color=discord.Color.blurple())
    embed.add_field(name="Dauer", value=str(track.length // 1000) + " Sek.", inline=True)
    embed.add_field(name="Kanal", value=track.author, inline=True)
    embed.set_footer(text="Hinzugefügt von " + interaction.user.display_name)
    if track.thumbnail:
        embed.set_thumbnail(url=track.thumbnail)
    await interaction.followup.send(embed=embed)

bot.run(os.environ.get("DISCORD_TOKEN"))
