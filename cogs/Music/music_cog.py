from discord.ext import commands
import discord
from cogs.Music.music_player import MusicPlayer
from utils.logger import log_debug, log_error
from utils.tools import update_config, create_embed
import asyncio
from datetime import datetime
import sqlite3
from random import shuffle

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
            await ctx.send("You need to be in a voice channel to use this command!", delete_after=12)
            return None
        elif ctx.message.channel.id not in self.music_channel_ids:
            await ctx.send("You need type in the music chat to use this command!", delete_after=12)
            return None

        voice_channel = ctx.author.voice.channel
        voice_client = discord.utils.get(
            self.bot.voice_clients, guild=ctx.guild)

        if voice_client is None:
            try:
                voice_client = await voice_channel.connect()
            except Exception as e:
                await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
                log_error(
                    self.bot, f"Unexpected error in join_voice_channel: {str(e)}")
                return None
        elif voice_client.channel != voice_channel:
            try:
                await voice_client.move_to(voice_channel)
            except Exception as e:
                await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
                log_error(
                    self.bot, f"Unexpected error in join_voice_channel: {str(e)}")
                return None

        return voice_client

    async def idle_disconnect(self, ctx):
        """Disconnects the bot if it is idle for 5 minutes."""
        for _ in range(30):
            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=ctx.guild)
            if voice_client is None or voice_client.is_playing() or self.player.queue:
                return
            await asyncio.sleep(10)

        voice_client = discord.utils.get(
            self.bot.voice_clients, guild=ctx.guild)
        if voice_client and not voice_client.is_playing():
            try:
                await ctx.send("You haven't played anything in awhile.\nI'll leave for now, use one of the play commands to bring me back!", delete_after=12)
                await voice_client.disconnect()
                self.player.is_playing = False
                await self.player.delete_player_embed()
            except Exception as e:
                await ctx.send(f"Error disconnecting from voice:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
                log_error(self.bot, f"Error disconnecting from voice: {e}")

    @commands.hybrid_command(name="play", help="Adds a song to the queue or plays immediately if none is playing. You can search or use a URL.")
    async def play_song(self, ctx, song: str):
        """Adds a song to the queue and starts playback."""
        voice_client = await self.join_voice_channel(ctx)
        if voice_client is None:
            return

        if len(self.player.queue) >= 100:
            await ctx.send("The queue is full! Maximum queue size is 100 songs.", delete_after=12)
            return None

        await ctx.send(f":notes: **Song Requested**\nAdded to the queue:\n{song}")

        if self.player.is_playing:
            self.player.queue.append((song, 1.0))
        else:
            self.player.is_playing = True
            try:
                await self.player._play_youtube_audio(ctx, voice_client, song, volume=self.music_volume / 100)
                if not voice_client.is_playing() and not self.player.queue:
                    self.bot.loop.create_task(self.idle_disconnect(ctx))
            except Exception as e:
                await ctx.send(f"Error playing {song}:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
                log_error(self.bot, f"Error playing {song}: `{e}`")
                self.player.is_playing = False

    @commands.hybrid_command(name="replay", help="Plays the most recent song played in general.")
    async def replay_song(self, ctx):
        """Plays the most recent song played in general."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, playback_speed, user_name
                    FROM user_actions 
                    WHERE action = 'request'
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''')

                recent_song = cursor.fetchone()

                if recent_song is None:
                    await ctx.send(f"No songs have been requested yet!", delete_after=12)
                    return

                song_title, song_url, playback_speed, user_name = recent_song
                playback_speed = playback_speed or 1.0

                voice_client = await self.join_voice_channel(ctx)
                if voice_client is None:
                    return

                await ctx.send(f":notes: **Song Requested**\nAdded the most recent song to the queue:\n{song_title} requested by {user_name} (at speed {playback_speed}x)")

                if self.player.is_playing:
                    self.player.queue.append((song_url, playback_speed))
                else:
                    self.player.is_playing = True
                    await self.player._play_youtube_audio(ctx, voice_client, song_url, volume=self.music_volume / 100, playback_speed=playback_speed)
                    if not voice_client.is_playing() and not self.player.queue:
                        self.bot.loop.create_task(self.idle_disconnect(ctx))
        except sqlite3.Error as e:
            await ctx.send(f"Error playing the most recent song:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error playing the most recent song: {e}")
        except Exception as e:
            await ctx.send(f"Error playing the most recent song:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error playing the most recent song: {e}")

    @commands.hybrid_command(name="playrecent", help="Plays the most recent song you or another user requested.")
    async def replay_recent_song(self, ctx, user: discord.User = None):
        """Plays the most recent song requested by the user or another specified user."""
        try:
            if user is None:
                user = ctx.author

            user_id = str(user.id)

            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, playback_speed
                    FROM user_actions 
                    WHERE user_id = ? AND action = 'request'
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''', (user_id,))

                recent_song = cursor.fetchone()

                if recent_song is None:
                    if user == ctx.author:
                        await ctx.send(f"{user.mention}, you haven't requested any songs yet!", delete_after=12)
                    else:
                        await ctx.send(f"{user.mention} hasn't requested any songs yet!", delete_after=12)
                    return

                song_title, song_url, playback_speed = recent_song
                playback_speed = playback_speed or 1.0

                voice_client = await self.join_voice_channel(ctx)
                if voice_client is None:
                    return

                await ctx.send(f":notes: **Song Requested**\nAdded {user.mention}'s most recent song to the queue:\n{song_title} (at speed {playback_speed}x)")

                if self.player.is_playing:
                    self.player.queue.append((song_url, playback_speed))
                else:
                    self.player.is_playing = True
                    await self.player._play_youtube_audio(ctx, voice_client, song_url, volume=self.music_volume / 100, playback_speed=playback_speed)
                    if not voice_client.is_playing() and not self.player.queue:
                        self.bot.loop.create_task(self.idle_disconnect(ctx))
                        self.player.is_playing = False
        except sqlite3.Error as e:
            await ctx.send(f"Error playing the most recent song:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error playing the most recent song: {e}")
        except Exception as e:
            await ctx.send(f"Error playing the most recent song:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error playing the most recent song: {e}")

    @commands.hybrid_command(name="playtop", help="Plays the most requested song.")
    async def play_top_song(self, ctx):
        """Plays the most requested song."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, COUNT(*) as request_count 
                    FROM user_actions 
                    WHERE action = 'request' 
                    GROUP BY song_title, song_url 
                    ORDER BY request_count DESC 
                    LIMIT 1
                ''')
                top_song = cursor.fetchone()

                if top_song is None:
                    await ctx.send("No songs have been requested yet.", delete_after=12)
                    return

                song_title, song_url, _ = top_song

                voice_client = await self.join_voice_channel(ctx)
                if voice_client is None:
                    return

                await ctx.send(f":notes: **Song Requested**\nAdded the most requested song to the queue:\n{song_title}")

                if self.player.is_playing:
                    self.player.queue.append((song_url, 1.0))
                else:
                    self.player.is_playing = True
                    await self.player._play_youtube_audio(ctx, voice_client, song_url, volume=self.music_volume / 100)
                    if not voice_client.is_playing() and not self.player.queue:
                        self.bot.loop.create_task(self.idle_disconnect(ctx))
        except sqlite3.Error as e:
            await ctx.send(f"Error playing the most requested song:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error playing the most requested song: {e}")
        except Exception as e:
            await ctx.send(f"Error playing the most requested song:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error playing the most requested song: {e}")

    @commands.hybrid_command(name="playtopliked", help="Plays the most liked song.")
    async def play_top_liked(self, ctx):
        """Plays the most liked song."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, COUNT(*) as like_count 
                    FROM user_actions 
                    WHERE action = 'like' 
                    GROUP BY song_title, song_url 
                    ORDER BY like_count DESC 
                    LIMIT 1
                ''')
                top_liked_song = cursor.fetchone()

                if top_liked_song is None:
                    await ctx.send("No songs have been liked yet.", delete_after=12)
                    return

                song_title, song_url, _ = top_liked_song

                voice_client = await self.join_voice_channel(ctx)
                if voice_client is None:
                    return

                await ctx.send(f":notes: **Song Requested**\nAdded the most liked song to the queue:\n{song_title}")

                if self.player.is_playing:
                    self.player.queue.append((song_url, 1.0))
                else:
                    self.player.is_playing = True
                    await self.player._play_youtube_audio(ctx, voice_client, song_url, volume=self.music_volume / 100)
                    if not voice_client.is_playing() and not self.player.queue:
                        self.bot.loop.create_task(self.idle_disconnect(ctx))
        except sqlite3.Error as e:
            await ctx.send(f"Error playing the most liked song:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error playing the most liked song: {e}")
        except Exception as e:
            await ctx.send(f"Error playing the most liked song:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error playing the most liked song: {e}")

    @commands.hybrid_command(name="playfavorite", help="Plays you or another users favorite song at their favorite speed.")
    async def play_favorite(self, ctx, user: discord.User = None):
        """Plays the favorite song of the invoking user or another specified user based on requests and uses the favorite speed."""
        try:
            if user is None:
                user = ctx.author

            user_id = str(user.id)

            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, playback_speed, COUNT(*) as request_count
                    FROM user_actions 
                    WHERE user_id = ? AND action = 'request'
                    GROUP BY song_title, song_url, playback_speed
                    ORDER BY request_count DESC 
                    LIMIT 1
                ''', (user_id,))

                favorite_song = cursor.fetchone()

                if favorite_song is None:
                    if user == ctx.author:
                        await ctx.send(f"{user.mention}, you haven't requested any songs yet!", delete_after=12)
                    else:
                        await ctx.send(f"{user.mention} hasn't requested any songs yet!", delete_after=12)
                    return

                song_title, song_url, playback_speed, request_count = favorite_song
                playback_speed = playback_speed or 1.0

                voice_client = await self.join_voice_channel(ctx)
                if voice_client is None:
                    return

                await ctx.send(f":notes: **Song Requested**\nAdded {user.mention}'s favorite song to the queue:\n{song_title} (Requested {request_count} times at speed {playback_speed}x)")

                if self.player.is_playing:
                    self.player.queue.append((song_url, playback_speed))
                else:
                    self.player.is_playing = True
                    await self.player._play_youtube_audio(ctx, voice_client, song_url, volume=self.music_volume / 100, playback_speed=playback_speed)
                    if not voice_client.is_playing() and not self.player.queue:
                        self.bot.loop.create_task(self.idle_disconnect(ctx))
        except sqlite3.Error as e:
            await ctx.send(f"Error playing the favorite song:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error playing the favorite song: {e}")
        except Exception as e:
            await ctx.send(f"Error playing the favorite song:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error playing the favorite song: {e}")

    @commands.hybrid_command(name="playtopspeed", help="Plays the most requested song with a speed change.")
    async def play_top_speed_song(self, ctx):
        """Plays the most requested song with a speed change."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, playback_speed, COUNT(*) as request_count 
                    FROM user_actions 
                    WHERE action = 'request' AND playback_speed != 1.0 
                    GROUP BY song_title, song_url, playback_speed 
                    ORDER BY request_count DESC 
                    LIMIT 1
                ''')
                top_speed_song = cursor.fetchone()

                if top_speed_song is None:
                    await ctx.send("No songs with speed changes have been requested yet.", delete_after=12)
                    return

                song_title, song_url, playback_speed, _ = top_speed_song

                voice_client = await self.join_voice_channel(ctx)
                if voice_client is None:
                    return

                await ctx.send(f":notes: **Song Requested**\nAdded song with the most speed changes to queue:\n{song_title} at speed {playback_speed}x")

                if self.player.is_playing:
                    self.player.queue.append((song_url, playback_speed))
                else:
                    self.player.is_playing = True
                    await self.player._play_youtube_audio(ctx, voice_client, song_url, volume=self.music_volume / 100, playback_speed=playback_speed)
                    if not voice_client.is_playing() and not self.player.queue:
                        self.bot.loop.create_task(self.idle_disconnect(ctx))
        except sqlite3.Error as e:
            await ctx.send(f"Error playing the most requested song with a speed change:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(
                self.bot, f"Error playing the most requested song with a speed change: {e}")
        except Exception as e:
            await ctx.send(f"Error playing the most requested song with a speed change:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(
                self.bot, f"Error playing the most requested song with a speed change: {e}")

    @commands.hybrid_command(name="slowplay", help="Plays a song at 0.75x speed.")
    async def slowplay(self, ctx, song: str):
        """Adds a song to the queue and plays at slow 0.75x speed."""
        await self.play_with_speed(ctx, song, 0.75, "slowplay", self.music_volume)

    @commands.hybrid_command(name="fastplay", help="Plays a song at 1.25x speed.")
    async def fastplay(self, ctx, song: str):
        """Adds a song to the queue and plays at fast 1.25x speed."""
        await self.play_with_speed(ctx, song, 1.25, "fastplay", self.music_volume)

    async def play_with_speed(self, ctx, song: str, speed: float, label: str, volume: int):
        """Helper to play songs with different speeds."""
        try:
            voice_client = await self.join_voice_channel(ctx)
            if voice_client is None:
                return

            if len(self.player.queue) >= 100:
                await ctx.send("The queue is full! Maximum queue size is 100 songs.", delete_after=12)
                return

            await ctx.send(f":notes: **Song Requested**\nAdded song at {label} speed to the queue:\n{song}")

            if self.player.is_playing:
                self.player.queue.append((song, speed))
            else:
                self.player.is_playing = True
                await self.player._play_youtube_audio(ctx, voice_client, song, playback_speed=speed, volume=self.music_volume / 100)
                # start the idle disconnect task
                if not voice_client.is_playing() and not self.player.queue:
                    self.bot.loop.create_task(self.idle_disconnect(ctx))
        except Exception as e:
            await ctx.send(f"Error playing {song} at {label} speed:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error playing {song} at {label} speed: {e}")

    @commands.hybrid_command(name="stop", help="Stops the audio and clears the queue.")
    async def stop(self, ctx):
        """Stops the audio, clears the queue, and disconnects."""
        try:
            if ctx.author.voice is None:
                await ctx.send("You need to be in a voice channel to use this command!", delete_after=12)
                return None
            elif ctx.message.channel.id not in self.music_channel_ids:
                await ctx.send("You need type in the music chat to use this command!", delete_after=12)
                return None

            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=ctx.guild)
            if voice_client and voice_client.is_playing():
                await ctx.send("Stopping audio and clearing the queue.", delete_after=12)
                voice_client.stop()
                self.player.queue.clear()
                self.player.is_playing = False
                await self.player.delete_player_embed()

            else:
                await ctx.send("No audio is playing.", delete_after=12)
        except Exception as e:
            await ctx.send(f"Error stopping audio:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error stopping audio: {e}")

    @commands.hybrid_command(name="skip", help="Skips the current song.")
    async def skip(self, ctx):
        """Skips the current song."""
        if ctx.author.voice is None:
            await ctx.send("You need to be in a voice channel to use this command!", delete_after=12)
            return None
        elif ctx.message.channel.id not in self.music_channel_ids:
            await ctx.send("You need to type in the music chat to use this command!", delete_after=12)
            return None

        voice_client = discord.utils.get(
            self.bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_playing():
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()

                try:
                    song_url = self.player.current_song_url

                    # track the skip here
                    cursor.execute(
                        'INSERT INTO user_actions (user_id, user_name, song_title, song_url, action) VALUES (?, ?, ?, ?, ?)',
                        (str(ctx.author.id), ctx.author.display_name,
                         self.player.current_video_info['title'], song_url, 'skip')
                    )
                    conn.commit()

                    await ctx.send("Song skipped.", delete_after=12)

                except sqlite3.Error as e:
                    conn.rollback()  # some rollback if there is an error
                    await ctx.send(f"Error while recording skip:\n `{str(e)}`\n\nReport this to your server admin if you think this is a bug.")
                    log_error(self.bot, f"Error recording skip: {e}")

                voice_client.stop()
                if not voice_client.is_playing() and not self.player.queue:
                    self.bot.loop.create_task(self.idle_disconnect(ctx))
        else:
            await ctx.send("No audio is playing.", delete_after=12)

    @commands.hybrid_command(name="queue", help="Displays the current queue.")
    async def list_queue(self, ctx):
        """Lists the current queue."""
        try:
            if ctx.message.channel.id not in self.music_channel_ids:
                await ctx.send("You need type in the music chat to use this command!", delete_after=12)
                return None

            if self.player.queue:
                queue_list = "\n".join(
                    [f"{i + 1}. [{title}]({url})" for i, (url, title)
                     in enumerate(self.player.queue)]
                )
                queue_list = queue_list.replace("'", "")
                embed = create_embed(
                    "Current Queue", f"Current queue:\n{queue_list}", discord.Color.blue(), self.thumbnail)
                await ctx.send(embed=embed)
            else:
                await ctx.send("The queue is empty.", delete_after=12)
        except Exception as e:
            await ctx.send(f"Error listing the queue:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error listing the queue: {e}")

    @commands.hybrid_command(name="clear", help="Clears the current queue.")
    async def clear_queue(self, ctx):
        """Clears the queue."""
        try:
            if ctx.author.voice is None:
                await ctx.send("You need to be in a voice channel to use this command!", delete_after=12)
                return None
            elif ctx.message.channel.id not in self.music_channel_ids:
                await ctx.send("You need type in the music chat to use this command!", delete_after=12)
                return None

            self.player.queue.clear()
            await ctx.send("Queue cleared.", delete_after=12)
        except Exception as e:
            await ctx.send(f"Error clearing the queue:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error clearing the queue: {e}")

    @commands.hybrid_command(name="volume", help="Sets the volume of the music player.")
    async def set_volume(self, ctx, volume: int or None = None):
        """Sets the volume of the music player."""
        try:
            if ctx.author.voice is None:
                await ctx.send("You need to be in a voice channel to use this command!", delete_after=12)
                return None
            elif ctx.message.channel.id not in self.music_channel_ids:
                await ctx.send("You need type in the music chat to use this command!", delete_after=12)
                return None

            if volume is None:
                embed = create_embed(
                    "Current Volume", f"The current volume is: {self.music_volume}\nUse /volume <0-100> to set the volume.", discord.Color.blue(), self.thumbnail)
                await ctx.send(embed=embed)
            elif volume < 0 or volume > 100:
                embed = create_embed(
                    "Invalid Volume", "Volume must be between 0 and 100.", discord.Color.red(), self.thumbnail)
                await ctx.send(embed=embed)
                return

            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=ctx.guild)

            if voice_client and voice_client.is_playing():
                voice_client.source.volume = volume / 100
                self.music_volume = volume
                update_config(self.bot.config_file, {"music_volume": volume})
                embed = create_embed(
                    "Volume Set", f"Volume set to {volume}", discord.Color.green(), self.thumbnail)
                await ctx.send(embed=embed)
            else:
                await ctx.send("No audio is playing.", delete_after=12)
        except Exception as e:
            await ctx.send(f"Error setting the volume:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error setting the volume: {e}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        message = reaction.message

        if message.id != self.player.player_message.id:
            return

        if reaction.emoji == '▶️':
            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=message.guild)
            if voice_client and not voice_client.is_playing():
                voice_client.resume()

        elif reaction.emoji == '⏸️':
            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=message.guild)
            if voice_client and voice_client.is_playing():
                voice_client.pause()

        elif reaction.emoji == '⏹️':
            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=message.guild)
            if voice_client and voice_client.is_playing():
                try:
                    await message.channel.send("Audio stopped and queue cleared.", delete_after=12)
                    voice_client.stop()
                    self.player.queue.clear()
                    self.player.is_playing = False
                    await self.player.delete_player_embed()
                except Exception as e:
                    await message.channel.send(f"Error stopping audio:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
                    log_error(self.bot, f"Error stopping audio: {e}")

        elif reaction.emoji == '⏮️':
            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=message.guild)

            current_time = time.time()
            cooldowns = {}
            if message.guild.id in self.cooldowns and current_time - self.cooldowns[message.guild.id] < 30:
                remaining_time = 30 - \
                    (current_time - self.cooldowns[message.guild.id])
                await message.channel.send(f"Cooldown active. Please wait {int(remaining_time)} seconds.", delete_after=12)
                return

            try:
                if voice_client and voice_client.is_playing():
                    voice_client.stop()
                    if self.player.queue:
                        song, speed = self.player.queue.pop(0)
                        await self.player._play_youtube_audio(message, voice_client, song, volume=self.music_volume / 100, playback_speed=speed)
                        await message.channel.send(f":notes: **Song Requested**\nPlaying previous song:\n{song} requested by reaction buttons.")

                        self.cooldowns[message.guild.id] = current_time

                    else:
                        self.player.is_playing = False
                        await self.player.delete_player_embed()
                        await message.channel.send("No more songs in the queue.", delete_after=12)
                else:
                    await message.channel.send("No audio is playing.", delete_after=12)
            except Exception as e:
                await message.channel.send(f"Error playing previous song:\n `{e}`\n\nReport this to your server admin if you think this is a bug.")
                log_error(self.bot, f"Error playing previous song: {e}")

        elif reaction.emoji == '⏭️':
            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=message.guild)
            if voice_client and voice_client.is_playing():
                with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                    conn.execute('PRAGMA foreign_keys = ON;')
                    cursor = conn.cursor()

                    try:

                        song_url = self.player.current_song_url

                        # track the skip here
                        cursor.execute(
                            'INSERT INTO user_actions (user_id, user_name, song_title, song_url, action) VALUES (?, ?, ?, ?, ?)',
                            (str(user.id), user.display_name,
                             self.player.current_video_info['title'], song_url, 'skip')
                        )
                        conn.commit()

                    except sqlite3.Error as e:
                        conn.rollback()  # some rollback if there is an error
                        await message.channel.send(f"Error while recording skip:\n `{str(e)}`\n\nReport this to your server admin if you think this is a bug.")
                        log_error(self.bot, f"Error recording skip: {e}")
                    voice_client.stop()

        elif reaction.emoji == '❤️':
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()
                try:
                    song_url = self.player.current_song_url
                    cursor.execute(
                        'INSERT INTO user_actions (user_id, user_name, song_title, song_url, action) VALUES (?, ?, ?, ?, ?)',
                        (str(user.id), user.display_name,
                            self.player.current_video_info['title'], song_url, 'like')
                    )
                    conn.commit()
                    await message.channel.send(f"❤️ **{user.name}** liked the song.", delete_after=8)
                except sqlite3.Error as e:
                    conn.rollback()  # some rollback if there is an error
                    await message.channel.send(f"Error while recording like:\n `{str(e)}`\n\nReport this to your server admin if you think this is a bug.")
                    log_error(self.bot, f"Error recording like: {e}")


async def setup(bot: "Bot"):
    """Loads the cog."""
    try:
        await bot.add_cog(MusicCog(bot))
    except Exception as e:
        log_error(bot, f"Error loading MusicCog: {e}")
