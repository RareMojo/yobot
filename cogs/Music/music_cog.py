import discord
import asyncio
import sqlite3
from discord.ext import commands
from cogs.Music.music_player import MusicPlayer
from utils.logger import log_debug, log_error
from utils.tools import update_config, create_embed, join_voice_channel
from datetime import datetime
from random import shuffle


class MusicCog(commands.Cog, name="MusicCog", description="Streams audio from the internet with various effects."):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.music_channel_ids = self.bot.config['music_channel_ids']
        self.thumbnail = 'https://i.imgur.com/tSuXN8P.png'
        self.music_volume = self.bot.config['music_volume']
        self.player = MusicPlayer(bot, [], None, None)
        self._initialize_music_db()
        log_debug(bot, "MusicCog initialized.")

    def _initialize_music_db(self):
        """Initialize the SQLite database and create the required tables."""
        with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
            cursor = conn.cursor()

            # idk some foreign key support
            cursor.execute('PRAGMA foreign_keys = ON;')

            # music tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    user_name TEXT NOT NULL,
                    song_title TEXT NOT NULL,
                    song_url TEXT NOT NULL,
                    genre TEXT NOT NULL,
                    playback_speed REAL,
                    duration REAL,
                    action TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_user_actions_guild_action ON user_actions (guild_id, action);')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_user_actions_guild_action_timestamp ON user_actions (guild_id, action, timestamp);')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_user_actions_guild_user ON user_actions (guild_id, user_id);')

            conn.commit()

    @commands.hybrid_command(name="play", help="Plays a song provided by the user. Can be search term or URL.")
    async def play_song(self, ctx, song: str):
        """Plays a song based on the provided song URL or search term."""

        voice_client = await join_voice_channel(self.bot, ctx, self.music_channel_ids)
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
                await self.player.play_youtube_audio(ctx, voice_client, song, volume=self.music_volume / 100)
                if not voice_client.is_playing() and not self.player.queue:
                    self.bot.loop.create_task(idle_disconnect(self.bot, ctx, self.player))
            except Exception as e:
                await ctx.send(f"Error playing {song}:\n\nReport this to your server admin if you think this is a bug.")
                log_error(self.bot, f"Error playing {song}: `{str(e)}`")
                self.player.is_playing = False

    @commands.hybrid_command(name="playdb", help="Plays a song from the database options such as recent, top, topspeed, favorite, topliked.")
    async def play_db_song(self, ctx, option: str, user: discord.User = None):
        """Plays a song based on database queries for recent, top, topspeed, favorite, or topliked songs."""

        if option != "favorite" and user is not None:
            await ctx.send("You can only specify a user when using the 'favorite' option.", delete_after=12)
            return

        voice_client = await join_voice_channel(self.bot, ctx, self.music_channel_ids)
        if voice_client is None:
            return

        if option == "recent":
            await self._play_recent_song(ctx)
        elif option == "top":
            await self._play_top_song(ctx)
        elif option == "topspeed":
            await self._play_top_speed_song(ctx)
        elif option == "favorite":
            await self._play_favorite_song(ctx, user)
        elif option == "topliked":
            await self._play_top_liked_song(ctx)
        else:
            await ctx.send("Invalid option provided. Use one of (recent, top, topspeed, favorite, topliked).", delete_after=12)

    @commands.hybrid_command(name="replay", help="Plays the most recent song played in general.")
    async def replay_song(self, ctx):
        """Plays the most recent song played in the current guild."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, playback_speed, user_name
                    FROM user_actions 
                    WHERE action = 'request' AND guild_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''', (ctx.guild.id,))

                recent_song = cursor.fetchone()

                if recent_song is None:
                    await ctx.send("No songs have been requested yet!", delete_after=12)
                    return

                song_title, song_url, playback_speed, user_name = recent_song
                playback_speed = playback_speed or 1.0

                voice_client = await join_voice_channel(self.bot, ctx, self.music_channel_ids)
                if voice_client is None:
                    return

                await ctx.send(f":notes: **Song Requested**\nAdded the most recent song to the queue:\n{song_title} requested by {user_name} (at speed {playback_speed}x)")

                if self.player.is_playing:
                    self.player.queue.append((song_url, playback_speed))
                else:
                    self.player.is_playing = True
                    await self.player.play_youtube_audio(ctx, voice_client, song_url, volume=self.music_volume / 100, playback_speed=playback_speed)
                    if not voice_client.is_playing() and not self.player.queue:
                        self.bot.loop.create_task(
                            idle_disconnect(self.bot, ctx, self.player))
        except sqlite3.Error as e:
            await ctx.send(f"Error playing the most recent song:\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error playing the most recent song: {str(e)}")
            self.player.is_playing = False

    @commands.hybrid_command(name="slowplay", help="Plays a song at 0.75x speed.")
    async def slowplay(self, ctx, song: str):
        """Adds a song to the queue and plays at slow 0.75x speed."""
        await self._play_with_speed(ctx, song, 0.75, "slowplay", self.music_volume)

    @commands.hybrid_command(name="fastplay", help="Plays a song at 1.25x speed.")
    async def fastplay(self, ctx, song: str):
        """Adds a song to the queue and plays at fast 1.25x speed."""
        await self._play_with_speed(ctx, song, 1.25, "fastplay", self.music_volume)

    async def _play_with_speed(self, ctx, song: str, speed: float, label: str, volume: int):
        """Helper to play songs with different speeds."""
        try:
            voice_client = await join_voice_channel(self.bot, ctx, self.music_channel_ids)
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
                await self.player.play_youtube_audio(ctx, voice_client, song, playback_speed=speed, volume=self.music_volume / 100)
                # start the idle disconnect task
                if not voice_client.is_playing() and not self.player.queue:
                    self.bot.loop.create_task(idle_disconnect(self.bot, ctx, self.player))
        except Exception as e:
            await ctx.send(f"Error playing {song} at {label} speed:\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error playing {song} at {label} speed: {str(e)}")
            self.player.is_playing = False

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
                await self.player.stop_playing()

            else:
                await ctx.send("No audio is playing.", delete_after=12)
        except Exception as e:
            await ctx.send(f"Error stopping audio:\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error stopping audio: {str(e)}")
            self.player.is_playing = False

    @commands.hybrid_command(name="skip", help="Skips the current song.")
    async def skip(self, ctx):
        """Skips the current song."""
        if ctx.author.voice is None:
            await ctx.send("You need to be in a voice channel to use this command!", delete_after=12)
            return
        elif ctx.message.channel.id not in self.music_channel_ids:
            await ctx.send("You need to type in the music chat to use this command!", delete_after=12)
            return

        voice_client = discord.utils.get(
            self.bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_playing():
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()

                try:
                    song_url = self.player.current_song_url

                    # Track the skip here
                    cursor.execute(
                        'INSERT INTO user_actions (guild_id, user_id, user_name, song_title, song_url, action) VALUES (?, ?, ?, ?, ?, ?)',
                        (ctx.guild.id, ctx.author.id, ctx.author.display_name,
                         self.player.current_video_info['title'], song_url, 'skip')
                    )
                    conn.commit()

                    await ctx.send("Song skipped.", delete_after=12)

                except sqlite3.Error as e:
                    conn.rollback()
                    await ctx.send(f"Error while recording skip.")
                    log_error(self.bot, f"Error recording skip: {str(e)}")

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
            await ctx.send(f"Error listing the queue:\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error listing the queue: {str(e)}")

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
            await ctx.send(f"Error clearing the queue:\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error clearing the queue: {str(e)}")

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
            await ctx.send(f"Error setting the volume:\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error setting the volume: {str(e)}")

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
                    await self.player.stop_playing()
                except Exception as e:
                    await message.channel.send(f"Error stopping audio.\n\nReport this to your server admin if you think this is a bug.")
                    log_error(self.bot, f"Error stopping audio: {str(e)}")

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
                        await self.player.play_youtube_audio(message, voice_client, song, volume=self.music_volume / 100, playback_speed=speed)
                        await message.channel.send(f":notes: **Song Requested**\nPlaying previous song:\n{song} requested by reaction buttons.")

                        self.cooldowns[message.guild.id] = current_time

                    else:
                        await self.player.stop_playing()
                        await message.channel.send("No more songs in the queue.", delete_after=12)
                else:
                    await message.channel.send("No audio is playing.", delete_after=12)
            except Exception as e:
                await message.channel.send(f"Error playing previous song.\n\nReport this to your server admin if you think this is a bug.")
                log_error(self.bot, f"Error playing previous song: {str(e)}")

        elif reaction.emoji == '⏭️':
            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=message.guild)
            if voice_client and voice_client.is_playing():
                with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                    conn.execute('PRAGMA foreign_keys = ON;')
                    cursor = conn.cursor()

                    try:
                        song_url = self.player.current_song_url

                        # Track the skip here
                        cursor.execute(
                            'INSERT INTO user_actions (guild_id, user_id, user_name, song_title, song_url, action) VALUES (?, ?, ?, ?, ?, ?)',
                            message.guild.id, user.id, user.display_name,
                             self.player.current_video_info['title'], song_url, 'skip')

                        conn.commit()

                    except sqlite3.Error as e:
                        conn.rollback()
                        await message.channel.send(f"Error while recording skip.")
                        log_error(self.bot, f"Error recording skip: {str(e)}")
                    voice_client.stop()

        elif reaction.emoji == '❤️':
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                conn.execute('PRAGMA foreign_keys = ON;')
                cursor = conn.cursor()
                try:
                    song_url = self.player.current_song_url
                    cursor.execute(
                        'INSERT INTO user_actions (guild_id, user_id, user_name, song_title, song_url, action) VALUES (?, ?, ?, ?, ?, ?)',
                        message.guild.id, user.id, user.display_name,
                         self.player.current_video_info['title'], song_url, 'like')

                    conn.commit()
                    await message.channel.send(f"❤️ **{user.name}** liked the song.", delete_after=8)
                except sqlite3.Error as e:
                    conn.rollback()
                    await message.channel.send(f"Error while recording like:\n `{str(e)}`")
                    log_error(self.bot, f"Error recording like: {str(e)}")

    async def _play_recent_song(self, ctx, user: discord.User = None):
        """Handles playing the most recent song requested by the user or another user."""
        try:
            if user is None:
                user = ctx.author

            user_id = str(user.id)

            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, playback_speed
                    FROM user_actions 
                    WHERE user_id = ? AND action = 'request' AND guild_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''', (user_id, ctx.guild.id))

                recent_song = cursor.fetchone()

                if recent_song is None:
                    await ctx.send(f"{user.mention} hasn't requested any songs yet!", delete_after=12)
                    return

                song_title, song_url, playback_speed = recent_song
                playback_speed = playback_speed or 1.0

                voice_client = await join_voice_channel(self.bot, ctx, self.music_channel_ids)
                if voice_client is None:
                    return

                await ctx.send(f":notes: **Song Requested**\nAdded {user.mention}'s most recent song to the queue:\n{song_title} (at speed {playback_speed}x)")

                if self.player.is_playing:
                    self.player.queue.append((song_url, playback_speed))
                else:
                    self.player.is_playing = True
                    await self.player.play_youtube_audio(ctx, voice_client, song_url, volume=self.music_volume / 100, playback_speed=playback_speed)
                    if not voice_client.is_playing() and not self.player.queue:
                        self.bot.loop.create_task(
                            self.idle_disconnect(ctx))
        except sqlite3.Error as e:
            await ctx.send(f"Error playing the most recent song.")
            log_error(self.bot, f"Error playing the most recent song: {str(e)}")
            self.player.is_playing = False

    async def _play_top_song(self, ctx):
        """Handles playing the most requested song in the current guild."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, COUNT(*) as request_count 
                    FROM user_actions 
                    WHERE action = 'request' AND guild_id = ?
                    GROUP BY song_title, song_url 
                    ORDER BY request_count DESC 
                    LIMIT 1
                ''', (ctx.guild.id,))
                top_song = cursor.fetchone()

                if top_song is None:
                    await ctx.send("No songs have been requested yet.", delete_after=12)
                    return

                song_title, song_url, _ = top_song

                voice_client = await join_voice_channel(self.bot, ctx, self.music_channel_ids)
                if voice_client is None:
                    return

                await ctx.send(f":notes: **Song Requested**\nAdded the most requested song to the queue:\n{song_title}")

                if self.player.is_playing:
                    self.player.queue.append((song_url, 1.0))
                else:
                    self.player.is_playing = True
                    await self.player.play_youtube_audio(ctx, voice_client, song_url, volume=self.music_volume / 100)
                    if not voice_client.is_playing() and not self.player.queue:
                        self.bot.loop.create_task(
                            self.idle_disconnect(ctx))
        except sqlite3.Error as e:
            await ctx.send(f"Error playing the most requested song.")
            log_error(self.bot, f"Error playing the most requested song: {str(e)}")
            self.player.is_playing = False

    async def _play_top_liked_song(self, ctx):
        """Handles playing the most liked song in the current guild."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, COUNT(*) as like_count 
                    FROM user_actions 
                    WHERE action = 'like' AND guild_id = ?
                    GROUP BY song_title, song_url 
                    ORDER BY like_count DESC 
                    LIMIT 1
                ''', (ctx.guild.id,))
                top_liked_song = cursor.fetchone()

                if top_liked_song is None:
                    await ctx.send("No songs have been liked yet.", delete_after=12)
                    return

                song_title, song_url, _ = top_liked_song

                voice_client = await join_voice_channel(self.bot, ctx, self.music_channel_ids)
                if voice_client is None:
                    return

                await ctx.send(f":notes: **Song Requested**\nAdded the most liked song to the queue:\n{song_title}")

                if self.player.is_playing:
                    self.player.queue.append((song_url, 1.0))
                else:
                    self.player.is_playing = True
                    await self.player.play_youtube_audio(ctx, voice_client, song_url, volume=self.music_volume / 100)
                    if not voice_client.is_playing() and not self.player.queue:
                        self.bot.loop.create_task(
                            self.idle_disconnect(ctx))
        except sqlite3.Error as e:
            await ctx.send(f"Error playing the most liked song.")
            log_error(self.bot, f"Error playing the most liked song: {str(e)}")
            self.player.is_playing = False

    async def _play_favorite_song(self, ctx, user: discord.User = None):
        """Handles playing the user's or another specified user's favorite song in the current guild."""
        try:
            if user is None:
                user = ctx.author

            user_id = str(user.id)

            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, playback_speed, COUNT(*) as request_count
                    FROM user_actions 
                    WHERE user_id = ? AND action = 'request' AND guild_id = ?
                    GROUP BY song_title, song_url, playback_speed
                    ORDER BY request_count DESC 
                    LIMIT 1
                ''', (user_id, ctx.guild.id))

                favorite_song = cursor.fetchone()

                if favorite_song is None:
                    await ctx.send(f"{user.mention} hasn't requested any songs yet!", delete_after=12)
                    return

                song_title, song_url, playback_speed, request_count = favorite_song
                playback_speed = playback_speed or 1.0

                voice_client = await join_voice_channel(self.bot, ctx, self.music_channel_ids)
                if voice_client is None:
                    return

                await ctx.send(f":notes: **Song Requested**\nAdded {user.mention}'s favorite song to the queue:\n{song_title} (Requested {request_count} times at speed {playback_speed}x)")

                if self.player.is_playing:
                    self.player.queue.append((song_url, playback_speed))
                else:
                    self.player.is_playing = True
                    await self.player.play_youtube_audio(ctx, voice_client, song_url, volume=self.music_volume / 100, playback_speed=playback_speed)
                    if not voice_client.is_playing() and not self.player.queue:
                        self.bot.loop.create_task(
                            self.idle_disconnect(ctx))
        except sqlite3.Error as e:
            await ctx.send(f"Error playing the favorite song.")
            log_error(self.bot, f"Error playing the favorite song: {str(e)}")
            self.player.is_playing = False

    async def _play_top_speed_song(self, ctx):
        """Handles playing the most requested song with a speed change in the current guild."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, playback_speed, COUNT(*) as request_count 
                    FROM user_actions 
                    WHERE action = 'request' AND playback_speed != 1.0 AND guild_id = ?
                    GROUP BY song_title, song_url, playback_speed 
                    ORDER BY request_count DESC 
                    LIMIT 1
                ''', (ctx.guild.id,))
                top_speed_song = cursor.fetchone()

                if top_speed_song is None:
                    await ctx.send("No songs with speed changes have been requested yet.", delete_after=12)
                    return

                song_title, song_url, playback_speed, _ = top_speed_song

                voice_client = await join_voice_channel(self.bot, ctx, self.music_channel_ids)
                if voice_client is None:
                    return

                await ctx.send(f":notes: **Song Requested**\nAdded song with the most speed changes to queue:\n{song_title} at speed {playback_speed}x")

                if self.player.is_playing:
                    self.player.queue.append((song_url, playback_speed))
                else:
                    self.player.is_playing = True
                    await self.player.play_youtube_audio(ctx, voice_client, song_url, volume=self.music_volume / 100, playback_speed=playback_speed)
                    if not voice_client.is_playing() and not self.player.queue:
                        self.bot.loop.create_task(
                            self.idle_disconnect(ctx))
        except sqlite3.Error as e:
            await ctx.send(f"Error playing the most requested song with a speed change.`")
            log_error(
                self.bot, f"Error playing the most requested song with a speed change: {str(e)}")
            self.player.is_playing = False


    async def idle_disconnect(self, ctx):
        """
        Disconnects the bot after a period of inactivity.
        Args:
            bot (Bot): The bot instance.
            ctx (Context): The Discord context.
            player (Player): The player reponsible for audio.
        Returns:
            None
        Examples:
            >>> await idle_disconnect(bot, ctx, player)
        """
        for _ in range(30):
            voice_client = discord.utils.get(
                bot.voice_clients, guild=ctx.guild)
            if voice_client is None or voice_client.is_playing() or self.player.queue:
                return
            await asyncio.sleep(10)

        voice_client = discord.utils.get(
            self.bot.voice_clients, guild=ctx.guild)
        if voice_client and not voice_client.is_playing():
            try:
                await ctx.send("I haven't played anything in awhile.\nI'll leave for now, use one of the play commands to bring me back!", delete_after=12)
                await voice_client.disconnect()
            except Exception as e:
                log_error(bot, f"Error disconnecting from voice: {str(e)}")


async def setup(bot: commands.Bot):
    """Loads the cog."""
    try:
        await bot.add_cog(MusicCog(bot))
    except Exception as e:
        log_error(bot, f"Error loading MusicCog: {str(e)}")
