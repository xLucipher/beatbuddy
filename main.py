import discord
from discord.ext import commands
import wavelink
import os

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot ist bereit als {bot.user}")
    # Node starten (Standard-Lavalink-Einstellungen)
    await wavelink.NodePool.create_node(
        bot=bot,
        host='localhost',
        port=2333,
        password='youshallnotpass',
        https=False
    )

@bot.command()
async def join(ctx):
    if not ctx.author.voice:
        return await ctx.send("⚠ Du bist in keinem Voice-Channel.")
    channel = ctx.author.voice.channel
    await channel.connect(cls=wavelink.Player)

@bot.command()
async def play(ctx, *, search: str):
    player: wavelink.Player = ctx.voice_client
    if not player:
        return await ctx.send("⚠ Bot ist in keinem Voice-Channel.")

    track = await wavelink.YouTubeTrack.search(search, return_first=True)
    await player.play(track)
    await ctx.send(f"🎶 Spiele: **{track.title}**")

@bot.command()
async def stop(ctx):
    player: wavelink.Player = ctx.voice_client
    if player:
        await player.stop()
        await ctx.send("⏹ Wiedergabe gestoppt.")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Verlassen.")
