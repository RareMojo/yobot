from discord.ext import commands
import discord
from cogs.Music.music_player import MusicPlayer
from utils.logger import log_debug, log_error
from utils.tools import update_config, create_embed
import asyncio
from datetime import datetime

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord_bot.bot import Bot


class MusicCog(commands.Cog, name="MusicCog", description="Streams audio from the internet with various effects."):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.music_channel_ids = self.bot.config['music_channel_ids']
        self.thumbnail = 'https://i.imgur.com/tSuXN8P.png'
        self.music_volume = self.bot.config['music_volume']
        self.player = MusicPlayer(bot, [], None, None)
        log_debug(bot, "MusicCog initialized.")

    async def join_voice_channel(self, ctx):
        """Joins the voice channel the user is in."""
        if ctx.author.voice is None:
            embed = create_embed("Voice Channel Required", "You need to be in a voice channel to use this command!", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)
            return None
        elif ctx.message.channel.id not in self.music_channel_ids:
            embed = create_embed("Music Text Channel Required", "You need type in the music chat to use this command!", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)

            return None

        voice_channel = ctx.author.voice.channel
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client is None:
            try:
                voice_client = await voice_channel.connect()
            except Exception as e:
                embed = create_embed("Connection Error", f"Error connecting to voice channel: {e}", discord.Color.red(), self.thumbnail)
                await ctx.send(embed=embed)
                log_error(self.bot, f"Error connecting: {e}")
                return None
        elif voice_client.channel != voice_channel:
            try:
                await voice_client.move_to(voice_channel)
            except Exception as e:
                embed = create_embed("Move Error", f"Error moving to voice channel: {e}", discord.Color.red(), self.thumbnail)
                await ctx.send(embed=embed)
                log_error(self.bot, f"Error moving: {e}")
                return None

        return voice_client

    async def idle_disconnect(self, ctx):
        """Disconnects the bot if it is idle for 5 minutes."""
        await asyncio.sleep(300)
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client and not voice_client.is_playing():
            embed = create_embed("Idle Disconnect", "You haven't played anything in a while.", discord.Color.orange(), self.thumbnail)
            await ctx.send(embed=embed)
            await asyncio.sleep(8)
            await voice_client.disconnect()
            self.player.is_playing = False
            await self.player.delete_player_embed()

    @commands.hybrid_command(name="play", help="Adds a song to the queue or plays immediately if none is playing. You can search or use a URL.")
    async def play(self, ctx, song: str):
        """Adds a song to the queue and starts playback."""
        voice_client = await self.join_voice_channel(ctx)
        if voice_client is None:
            return

        if len(self.player.queue) >= 100:
            embed = create_embed("Queue Full", "The queue is full! Maximum queue size is 100 songs.", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)
            return

        await ctx.send(f"Song Added to the queue: {song}")

        if self.player.is_playing:
            self.player.queue.append((song, 1.0))
        else:
            self.player.is_playing = True
            try:
                await self.player._play_youtube_audio(ctx, voice_client, song, volume=self.music_volume / 100)
                self.bot.loop.create_task(self.idle_disconnect(ctx))
            except Exception as e:
                log_error(self.bot, f"Error playing {song}: {e}")
                self.player.is_playing = False
                
    @commands.hybrid_command(name="slowplay", help="Plays a song at 0.75x speed.")
    async def slowplay(self, ctx, song: str):
        """Adds a song to the queue and plays at slow 0.75x speed."""
        await self.play_with_speed(ctx, song, 0.75, "slowplay", self.music_volume )

    @commands.hybrid_command(name="fastplay", help="Plays a song at 1.25x speed.")
    async def fastplay(self, ctx, song: str):
        """Adds a song to the queue and plays at fast 1.25x speed."""
        await self.play_with_speed(ctx, song, 1.25, "fastplay", self.music_volume)

    async def play_with_speed(self, ctx, song: str, speed: float, label: str, volume: int):
        """Helper to play songs with different speeds."""
        voice_client = await self.join_voice_channel(ctx)
        if voice_client is None:
            return

        if len(self.player.queue) >= 100:
            embed = create_embed("Queue Full", "The queue is full! Maximum queue size is 100 songs.", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)
            return

        await ctx.send(f"Song added at {label} speed: {song}")

        if self.player.is_playing:
            self.player.queue.append((song, speed))
        else:
            self.player.is_playing = True
            try:
                await self.player._play_youtube_audio(ctx, voice_client, song, playback_speed=speed, volume=self.music_volume / 100)
                # start the idle disconnect task
                self.bot.loop.create_task(self.idle_disconnect(ctx))
            except Exception as e:
                await ctx.send(f"An error occurred: {e}")
                log_error(
                    self.bot, f"Error playing {song} at {label} speed: {e}")
                self.player.is_playing = False
                
    @commands.hybrid_command(name="stop", help="Stops the audio and clears the queue.")
    async def stop(self, ctx):
        """Stops the audio, clears the queue, and disconnects."""
        if ctx.author.voice is None:
            embed = create_embed("Voice Channel Required", "You need to be in a voice channel to use this command!", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)
            return None
        elif ctx.message.channel.id not in self.music_channel_ids:
            embed = create_embed("Music Text Channel Required", "You need type in the music chat to use this command!", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)
            return None
        
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            self.player.queue.clear()
            self.player.is_playing = False
            await self.player.delete_player_embed()
            await voice_client.disconnect()
            embed = create_embed("Stopped", "Audio stopped and queue cleared.", discord.Color.green(), self.thumbnail)
            await ctx.send(embed=embed)
        else:
            embed = create_embed("No Audio", "No audio is currently playing.", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="skip", help="Skips the current song.")
    async def skip(self, ctx):
        """Skips the current song."""
        if ctx.author.voice is None:
            embed = create_embed("Voice Channel Required", "You need to be in a voice channel to use this command!", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)
            return None
        elif ctx.message.channel.id not in self.music_channel_ids:
            embed = create_embed("Music Text Channel Required", "You need type in the music chat to use this command!", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)
            return None
        
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            embed = create_embed("Skipped", f"{ctx.author} skipped the current song.", discord.Color.green(), self.thumbnail)
            await ctx.send(embed=embed)
            self.bot.loop.create_task(self.idle_disconnect(ctx))
        else:
            embed = create_embed("No Song", "No song is currently playing.", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="queue", help="Displays the current queue.")
    async def list_queue(self, ctx):
        """Lists the current queue."""
        if ctx.message.channel.id not in self.music_channel_ids:
            embed = create_embed("Music Text Channel Required", "You need type in the music chat to use this command!", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)
            return None
        
        if self.player.queue:
            queue_list = "\n".join([f"{i + 1}. {url}" for i, (url, _) in enumerate(self.player.queue)])
            queue_list = queue_list.replace("'", "")
            embed = create_embed("Current Queue", f"Current queue:\n{queue_list}", discord.Color.blue(), self.thumbnail)
            await ctx.send(embed=embed)
        else:
            embed = create_embed("Queue Empty", "The queue is empty.", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="clear", help="Clears the current queue.")
    async def clear_queue(self, ctx):
        """Clears the queue."""
        if ctx.author.voice is None:
            embed = create_embed("Voice Channel Required", "You need to be in a voice channel to use this command!", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)
            return None
        elif ctx.message.channel.id not in self.music_channel_ids:
            embed = create_embed("Music Text Channel Required", "You need type in the music chat to use this command!", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)
            return None
        
        self.player.queue.clear()
        embed = create_embed("Queue Cleared", "The queue has been cleared.", discord.Color.green(), self.thumbnail)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="volume", help="Sets the volume of the music player.")
    async def set_volume(self, ctx, volume: int or None = None):
        """Sets the volume of the music player."""
        if ctx.author.voice is None:
            embed = create_embed("Voice Channel Required", "You need to be in a voice channel to use this command!", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)
            return None
        elif ctx.message.channel.id not in self.music_channel_ids:
            embed = create_embed("Music Text Channel Required", "You need type in the music chat to use this command!", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)
            return None
        
        if volume is None:
            embed = create_embed("Current Volume", f"The current volume is: {self.music_volume}\nUse /volume <0-100> to set the volume.", discord.Color.blue(), self.thumbnail)
            await ctx.send(embed=embed)
        elif volume < 0 or volume > 100:
            embed = create_embed("Invalid Volume", "Volume must be between 0 and 100.", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)
            return
        
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client and voice_client.is_playing():
            voice_client.source.volume = volume / 100
            self.music_volume = volume
            update_config(self.bot.config_file, {"music_volume": volume})
            embed = create_embed("Volume Set", f"Volume set to {volume}", discord.Color.green(), self.thumbnail)
            await ctx.send(embed=embed)
        else:
            embed = create_embed("No Audio", "No audio is playing.", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="helpmusic", help="Displays help with available commands.")
    async def help_command(self, ctx):
        """Displays help with available commands."""
        if ctx.message.channel.id not in self.music_channel_ids:
            embed = create_embed("Music Text Channel Required", "You need type in the music chat to use this command!", discord.Color.red(), self.thumbnail)
            await ctx.send(embed=embed)
            return None
        
        help_embed = discord.Embed(
            title="Help - Available Commands",
            description="Here are the available commands you can use:",
            color=discord.Color.blurple()
        )

        for command in self.bot.commands:
            if not command.hidden and await command.can_run(ctx):
                help_embed.add_field(
                    name=f"/{command.name}",
                    value=command.help or "No description available.",
                    inline=False
                )

        help_embed.set_footer(
            text="Use the commands with / followed by the command name.\n\n  yobot | " + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') + " UTC"
        )
        await ctx.send(embed=help_embed)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handles the reactions added to the player embed."""
        if user.bot:
            return  # Ignore bot reactions
        
        message = reaction.message

        if message.id != self.player.player_message.id:
            return  # Ignore reactions on other messages

        # Only handle reactions for the current player message
        if reaction.emoji == '▶️':
            voice_client = discord.utils.get(self.bot.voice_clients, guild=message.guild)
            if voice_client and not voice_client.is_playing():
                voice_client.resume()
        if reaction.emoji == '⏸️':
            voice_client = discord.utils.get(self.bot.voice_clients, guild=message.guild)
            if voice_client and voice_client.is_playing():
                voice_client.pause()
        elif reaction.emoji == '⏹️':
            voice_client = discord.utils.get(self.bot.voice_clients, guild=message.guild)
            if voice_client and voice_client.is_playing():
                voice_client.stop()
                self.player.queue.clear()
                self.player.is_playing = False
                await self.player.delete_player_embed()
        elif reaction.emoji == '⏭️':
            voice_client = discord.utils.get(self.bot.voice_clients, guild=message.guild)
            if voice_client and voice_client.is_playing():
                voice_client.stop()
        elif reaction.emoji == '❤️':
            pass
            
async def setup(bot: "Bot"):
    """Loads the cog."""
    try:
        await bot.add_cog(MusicCog(bot))
    except Exception as e:
        log_error(bot, f"Error loading MusicCog: {e}")