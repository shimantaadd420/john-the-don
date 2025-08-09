import discord
from discord.ext import commands
import yt_dlp
import asyncio

token = "YOUR_ACTUAL_TOKEN_HERE "

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

ytdlp_format_options = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "noplaylist": True,
    "ignoreerrors": True,
    "source_address": "0.0.0.0",
    "nocheckcertificate": True,
}

ffmpeg_options = {
    "options": "-vn",
}

ytdlp = yt_dlp.YoutubeDL(ytdlp_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=1.0):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()

        try:
            data = await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: ytdlp.extract_info(url, download=not stream)
                ),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            raise Exception("Timeout while downloading audio.")

        if "entries" in data:
            data = data["entries"][0]

        if stream:
            return cls(discord.FFmpegPCMAudio(data["url"], **ffmpeg_options), data=data)
        else:
            filename = ytdlp.prepare_filename(data)
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Music and more"))
    print(f"Logged in as {bot.user}")


@bot.command()
async def join(ctx):
    if ctx.author.voice is None:
        return await ctx.send("You’re not connected to a voice channel.")

    channel = ctx.author.voice.channel

    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()

    await ctx.send(f"Joined {channel}")


@bot.command()
async def leave(ctx):
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected from voice channel.")
    else:
        await ctx.send("I’m not in a voice channel.")


@bot.command()
async def play(ctx, *, url):
    if ctx.author.voice is None:
        return await ctx.send("You need to be in a voice channel to play music.")

    if ctx.voice_client is None:
        await ctx.author.voice.channel.connect()

    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            ctx.voice_client.play(
                player, after=lambda e: print(f"Player error: {e}") if e else None
            )
        except Exception as e:
            await ctx.send(f"Error playing audio: {e}")
            print(f"Error: {e}")
            return

    await ctx.send(f"Now playing: {player.title}")


@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Paused ⏸️")
    else:
        await ctx.send("Nothing is playing right now.")


@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Resumed ▶️")
    else:
        await ctx.send("The player is not paused.")


@bot.command()
async def stop(ctx):
    if ctx.voice_client and (
        ctx.voice_client.is_playing() or ctx.voice_client.is_paused()
    ):
        ctx.voice_client.stop()
        await ctx.send("Stopped ⏹️")
    else:
        await ctx.send("Nothing to stop.")


@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"Error: {str(error)}")


bot.run(token)
