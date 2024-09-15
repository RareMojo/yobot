import discord
import yt_dlp
import asyncio
import time
import re
import os
from cogs.Music.music_utils import generate_progress_bar, find_similar_song_title
from utils.tools import format_time
from utils.logger import log_error, log_debug
import sqlite3


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord_bot.bot import Bot


class MusicPlayer:
    def __init__(self, bot, queue, current_video_info, player_message):
        self.bot = bot
        self.queue = queue
        self.current_video_info = current_video_info
        self.player_message = player_message
        self.is_playing = False
        self.current_song_url = None
        self.initialize_music_db()

    def initialize_music_db(self):
        """Initialize the SQLite database and create the required tables."""
        with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
            cursor = conn.cursor()

            # idk some foreign key support
            cursor.execute('PRAGMA foreign_keys = ON;')

            # music tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    song_title TEXT NOT NULL,
                    song_url TEXT NOT NULL,
                    playback_speed REAL,  -- Optional, used only for song requests
                    duration REAL,        -- Optional, used only for song requests
                    action TEXT NOT NULL,  -- 'request', 'like', or 'skip'
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()

    async def create_player_embed(self, ctx, url, title, playback_speed=1.0, thumbnail='https://i.imgur.com/tSuXN8P.png'):
        """Creates or updates the player embed."""
        embed = discord.Embed(
            title=":notes: Now Playing",
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
            embed.add_field(name="Up Next", value=next_song_field, inline=False)
        else:
            next_song_field = "No more songs in the queue"
            embed.add_field(name="Up Next", value=next_song_field, inline=False)

        embed.add_field(name="Progress",
                        value="[00:00] ▰▰▰▱▱▱▱▱▱▱ 00:00", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")

        # update the message or make a new one
        if self.player_message:
            try:
                await self.player_message.edit(embed=embed)
            except discord.NotFound:
                self.player_message = await ctx.send(embed=embed)
        else:
            self.player_message = await ctx.send(embed=embed)

        reactions = ['⏮️', '▶️', '⏸️', '⏹️', '⏭️', '❤️']
        for reaction in reactions:
            await self.player_message.add_reaction(reaction)

    async def update_progress_bar(self, voice_client, video_info, playback_speed=1.0, requester=None, thumbnail=None):
        """Updates the progress bar as the song plays."""
        duration = video_info['duration'] / playback_speed
        title, url = video_info['title'], video_info['webpage_url']
        start_time = time.time()

        while voice_client.is_playing():
            elapsed_time = time.time() - start_time
            progress_percentage = min(elapsed_time / duration, 1.0)
            progress_bar = generate_progress_bar(progress_percentage)

            embed = discord.Embed(
                title=":notes: Now Playing",
                description=f"[{title}]({url})",
                color=discord.Color.blurple()
            )
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
            else:
                embed.set_thumbnail(url="https://i.imgur.com/tSuXN8P.png")
            embed.set_footer(
                text=f"Requested by {requester.display_name}" if requester else "Requested by someone")

            next_song_field = "No more songs in the queue"
            if self.queue:
                next_url, _ = self.queue[0]
                next_title = self.queue[0][0].split('/')[-1]
                # if next url isnt a url change the next song field
                if not next_url.startswith('http'):
                    next_song_field = f"[{next_title}]"
                else:
                    next_song_field = f"[{next_title}]({next_url})"
                embed.clear_fields()
                embed.add_field(name="Up Next", value=next_song_field, inline=False)

            embed.clear_fields()
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

    async def _play_youtube_audio(self, ctx, voice_client, video_url=None, playback_speed=1.0, volume=0.2):
        """Plays YouTube audio and updates the player UI."""
        url_regex = re.compile(
            r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$')
        search_query = video_url if video_url and url_regex.match(
            video_url) else f'ytsearch1:{video_url}'

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

                if not media_url:
                    raise ValueError("Failed to extract media URL")

                with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                    cursor = conn.cursor()

                    song_title = info['title']
                    similar_title = find_similar_song_title(cursor, song_title)

                    if similar_title:
                        song_title = similar_title

                    cursor.execute('''
                        INSERT INTO user_actions (user_id, user_name, song_title, song_url, playback_speed, duration, action)
                        VALUES (?, ?, ?, ?, ?, ?, 'request')
                    ''', (str(ctx.author.id), ctx.author.display_name, song_title, info['webpage_url'], playback_speed, info['duration']))

                    conn.commit()

                    thumbnail_url = info['thumbnail']
                    self.current_video_info = info
                    self.current_song_url = self.current_video_info['webpage_url']
                    await self.create_player_embed(ctx, info['webpage_url'], info['title'], playback_speed, thumbnail_url)

                    ffmpeg_options = self._get_ffmpeg_options(playback_speed)
                    source = discord.FFmpegPCMAudio(
                        media_url, executable=self.bot.ffmpeg_path, **ffmpeg_options)
                    voice_client.play(discord.PCMVolumeTransformer(
                        source, volume=volume), after=lambda e: self._after_play(ctx))

                    await self.update_progress_bar(voice_client, info, playback_speed, ctx.author, thumbnail_url)

        except Exception as e:
            log_error(self.bot, f"Error playing audio: {e}")
            raise e

    def _get_ffmpeg_options(self, playback_speed):
        """Returns the appropriate FFmpeg options depending on the playback speed."""
        if playback_speed != 1.0:
            return {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': f'-vn -filter:a "asetrate=48000*{playback_speed},aresample=48000"'
            }
        return {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }

    async def play_next_in_queue(self, ctx):
        """Plays the next song in the queue, if available."""
        if self.queue:
            next_url, playback_speed = self.queue.pop(0)
            voice_client = discord.utils.get(
                self.bot.voice_clients, guild=ctx.guild)

            if voice_client and voice_client.is_connected():
                self.is_playing = True
                await self.delete_player_embed()

                await self.create_player_embed(ctx, next_url, self.current_video_info['title'], playback_speed)
                await self._play_youtube_audio(ctx, voice_client, next_url, playback_speed)
            else:
                await self.stop_playing(ctx)
        else:
            await self.stop_playing(ctx)

    async def stop_playing(self, ctx):
        """Stops the music player and clears the state."""
        await self.delete_player_embed()
        self.is_playing = False
        self.player_message = None

    def _after_play(self, ctx):
        """Callback function to be called after a song finishes playing."""
        coro = self.play_next_in_queue(ctx)
        future = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)

        try:
            future.result()
        except Exception as e:
            if e.code != 10008:
                pass
            else:
                if e.code == 10008:
                    pass
                log_error(self.bot, f"Error in after play callback: {e}")

    async def delete_player_embed(self):
        if self.player_message:
            try:
                await self.player_message.delete()
                self.player_message = None

            except Exception as e:
                if e == discord.NotFound or e == discord.HTTPException:
                    log_error(
                        self.bot, f"Failed to delete player message: {e}")
                else:
                    pass
