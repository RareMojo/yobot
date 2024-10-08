import discord
import asyncio
import sqlite3
from discord.ext import commands
from cogs.Music.music_manager import MusicManager
from utils.logger import log_debug, log_error
from utils.tools import update_config, create_embed, join_voice_channel, format_time, generate_bar_chart, generate_pie_chart
from datetime import datetime
from random import shuffle


class MusicCog(commands.Cog, name="MusicCog", description="Streams audio from the internet with various effects."):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.music_channel_ids = self.bot.config['music_channel_ids']
        self.thumbnail = 'https://i.imgur.com/tSuXN8P.png'
        self.media_volume = self.bot.config['media_volume'] / 100
        self.request_icon = ':satellite: '
        self.music_manager = MusicManager(self.bot)
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
                CREATE TABLE IF NOT EXISTS music_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    user_name TEXT NOT NULL,
                    media_title TEXT NOT NULL,
                    media_url TEXT NOT NULL,
                    genre TEXT DEFAULT Unknown,
                    playback_speed REAL,
                    duration REAL,
                    action TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_music_actions_guild_action ON music_actions (guild_id, action);')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_music_actions_guild_action_timestamp ON music_actions (guild_id, action, timestamp);')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_music_actions_guild_user ON music_actions (guild_id, user_id);')

            conn.commit()

    @commands.hybrid_command(name="play", help="Plays a song provided by the user. Can be search term or URL.")
    async def play_song(self, ctx, song: str):
        """Plays a song based on the provided song URL or search term."""
        music_player = await self.music_manager.get_player(ctx.guild)
        voice_client = await join_voice_channel(self.bot, ctx, self.music_channel_ids)
        if voice_client is None:
            return

        if len(music_player.queue) >= 100:
            await ctx.send("The queue is full! Maximum queue size is 100 songs.", delete_after=12)
            return None

        await ctx.send(f"{self.request_icon} **Song Requested**\nAdded to the queue:\n{song}")

        if music_player.is_playing:
            await music_player.add_to_queue(ctx, song, 1.0)
        else:
            music_player.is_playing = True
            try:
                await music_player.play_youtube_audio(ctx.channel, voice_client, song, volume=self.media_volume, requester=ctx.author)
            except Exception as e:
                await ctx.send(f"Error playing {song}:\n\nReport this to your server admin if you think this is a bug.")
                log_error(self.bot, f"Error playing {song}: `{str(e)}`")
                music_player.is_playing = False

    # for jonston
    @commands.hybrid_command(name="replay", help="Plays the most recent song played in general.")
    async def replay_song(self, ctx):
        """Plays the most recent song played in the current guild."""
        music_player = await self.music_manager.get_player(ctx.guild)
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT media_title, media_url, playback_speed, user_name
                    FROM music_actions 
                    WHERE action = 'request' AND guild_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''', (ctx.guild.id,))

                recent_song = cursor.fetchone()

                if recent_song is None:
                    await ctx.send("No songs have been requested yet!", delete_after=12)
                    return

                media_title, media_url, playback_speed, user_name = recent_song
                playback_speed = playback_speed or 1.0

                voice_client = await join_voice_channel(self.bot, ctx, self.music_channel_ids)
                if voice_client is None:
                    return

                await ctx.send(f"{self.request_icon} **Song Requested**\nAdded the most recent song to the queue:\n{media_title} requested by {user_name} (at speed {playback_speed}x)")

                if music_player.is_playing:
                    await music_player.add_to_queue(ctx, media_url, playback_speed)
                else:
                    music_player.is_playing = True
                    await music_player.play_youtube_audio(ctx.channel, voice_client, media_url, volume=self.media_volume, playback_speed=playback_speed, requester=ctx.author)
        except sqlite3.Error as e:
            await ctx.send(f"Error playing the most recent song:\n\nReport this to your server admin if you think this is a bug.")
            log_error(
                self.bot, f"Error playing the most recent song: {str(e)}")
            music_player.is_playing = False

    @commands.hybrid_command(name="slowplay", help="Plays a song at 0.75x speed.")
    async def slowplay(self, ctx, song: str):
        """Adds a song to the queue and plays at slow 0.75x speed."""
        await self._play_with_speed(ctx, song, 0.75, "slowplay", self.media_volume)

    @commands.hybrid_command(name="fastplay", help="Plays a song at 1.25x speed.")
    async def fastplay(self, ctx, song: str):
        """Adds a song to the queue and plays at fast 1.25x speed."""
        await self._play_with_speed(ctx, song, 1.25, "fastplay", self.media_volume)

    async def _play_with_speed(self, ctx, song: str, speed: float, label: str, volume: int):
        """Helper to play songs with different speeds."""
        music_player = await self.music_manager.get_player(ctx.guild)
        try:
            voice_client = await join_voice_channel(self.bot, ctx, self.music_channel_ids)
            if voice_client is None:
                return

            if len(music_player.queue) >= 100:
                await ctx.send("The queue is full! Maximum queue size is 100 songs.", delete_after=12)
                return

            await ctx.send(f"{self.request_icon} **Song Requested**\nAdded song at {label} speed to the queue:\n{song}")

            if music_player.is_playing:
                await music_player.add_to_queue(ctx, song, speed)
            else:
                music_player.is_playing = True
                await music_player.play_youtube_audio(ctx.channel, voice_client, song, playback_speed=speed, volume=self.media_volume, requester=ctx.author)
        except Exception as e:
            await ctx.send(f"Error playing {song} at {label} speed:\n\nReport this to your server admin if you think this is a bug.")
            log_error(
                self.bot, f"Error playing {song} at {label} speed: {str(e)}")
            music_player.is_playing = False

    @commands.hybrid_command(name="stop", help="Stops the audio and clears the queue.")
    async def stop(self, ctx):
        """Stops the audio, clears the queue, and disconnects."""
        music_player = await self.music_manager.get_player(ctx.guild)
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
                music_player.queue.clear()
                await music_player.stop_playing()

            else:
                await ctx.send("No audio is playing.", delete_after=12)
        except Exception as e:
            await ctx.send(f"Error stopping audio:\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error stopping audio: {str(e)}")
            music_player.is_playing = False

    @commands.hybrid_command(name="skip", help="Skips the current song.")
    async def skip(self, ctx):
        """Skips the current song."""
        music_player = await self.music_manager.get_player(ctx.guild)
        if ctx.author.voice is None:
            await ctx.send("You need to be in a voice channel to use this command!", delete_after=12)
            return
        elif ctx.message.channel.id not in self.music_channel_ids:
            await ctx.send("You need to type in the music chat to use this command!", delete_after=12)
            return

        voice_client = discord.utils.get(
            self.bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_playing():
            try:
                with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                    conn.execute('PRAGMA foreign_keys = ON;')
                    cursor = conn.cursor()
                    media_url = music_player.current_media_url
                    genre = "Unknown"
                    if music_player.current_video_info.get('genre'):
                        genre = genre[0]

                    cursor.execute('''
                        INSERT INTO music_actions (
                            guild_id,
                            user_id,
                            user_name,
                            media_title,
                            media_url,
                            genre,
                            playback_speed,
                            duration,
                            action
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'skip')
                    ''', (
                        ctx.guild.id,
                        ctx.author.id,
                        ctx.author.display_name,
                        music_player.current_video_info['title'],
                        media_url,
                        genre,
                        music_player.current_playback_speed,
                        music_player.current_video_info['duration']
                    ))

                    conn.commit()

            except sqlite3.Error as e:
                conn.rollback()
                await ctx.send(f"Error while recording skip.")
                log_error(self.bot, f"Error recording skip: {str(e)}")
            except Exception as e:
                await ctx.send(f"Error skipping song.\n\nReport this to your server admin if you think this is a bug.")
                log_error(self.bot, f"Error skipping song: {str(e)}")

            voice_client.stop()
            await music_player.stop_playing()
            await ctx.send("Skipping song.", delete_after=12)

        else:
            await ctx.send("No audio is playing.", delete_after=12)

    @commands.hybrid_command(name="queue", help="Displays the current queue.")
    async def list_queue(self, ctx):
        """Lists the current queue."""
        music_player = await self.music_manager.get_player(ctx.guild)

        if music_player.queue.is_empty():
            await ctx.send("The queue is empty.", delete_after=12)
            return

        queue_list = ""
        for index, song in enumerate(music_player.queue._queue):
            queue_list += f"{index + 1}. [{song.title}]({song.url}) requested by {song.requester.display_name}\n"

        embed = create_embed(
            "Current Queue", f"Current queue:\n{queue_list}", discord.Color.blue(), self.thumbnail)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="clear", help="Clears the current queue.")
    async def clear_queue(self, ctx):
        """Clears the queue."""
        music_player = await self.music_manager.get_player(ctx.guild)
        try:
            if ctx.author.voice is None:
                await ctx.send("You need to be in a voice channel to use this command!", delete_after=12)
                return None
            elif ctx.message.channel.id not in self.music_channel_ids:
                await ctx.send("You need type in the music chat to use this command!", delete_after=12)
                return None

            music_player.queue.clear()
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
                    "Current Volume", f"The current volume is: {self.media_volume}\nUse /volume <0-100> to set the volume.", discord.Color.blue(), self.thumbnail)
                await ctx.send(embed=embed)
            elif volume < 0 or volume > 100:
                embed = create_embed(
                    "Invalid Volume", "Volume must be between 0 and 100.", discord.Color.red(), self.thumbnail)
                await ctx.send(embed=embed)
                return

            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=ctx.guild)

            if voice_client and voice_client.is_playing():
                voice_client.source.volume = volume
                self.media_volume = volume
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
        guild = message.guild

        music_player = await self.music_manager.get_player(guild)

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
                    music_player.queue.clear()
                    await music_player.stop_playing()
                except Exception as e:
                    await message.channel.send(f"Error stopping audio.\n\nReport this to your server admin if you think this is a bug.")
                    log_error(self.bot, f"Error stopping audio: {str(e)}")

        # for jonston
        elif reaction.emoji == '⏮️':
            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=message.guild)
            if user.voice is None:
                await message.channel.send("You need to be in a voice channel to use this command!", delete_after=12)
                return
            try:
                if music_player.current_media_url:
                    await music_player.add_to_queue(guild, music_player.current_media_url, music_player.current_playback_speed)
                    await message.channel.send("Previous song will be played again.", delete_after=12)
                else:
                    await message.channel.send("No previous song to play.", delete_after=12)
            except Exception as e:
                await message.channel.send(f"Error playing previous song.\n\nReport this to your server admin if you think this is a bug.")
                log_error(self.bot, f"Error playing previous song: {str(e)}")

        elif reaction.emoji == '⏭️':
            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=message.guild)

            if user.voice is None:
                await message.channel.send("You need to be in a voice channel to use this command!", delete_after=12)
                return
            try:
                with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                    conn.execute('PRAGMA foreign_keys = ON;')
                    cursor = conn.cursor()
                    media_url = music_player.current_media_url
                    genre = "Unknown"
                    if music_player.current_video_info.get('genre'):
                        genre = genre[0]

                    cursor.execute('''
                        INSERT INTO music_actions (
                            guild_id,
                            user_id,
                            user_name,
                            media_title,
                            media_url,
                            genre,
                            playback_speed,
                            duration,
                            action
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'skip')
                    ''', (
                        message.guild.id,
                        user.id,
                        user.display_name,
                        music_player.current_video_info['title'],
                        media_url,
                        genre,
                        music_player.current_playback_speed,
                        music_player.current_video_info['duration']
                    ))

                    conn.commit()

            except sqlite3.Error as e:
                conn.rollback()
                await message.channel.send(f"Error while recording skip.")
                log_error(self.bot, f"Error recording skip: {str(e)}")
            except Exception as e:
                await message.channel.send(f"Error skipping song.\n\nReport this to your server admin if you think this is a bug.")
                log_error(self.bot, f"Error skipping song: {str(e)}")

            voice_client.stop()
            await message.channel.send("Skipping song.", delete_after=12)

        elif reaction.emoji == '❤️':
            try:
                with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                    conn.execute('PRAGMA foreign_keys = ON;')
                    cursor = conn.cursor()
                    media_url = music_player.current_media_url
                    genre = "Unknown"
                    if music_player.current_video_info.get('genre'):
                        genre = genre[0]

                    cursor.execute('''
                        INSERT INTO music_actions (
                            guild_id,
                            user_id,
                            user_name,
                            media_title,
                            media_url,
                            genre,
                            playback_speed,
                            duration,
                            action
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'like')
                    ''', (
                        message.guild.id,
                        user.id,
                        user.display_name,
                        music_player.current_video_info['title'],
                        media_url,
                        genre,
                        music_player.current_playback_speed,
                        music_player.current_video_info['duration']
                    ))

                    conn.commit()
                    await message.channel.send(f"❤️ **{user.name}** liked the song.", delete_after=12)
            except sqlite3.Error as e:
                conn.rollback()
                await message.channel.send(f"Error while recording like:\n `{str(e)}`")
                log_error(self.bot, f"Error recording like: {str(e)}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # fallback for cached messages
        if payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        music_player = await self.music_manager.get_player(guild)

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return
        except discord.Forbidden:
            return
        except discord.HTTPException:
            return

        user = guild.get_member(payload.user_id)
        if not user:
            return

        reaction = discord.Reaction(
            message=message, emoji=payload.emoji, data=payload)

        # resend the reaction event to the on_reaction_add listener
        await self.on_reaction_add(reaction, user)

    async def _play_recent_song(self, ctx, user: discord.User = None):
        """Handles playing the most recent song requested by the user or another user."""
        music_player = await self.music_manager.get_player(ctx.guild)
        try:
            if user is None:
                user = ctx.author

            user_id = str(user.id)

            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT media_title, media_url, playback_speed
                    FROM music_actions 
                    WHERE user_id = ? AND action = 'request' AND guild_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''', (user_id, ctx.guild.id))

                recent_song = cursor.fetchone()

                if recent_song is None:
                    await ctx.send(f"{user.mention} hasn't requested any songs yet!", delete_after=12)
                    return

                media_title, media_url, playback_speed = recent_song
                playback_speed = playback_speed or 1.0

                voice_client = await join_voice_channel(self.bot, ctx, self.music_channel_ids)
                if voice_client is None:
                    return

                await ctx.send(f"{self.request_icon} **Song Requested**\nAdded {user.mention}'s most recent song to the queue:\n{media_title} (at speed {playback_speed}x)")

                if music_player.is_playing:
                    music_player.queue.append((media_url, playback_speed))
                else:
                    music_player.is_playing = True
                    await music_player.play_youtube_audio(ctx.channel, voice_client, media_url, self.media_volume, playback_speed, user)
        except sqlite3.Error as e:
            await ctx.send(f"Error playing the most recent song.")
            log_error(
                self.bot, f"Error playing the most recent song: {str(e)}")
            music_player.is_playing = False

    @commands.hybrid_command(name="musicstats", help="request/like/skip/duration | all/today/week/month | song/hour/day | bar/pie")
    async def music_stats(self, ctx, stat_type: str = "request", timeframe: str = "all", user: discord.Member = None, chart: str = None, group: str = "song"):
        valid_stat_types = ['request', 'like', 'skip', 'duration']
        valid_timeframes = ['all', 'today', 'week', 'month']
        valid_charts = ['bar', 'pie', None]
        valid_group = ['song', 'hour', 'day']

        if stat_type not in valid_stat_types:
            await ctx.send(f"**Error**\nInvalid stat_type: {stat_type}.\nValid options are: request, like, skip, duration.", delete_after=12)
            return

        if timeframe not in valid_timeframes:
            await ctx.send(f"**Error**\nInvalid timeframe: {timeframe}.\nValid options are: all, today, week, month.", delete_after=12)
            return

        if chart not in valid_charts:
            await ctx.send(f"**Error**\nInvalid chart type: {chart}.\nValid options are: bar, pie.", delete_after=12)
            return

        if group not in valid_group:
            await ctx.send(f"**Error**\nInvalid group: {group}.\nValid options are: song, hour, day.", delete_after=12)
            return

        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                if stat_type == "duration":
                    await self._calculate_total_listening_time(ctx, cursor, timeframe, user)
                    return

                params = [stat_type, ctx.guild.id]

                if group == 'song':
                    select_clause = "SELECT media_title, media_url, COUNT(*) as count"
                    group_clause = "GROUP BY media_title, media_url"
                elif group == 'hour':
                    select_clause = "SELECT strftime('%H', timestamp) as hour, COUNT(*) as count"
                    group_clause = "GROUP BY hour"
                elif group == 'day':
                    select_clause = "SELECT strftime('%w', timestamp) as day_of_week, COUNT(*) as count"
                    group_clause = "GROUP BY day_of_week"

                query = f"{select_clause} FROM music_actions WHERE action = ? AND guild_id = ?"

                if timeframe == "today":
                    query += " AND DATE(timestamp) = DATE('now')"
                elif timeframe == "week":
                    query += " AND timestamp >= DATE('now', '-7 days')"
                elif timeframe == "month":
                    query += " AND timestamp >= DATE('now', '-30 days')"

                if user:
                    query += " AND user_id = ?"
                    params.append(str(user.id))

                query += f" {group_clause} ORDER BY count DESC LIMIT 5"

                cursor.execute(query, params)
                data = cursor.fetchall()

                if data:
                    if chart == "bar":
                        title = f"Top {stat_type}s by {group} ({timeframe})"
                        xlabel = group.title()
                        ylabel = f"Number of {stat_type}s"
                        await generate_bar_chart(ctx, data, title=title, xlabel=xlabel, ylabel=ylabel, group=group)
                    elif chart == "pie":
                        title = f"Top {stat_type}s by {group} ({timeframe})"
                        await generate_pie_chart(ctx, data, title=title, group=group)
                    else:
                        message = f"**Top {stat_type}s by {group} ({timeframe}):**\n"
                        for i, row in enumerate(data, start=1):
                            if group == 'song':
                                media_title, media_url, count = row
                                message += f"{i}. [{media_title}](<{media_url}>): {count} {stat_type}s\n"
                            elif group == 'hour':
                                hour, count = row
                                message += f"{i}. Hour {hour}: {count} {stat_type}s\n"
                            elif group == 'day':
                                day_of_week, count = row
                                day_name = ['Sunday', 'Monday', 'Tuesday', 'Wednesday',
                                            'Thursday', 'Friday', 'Saturday'][int(day_of_week)]
                                message += f"{i}. {day_name}: {count} {stat_type}s\n"
                        await ctx.send(message)
                else:
                    await ctx.send("No data available for the selected filters.", delete_after=12)
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}")

    async def _calculate_total_listening_time(self, ctx, cursor, timeframe, user):
        """
        Calculates the total listening time, both globally and per user.
        """
        query = "SELECT SUM(playback_speed * duration) as total_time FROM music_actions WHERE action = 'request' AND guild_id = ?"
        params = [ctx.guild.id]

        if timeframe == "today":
            query += " AND DATE(timestamp) = DATE('now')"
        elif timeframe == "week":
            query += " AND timestamp >= DATE('now', '-7 days')"
        elif timeframe == "month":
            query += " AND timestamp >= DATE('now', '-30 days')"

        if user:
            query += " AND user_id = ?"
            params.append(str(user.id))

        cursor.execute(query, params)
        result = cursor.fetchone()

        if result and result[0]:
            total_seconds = result[0]
            total_time = format_time(total_seconds)
            user_message = f"Total listening time for {user.display_name}: **{total_time}**" if user else f"Total listening time: **{total_time}**"
            await ctx.send(user_message)
        else:
            await ctx.send("No data available for the selected filters.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handles the event when a member's voice state updates."""
        if member == self.bot.user:
            if before.channel and not after.channel:
                guild = before.channel.guild
                music_player = await self.bot.music_manager.get_player(guild)
                await music_player.stop_playing()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Handles the event when the bot is removed from a guild."""
        await self.bot.music_manager.cleanup_player(guild.id)


async def setup(bot: commands.Bot):
    """Loads the cog."""
    try:
        await bot.add_cog(MusicCog(bot))
    except Exception as e:
        log_error(bot, f"Error loading MusicCog: {str(e)}")
