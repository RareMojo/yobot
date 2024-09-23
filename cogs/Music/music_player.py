import discord
import sqlite3
import yt_dlp
import asyncio
import time
import re
import os
import sys
from discord.ext import commands, tasks
from utils.tools import format_time, generate_progress_bar
from utils.logger import log_error, log_debug


class MusicPlayer:
    def __init__(self, bot, guild, manager):
        self.bot = bot
        self.guild = guild
        self.manager = manager
        self.queue = []
        self.current_video_info = None
        self.player_message = None
        self.is_playing = False
        self.current_media_url = None
        self.max_media_duration = self.bot.config['max_media_duration']
        self.player_icon = ':notes: '
        if sys.platform == 'win32':
            self.ffmpeg_path = 'ffmpeg.exe'
        elif sys.platform == 'linux':
            self.ffmpeg_path = 'ffmpeg'
        self.disconnect_timer = None
        self.inactivity_duration = self.bot.config['inactivity_duration']

    async def create_player_embed(self, channel, url, title, playback_speed=1.0, thumbnail='https://i.imgur.com/tSuXN8P.png', requester=None):
        """Creates or updates the player embed."""
        if playback_speed > 1.0:
            player_title = f"{self.player_icon} Fast Playing"
        elif playback_speed < 1.0:
            player_title = f"{self.player_icon} Slow Playing"
        else:
            player_title = f"{self.player_icon} Now Playing"
        embed = discord.Embed(
            title=player_title,
            description=f"[{title}]({url})",
            color=discord.Color.blurple()
        )
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        else:
            embed.set_thumbnail(url="https://i.imgur.com/tSuXN8P.png")

        if len(self.queue) > 0:
            next_url, _ = self.queue[0]
            next_song_field = f"[Next Song]({next_url})"
            embed.add_field(
                name="Up Next", value=next_song_field, inline=False)

        embed.add_field(name="Progress",
                        value="[00:00] ▰▰▰▱▱▱▱▱▱▱ 00:00", inline=False)
        embed.set_footer(
            text=f"Requested by {requester.display_name}" if requester else "Requested by someone")

        if self.player_message:
            try:
                await self.player_message.edit(embed=embed)
            except discord.NotFound:
                self.player_message = await channel.send(embed=embed)
        else:
            self.player_message = await channel.send(embed=embed)

        reactions = ['⏮️', '▶️', '⏸️', '⏹️', '⏭️', '❤️']
        for reaction in reactions:
            try:
                await self.player_message.add_reaction(reaction)
            except discord.Forbidden:
                log_error(
                    self.bot, f"Missing permissions to add reactions in {channel.name}")
                break

        await self.cancel_disconnect_timer()

    async def update_progress_bar(self, voice_client, video_info, playback_speed=1.0, requester=None, thumbnail=None):
        """Updates the progress bar as the song plays."""
        duration = video_info['duration'] / playback_speed
        title, url = video_info['title'], video_info['webpage_url']
        start_time = time.time()
        if playback_speed > 1.0:
            player_title = f"{self.player_icon} Fast Playing"
        elif playback_speed < 1.0:
            player_title = f"{self.player_icon} Slow Playing"
        else:
            player_title = f"{self.player_icon} Now Playing"
        while voice_client.is_playing():
            elapsed_time = time.time() - start_time
            progress_percentage = min(elapsed_time / duration, 1.0)
            progress_bar = generate_progress_bar(progress_percentage)

            embed = discord.Embed(
                title=player_title,
                description=f"[{title}]({url})",
                color=discord.Color.blurple()
            )
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
            else:
                embed.set_thumbnail(url="https://i.imgur.com/tSuXN8P.png")
            embed.set_footer(
                text=f"Requested by {requester.display_name}" if requester else "Requested by someone")

            embed.clear_fields()
            if len(self.queue) > 0:
                next_song = self.queue[0]
                next_url = next_song[0]
                if not next_url.startswith('http'):
                    next_song_field = f"[{next_url}]"
                    embed.add_field(
                        name="Up Next", value=next_song_field, inline=False)
                else:
                    next_song_field = f"[Next Song]({next_url})"
                    embed.add_field(
                        name="Up Next", value=next_song_field, inline=False)

            embed.add_field(
                name="Progress",
                value=f"[{format_time(elapsed_time)}] {progress_bar} {format_time(duration)}",
                inline=False
            )

            if self.player_message:
                try:
                    await self.player_message.edit(embed=embed)
                except discord.NotFound:
                    self.player_message = None
                    break

            await asyncio.sleep(5)

            if elapsed_time >= duration:
                break

    async def play_youtube_audio(self, channel, voice_client, media_url=None, playback_speed=1.0, volume=0.2, requester=None):
        """Plays YouTube audio and updates the player UI."""
        await self.cancel_disconnect_timer()

        url_regex = re.compile(
            r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$')
        search_query = media_url if media_url and url_regex.match(
            media_url) else f'ytsearch1:{media_url}'

        self.current_playback_speed = playback_speed

        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'opus',
                'preferredquality': '198',
            }],
            'writethumbnail': True,
            'outtmpl': 'thumbnails/%(id)s.%(ext)s',
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                info = info['entries'][0] if 'entries' in info else info
                media_url = info.get('url')
                genre = info.get('genre', 'Unknown')

                if info.get('duration') > self.max_media_duration:
                    await channel.send("Sorry, I can't play songs longer than 2 hours.", delete_after=12)
                    return

                if not media_url:
                    raise ValueError("Failed to extract media URL")

                with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                    cursor = conn.cursor()

                    media_title = info['title']

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
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'request')
                    ''', (
                        self.guild.id,
                        requester.id if requester else None,
                        requester.display_name if requester else 'Unknown',
                        media_title,
                        info['webpage_url'],
                        genre,
                        playback_speed,
                        info['duration']
                    ))

                    conn.commit()

                    thumbnail_url = info['thumbnail']
                    self.current_video_info = info
                    self.current_media_url = self.current_video_info['webpage_url']

                    await self.create_player_embed(channel, info['webpage_url'], info['title'], playback_speed, thumbnail_url, requester)

                    ffmpeg_options = self._get_ffmpeg_options(playback_speed)
                    source = discord.FFmpegPCMAudio(
                        media_url, executable=self.ffmpeg_path, **ffmpeg_options)

                    voice_client.play(discord.PCMVolumeTransformer(
                        source, volume=volume), after=self._after_play)

                    self.is_playing = True
                    asyncio.create_task(self.update_progress_bar(
                        voice_client, info, playback_speed, requester, thumbnail_url))

        except sqlite3.Error as e:
            log_error(self.bot, f"SQLite Error in play_youtube_audio: {e}")
        except Exception as e:
            log_error(self.bot, f"Error in play_youtube_audio: {e}")

    def _after_play(self, error):
        """Callback function to be called after a song finishes playing."""
        if error:
            log_error(self.bot, f"Error in after_play: {error}")
        future = asyncio.run_coroutine_threadsafe(
            self._play_next_in_queue(), self.bot.loop)
        try:
            future.result()
        except Exception as e:
            log_error(self.bot, f"Error in _play_next_in_queue: {e}")

    async def add_to_queue(self, ctx, url, playback_speed=1.0):
        self.queue.append((url, playback_speed, ctx.author, ctx.channel))

    async def stop_playing(self):
        """Stops the music player and clears the state."""
        await self.delete_player_embed()
        self.is_playing = False
        self.current_video_info = None
        self.current_media_url = None
        await self.start_disconnect_timer()
        self.manager.cleanup_player(self.guild.id)

    async def delete_player_embed(self):
        if self.player_message:
            try:
                await self.player_message.delete()
                self.player_message = None

            except Exception as e:
                if isinstance(e, (discord.NotFound, discord.HTTPException)):
                    log_error(
                        self.bot, f"Failed to delete player message: {str(e)}")
                else:
                    pass

    def _get_ffmpeg_options(self, playback_speed):
        """Returns the appropriate FFmpeg options depending on the playback speed."""
        preload_time = 1  # seconds
        if playback_speed != 1.0:
            return {
                'before_options': f'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {preload_time}',
                'options': f'-vn -filter:a "asetrate=48000*{playback_speed},aresample=48000"'
            }
        return {
            'before_options': f'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {preload_time}',
            'options': '-vn',
        }

    async def _play_next_in_queue(self):
        """Plays the next song in the queue, if available."""
        if len(self.queue) > 0:
            url, playback_speed, requester, channel = self.queue.pop(0)
            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=self.guild)

            if not voice_client:
                return

            await self.play_youtube_audio(channel, voice_client, url, playback_speed, requester=requester)
        else:
            await self.stop_playing()

    async def start_disconnect_timer(self):
        """Starts a timer to disconnect the bot after inactivity."""
        if self.disconnect_timer:
            # timer is running arleady
            return

        log_debug(
            self.bot, f"Starting disconnect timer for guild: {self.guild.name} ({self.guild.id})")
        self.disconnect_timer = asyncio.create_task(
            self._disconnect_after_timeout())

    async def cancel_disconnect_timer(self):
        """Cancels the disconnect timer if it's running."""
        if self.disconnect_timer:
            self.disconnect_timer.cancel()
            self.disconnect_timer = None
            log_debug(
                self.bot, f"Canceled disconnect timer for guild: {self.guild.name} ({self.guild.id})")

    async def _disconnect_after_timeout(self):
        """Waits for the inactivity duration and disconnects the bot."""
        try:
            await asyncio.sleep(self.inactivity_duration)
            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=self.guild)

            if voice_client and not voice_client.is_playing():
                await voice_client.disconnect()
                log_debug(
                    self.bot, f"Disconnected from voice channel in guild '{self.guild.name}' due to inactivity.")
                await self.stop_playing()
        except asyncio.CancelledError:
            log_debug(
                self.bot, f"Disconnect timer was canceled for guild: {self.guild.name} ({self.guild.id})")
        except Exception as e:
            log_error(
                self.bot, f"Error in disconnect timer for guild '{self.guild.name}': {e}")
