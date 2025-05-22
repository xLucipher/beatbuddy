import discord
from discord.ext import commands
import wavelink
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ Bot ist online als {self.bot.user}")
        await wavelink.NodePool.create_node(
            bot=self.bot,
            host='localhost',
            port=2333,
            password='youshallnotpass'
        )

    @commands.command(name="join")
    async def join(self, ctx: commands.Context):
        if not ctx.author.voice:
            return await ctx.send("❌ Du bist nicht in einem Voice-Channel.")

        channel = ctx.author.voice.channel
        await channel.connect(cls=wavelink.Player)

    @commands.command(name="play")
    async def play(self, ctx: commands.Context, *, search: str):
        vc: wavelink.Player = ctx.voice_client

        if not vc:
            await ctx.invoke(self.join)

        vc: wavelink.Player = ctx.voice_client
        track = await wavelink.YouTubeTrack.search(search, return_first=True)
        await vc.play(track)
        await ctx.send(f"🎶 Now Playing: **{track.title}**")

    @commands.command(name="pause")
    async def pause(self, ctx: commands.Context):
        vc: wavelink.Player = ctx.voice_client
        await vc.pause()
        await ctx.send("⏸️ Pausiert")

    @commands.command(name="resume")
    async def resume(self, ctx: commands.Context):
        vc: wavelink.Player = ctx.voice_client
        await vc.resume()
        await ctx.send("▶ Fortgesetzt")

    @commands.command(name="stop")
    async def stop(self, ctx: commands.Context):
        vc: wavelink.Player = ctx.voice_client
        await vc.stop()
        await vc.disconnect()
        await ctx.send("⏹ Gestoppt")

    @commands.command(name="skip")
    async def skip(self, ctx: commands.Context):
        vc: wavelink.Player = ctx.voice_client
        await vc.stop()
        await ctx.send("⏭ Übersprungen")

bot.add_cog(Music(bot))
bot.run(os.environ["DISCORD_TOKEN"])
