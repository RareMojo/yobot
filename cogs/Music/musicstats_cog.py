import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import sqlite3
from discord.ext import commands
import discord
from utils.logger import log_debug, log_error
from utils.tools import format_time
from datetime import datetime, timedelta

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord_bot.bot import Bot


class MusicStatsCog(commands.Cog, name="MusicStatsCog", description="Displays music statistics."):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log_debug(bot, "MusicStatsCog initialized.")

    @commands.hybrid_command(name="musichistory", help="Show the last 10 songs played.")
    async def last_played_songs(self, ctx):
        """Show the last 10 songs played."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url 
                    FROM user_actions 
                    WHERE action = 'request'
                    ORDER BY timestamp DESC 
                    LIMIT 10
                ''')
                results = cursor.fetchall()

                if results:
                    message = "**Here are the last 10 songs played:**\n"
                    for index, (song_title, song_url) in enumerate(results, start=1):
                        message += f"{index}. [{song_title}](<{song_url}>)\n"
                    await ctx.send(message)
                else:
                    await ctx.send("No song history available.")   
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")
            

    @commands.hybrid_command(name="topsong", help="Show the most requested song.")
    async def most_requested(self, ctx):
        """Show the most requested song."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, COUNT(*) AS count 
                    FROM user_actions 
                    WHERE action = 'request'
                    GROUP BY song_title, song_url 
                    ORDER BY count DESC 
                    LIMIT 1
                ''')
                result = cursor.fetchone()

                if result:
                    song_title, song_url, count = result
                    await ctx.send(f"The most requested song is [{song_title}]({song_url}) with **{count}** requests.")
                else:
                    await ctx.send("No data for this yet.. Go do the thing! :rocket:")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")    

    @commands.hybrid_command(name="topslowsong", help="Show the most requested slow song.")
    async def most_requested_slow(self, ctx):
        """Show the most requested slow song (<= 0.9x speed)."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, COUNT(*) AS count 
                    FROM user_actions 
                    WHERE action = 'request' AND playback_speed <= 0.9
                    GROUP BY song_title, song_url 
                    ORDER BY count DESC 
                    LIMIT 1
                ''')
                result = cursor.fetchone()

                if result:
                    song_title, song_url, count = result
                    await ctx.send(f"The most requested slow song (<= 0.9x speed) is [{song_title}]({song_url}) with **{count}** requests.")
                else:
                    await ctx.send("No data available for slow songs.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="topfastsong", help="Show the most requested fast song.")
    async def most_requested_fast(self, ctx):
        """Show the most requested fast song (>= 1.1x speed)."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, COUNT(*) AS count 
                    FROM user_actions 
                    WHERE action = 'request' AND playback_speed >= 1.1
                    GROUP BY song_title, song_url 
                    ORDER BY count DESC 
                    LIMIT 1
                ''')
                result = cursor.fetchone()
                
                if result:
                    song_title, song_url, count = result
                    await ctx.send(f"The most requested fast song (>= 1.1x speed) is [{song_title}]({song_url}) with **{count}** requests.")
                else:
                    await ctx.send("No data available for fast songs.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="topliked", help="Show the most liked song.")
    async def most_liked(self, ctx):
        """Show the most liked song."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, COUNT(*) AS like_count
                    FROM user_actions 
                    WHERE action = 'like'
                    GROUP BY song_title, song_url
                    ORDER BY like_count DESC
                    LIMIT 1
                ''')
                result = cursor.fetchone()
                
                if result:
                    song_title, song_url, like_count = result
                    await ctx.send(f"The most liked song **EVER** is [{song_title}]({song_url}) with **{like_count}** likes.")
                else:
                    await ctx.send("No data for this yet.. Go do the thing! :rocket:")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="topsongtoday", help="Show the most requested song of the day.")
    async def top_song_of_the_day(self, ctx):
        """Show the most requested song of the day."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, COUNT(*) AS count 
                    FROM user_actions 
                    WHERE action = 'request' AND DATE(timestamp) = DATE('now')
                    GROUP BY song_title, song_url 
                    ORDER BY count DESC 
                    LIMIT 1
                ''')
                result = cursor.fetchone()

                if result:
                    song_title, song_url, count = result
                    await ctx.send(f"The most requested song **TODAY** is [{song_title}]({song_url}) with **{count}** requests.")
                else:
                    await ctx.send("No data available for today.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="topsongweek", help="Show the most requested song of the week.")
    async def top_song_of_the_week(self, ctx):
        """Show the most requested song of the week."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, COUNT(*) AS count 
                    FROM user_actions 
                    WHERE action = 'request' AND timestamp >= DATE('now', '-7 days')
                    GROUP BY song_title, song_url 
                    ORDER BY count DESC 
                    LIMIT 1
                ''')
                result = cursor.fetchone()

                if result:
                    song_title, song_url, count = result
                    await ctx.send(f"The most requested song **THIS WEEK** is [{song_title}]({song_url}) with **{count}** requests.")
                else:
                    await ctx.send("No data available for this week.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="topsongmonth", help="Show the most requested song of the month.")
    async def top_song_of_the_month(self, ctx):
        """Show the most requested song of the month."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, COUNT(*) AS count 
                    FROM user_actions 
                    WHERE action = 'request' AND timestamp >= DATE('now', '-30 days')
                    GROUP BY song_title, song_url 
                    ORDER BY count DESC 
                    LIMIT 1
                ''')
                result = cursor.fetchone()

                if result:
                    song_title, song_url, count = result
                    await ctx.send(f"The most requested song **THIS MONTH** is [{song_title}]({song_url}) with **{count}** requests.")
                else:
                    await ctx.send("No data available for this month.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="topdj", help="Show the user with the most song requests.")
    async def top_user(self, ctx):
        """Show the user with the most song requests."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT user_name, COUNT(*) AS count 
                    FROM user_actions 
                    WHERE action = 'request'
                    GROUP BY user_id 
                    ORDER BY count DESC 
                    LIMIT 1
                ''')
                result = cursor.fetchone()

                if result:
                    user_name, count = result
                    await ctx.send(f"The top user is **{user_name}** with **{count}** song requests.")
                else:
                    await ctx.send("No data for this yet.. Go do the thing! :rocket:")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="topdjweek", help="Show the user with the most song requests this week.")
    async def top_user_week(self, ctx):
        """Show the user with the most song requests for the current week."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT user_name, COUNT(*) AS count
                    FROM user_actions
                    WHERE action = 'request' AND strftime('%W', timestamp) = strftime('%W', 'now')
                    GROUP BY user_id
                    ORDER BY count DESC
                    LIMIT 1
                ''')
                result = cursor.fetchone()

                if result:
                    user_name, count = result
                    await ctx.send(f"The top user this week is **{user_name}** with **{count}** song requests.")
                else:
                    await ctx.send("No data available for this week.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="topdjmonth", help="Show the user with the most song requests this month.")
    async def top_user_month(self, ctx):
        """Show the user with the most song requests for the current month."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT user_name, COUNT(*) AS count
                    FROM user_actions
                    WHERE action = 'request' AND strftime('%m', timestamp) = strftime('%m', 'now')
                    GROUP BY user_id
                    ORDER BY count DESC
                    LIMIT 1
                ''')
                result = cursor.fetchone()

                if result:
                    user_name, count = result
                    await ctx.send(f"The top user this month is **{user_name}** with **{count}** song requests.")
                else:
                    await ctx.send("No data available for this month.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="totalsongs", help="Show the total number of songs requested.")
    async def total_songs(self, ctx):
        """Show the total number of songs requested."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute(
                    'SELECT COUNT(*) FROM user_actions WHERE action = "request"')
                result = cursor.fetchone()

                total_songs = result[0] if result else 0
                await ctx.send(f"A total of **{total_songs}** songs have been requested.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="musictime", help="Show the total time spent listening to songs.")
    async def total_time(self, ctx):
        """Show the total time spent listening to songs."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute(
                    'SELECT SUM(playback_speed * duration) FROM user_actions WHERE action = "request"')
                result = cursor.fetchone()

                total_seconds = result[0] if result else 0
                total_time = format_time(total_seconds)
                await ctx.send(f"The total time spent listening to songs is **{total_time}**.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="songstats", help="Show generic stats for song requests and likes.")
    async def songstats(self, ctx):
        """Display general statistics about song requests and likes."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute(
                    'SELECT COUNT(*) FROM user_actions WHERE action = "request"')
                total_requests = cursor.fetchone()[0]

                cursor.execute(
                    'SELECT COUNT(*) FROM user_actions WHERE action = "like"')
                total_likes = cursor.fetchone()[0]

                cursor.execute(
                    'SELECT COUNT(DISTINCT user_id) FROM user_actions WHERE action = "request"')
                unique_users = cursor.fetchone()[0]

                cursor.execute('''
                    SELECT song_title, COUNT(*) AS count
                    FROM user_actions
                    WHERE action = "request"
                    GROUP BY song_title
                    ORDER BY count DESC
                    LIMIT 1
                ''')
                most_requested_song = cursor.fetchone()

                cursor.execute('''
                    SELECT song_title, COUNT(*) AS like_count
                    FROM user_actions
                    WHERE action = "like"
                    GROUP BY song_title
                    ORDER BY like_count DESC
                    LIMIT 1
                ''')
                most_liked_song = cursor.fetchone()

                message = (f"**Song Request and Like Stats**\n\n"
                        f"**Total Song Requests:** {total_requests}\n"
                        f"**Total Likes:** {total_likes}\n"
                        f"**Unique Users:** {unique_users}\n"
                        f"**Most Requested Song:** {most_requested_song[0]} ({most_requested_song[1]} requests)\n"
                        f"**Most Liked Song:** {most_liked_song[0]} ({most_liked_song[1]} likes)")

                await ctx.send(message)
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="musicstats", help="Show stats for a specific user's requests and likes, or your own if no user is specified.")
    async def user_music_stats(self, ctx, user: discord.Member = None):
        """Show stats for the user issuing the command or a specified user."""
        if user is None:
            await ctx.send("Invalid user. Please specify a valid member.")
            return
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute(
                    'SELECT COUNT(*), SUM(playback_speed * duration) FROM user_actions WHERE action = "request" AND user_id = ?', (str(user.id),))
                total_songs, total_time = cursor.fetchone()

                cursor.execute(
                    'SELECT COUNT(*) FROM user_actions WHERE action = "like" AND user_id = ?', (str(user.id),))
                total_likes = cursor.fetchone()[0]

                cursor.execute(
                    'SELECT song_title, COUNT(*) FROM user_actions WHERE action = "request" AND user_id = ? GROUP BY song_title ORDER BY COUNT(*) DESC LIMIT 1', (str(user.id),))
                top_requested_song = cursor.fetchone()

                cursor.execute('''
                    SELECT song_title, COUNT(*)
                    FROM user_actions
                    WHERE action = "like" AND user_id = ?
                    GROUP BY song_title
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                ''', (str(user.id),))
                top_liked_song = cursor.fetchone()

                total_time = format_time(total_time) if total_time else "0:00"
                message = (f"**Stats for {user.display_name}**\n"
                        f"**Total Songs Requested:** {total_songs}\n"
                        f"**Total Likes Given:** {total_likes}\n"
                        f"**Total Listening Time:** {total_time}\n"
                        f"**Most Requested Song:** {top_requested_song[0]} ({top_requested_song[1]} requests)\n"
                        f"**Most Liked Song:** {top_liked_song[0]} ({top_liked_song[1]} likes)")

                await ctx.send(message)
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")
            
    @commands.hybrid_command(name="usersongchart", help="Show a donut chart of the number of requests for each user.")
    async def user_distribution(self, ctx):
        """Generate and display a donut chart of user request distribution."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT user_name, COUNT(*) AS count
                    FROM user_actions
                    WHERE action = "request"
                    GROUP BY user_name
                    ORDER BY count DESC
                    LIMIT 5
                ''')
                data = cursor.fetchall()

                if data:
                    users, counts = zip(*data)

                    fig, ax = plt.subplots(figsize=(6, 4))

                    colors = plt.cm.get_cmap('tab10', len(users))

                    wedges, texts, autotexts = ax.pie(counts, labels=None, autopct='%1.1f%%',
                                                    startangle=90, colors=colors(np.linspace(0, 1, len(users))),
                                                    wedgeprops=dict(width=0.3))

                    plt.setp(autotexts, size=10, weight="bold")

                    center_circle = plt.Circle((0, 0), 0.70, fc='white')
                    fig.gca().add_artist(center_circle)

                    ax.legend(wedges, users, title="Users",
                            loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

                    plt.title('Top 5 Users by Song Requests', fontsize=16)

                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    buf.seek(0)

                    file = discord.File(fp=buf, filename="user_distribution.png")
                    await ctx.send(file=file)

                    buf.close()
                    plt.clf()
                else:
                    await ctx.send("No data available for user distribution.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="likechart", help="Show a donut chart of the number of likes for each song.")
    async def like_distribution(self, ctx):
        """Generate and display a donut chart of song like distribution."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, COUNT(*) AS like_count
                    FROM user_actions
                    WHERE action = 'like'
                    GROUP BY song_title
                    ORDER BY like_count DESC
                    LIMIT 5
                ''')
                data = cursor.fetchall()
                
                if data:
                    songs, like_counts = zip(*data)

                    fig, ax = plt.subplots(figsize=(6, 4))

                    colors = plt.cm.get_cmap('tab10', len(songs))

                    wedges, texts, autotexts = ax.pie(like_counts, labels=None, autopct='%1.1f%%',
                                                    startangle=90, colors=colors(np.linspace(0, 1, len(songs))),
                                                    wedgeprops=dict(width=0.3))

                    plt.setp(autotexts, size=10, weight="bold")

                    center_circle = plt.Circle((0, 0), 0.70, fc='white')
                    fig.gca().add_artist(center_circle)

                    ax.legend(wedges, songs, title="Songs",
                            loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

                    plt.title('Top 5 Most Liked Songs', fontsize=16)

                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    buf.seek(0)

                    file = discord.File(fp=buf, filename="like_distribution.png")
                    await ctx.send(file=file)

                    buf.close()
                    plt.clf()
                else:
                    await ctx.send("No data available for song like distribution.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="songchart", help="Show a donut chart of the number of requests for each song.")
    async def song_distribution(self, ctx):
        """Generate and display a donut chart of song request distribution."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, COUNT(*) AS count
                    FROM user_actions
                    WHERE action = 'request'
                    GROUP BY song_title
                    ORDER BY count DESC
                    LIMIT 5
                ''')
                data = cursor.fetchall()

                if data:
                    songs, counts = zip(*data)

                    fig, ax = plt.subplots(figsize=(6, 4))

                    colors = plt.cm.get_cmap('tab10', len(songs))

                    wedges, texts, autotexts = ax.pie(counts, labels=None, autopct='%1.1f%%',
                                                    startangle=90, colors=colors(np.linspace(0, 1, len(songs))),
                                                    wedgeprops=dict(width=0.3))

                    plt.setp(autotexts, size=10, weight="bold")

                    center_circle = plt.Circle((0, 0), 0.70, fc='white')
                    fig.gca().add_artist(center_circle)

                    ax.legend(wedges, songs, title="Songs",
                            loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

                    plt.title('Top 5 Most Requested Songs', fontsize=16)

                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    buf.seek(0)

                    file = discord.File(fp=buf, filename="song_distribution.png")
                    await ctx.send(file=file)

                    buf.close()
                    plt.clf()
                else:
                    await ctx.send("No data available for song distribution.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="songspeedchart", help="Show a donut chart of playback speed distribution.")
    async def playback_speed_distribution(self, ctx):
        """Generate and display a donut chart of playback speed distribution."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT 
                        SUM(CASE WHEN playback_speed < 0.9 THEN 1 ELSE 0 END) AS slow,
                        SUM(CASE WHEN playback_speed BETWEEN 0.9 AND 1.1 THEN 1 ELSE 0 END) AS normal,
                        SUM(CASE WHEN playback_speed > 1.1 THEN 1 ELSE 0 END) AS fast
                    FROM user_actions
                    WHERE action = 'request'
                ''')
                data = cursor.fetchone()

                if data:
                    speed_categories = ['Slow', 'Normal', 'Fast']
                    counts = list(data)

                    fig, ax = plt.subplots(figsize=(6, 4))

                    colors = plt.cm.get_cmap('tab10', len(speed_categories))

                    wedges, texts, autotexts = ax.pie(counts, labels=None, autopct='%1.1f%%',
                                                    startangle=90, colors=colors(np.linspace(0, 1, len(speed_categories))),
                                                    wedgeprops=dict(width=0.3))

                    plt.setp(autotexts, size=10, weight="bold")

                    center_circle = plt.Circle((0, 0), 0.70, fc='white')
                    fig.gca().add_artist(center_circle)

                    ax.legend(wedges, speed_categories, title="Playback Speed",
                            loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
                    plt.title('Playback Speed Distribution', fontsize=16)

                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    buf.seek(0)

                    file = discord.File(
                        fp=buf, filename="playback_speed_distribution.png")
                    await ctx.send(file=file)

                    buf.close()
                    plt.clf()
                else:
                    await ctx.send("No data available for playback speed distribution.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="slowsongchart", help="Show a donut chart for the top 5 slow songs.")
    async def most_slow_songs_chart(self, ctx):
        """Generate and display a donut chart of the top 5 slow songs (<= 0.9x speed)."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, COUNT(*) AS count 
                    FROM user_actions 
                    WHERE playback_speed <= 0.9 AND action = 'request'
                    GROUP BY song_title
                    ORDER BY count DESC 
                    LIMIT 5
                ''')
                slow_data = cursor.fetchall()

                if slow_data:
                    slow_songs = [row[0] for row in slow_data]
                    slow_counts = [row[1] for row in slow_data]

                    fig, ax = plt.subplots(figsize=(6, 4))

                    wedges, texts, autotexts = ax.pie(slow_counts, labels=None, autopct='%1.1f%%',
                                                    startangle=90, wedgeprops=dict(width=0.3))
                    ax.set_title("Top 5 Slow Songs (<= 0.9x)", fontsize=14)

                    center_circle = plt.Circle((0, 0), 0.70, fc='white')
                    fig.gca().add_artist(center_circle)

                    ax.legend(wedges, slow_songs, title="Slow Songs",
                            loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    buf.seek(0)

                    file = discord.File(fp=buf, filename="top5_slow_songs.png")
                    await ctx.send(file=file)

                    buf.close()
                    plt.clf()
                else:
                    await ctx.send("No data available for slow songs.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="fastsongchart", help="Show a donut chart for the top 5 fast songs.")
    async def most_fast_songs_chart(self, ctx):
        """Generate and display a donut chart of the top 5 fast songs (>= 1.1x speed)."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, COUNT(*) AS count 
                    FROM user_actions 
                    WHERE playback_speed >= 1.1 AND action = 'request'
                    GROUP BY song_title
                    ORDER BY count DESC 
                    LIMIT 5
                ''')
                fast_data = cursor.fetchall()

                if fast_data:
                    fast_songs = [row[0] for row in fast_data]
                    fast_counts = [row[1] for row in fast_data]

                    fig, ax = plt.subplots(figsize=(6, 4))

                    wedges, texts, autotexts = ax.pie(fast_counts, labels=None, autopct='%1.1f%%',
                                                    startangle=90, wedgeprops=dict(width=0.3))
                    ax.set_title("Top 5 Fast Songs (>= 1.1x)", fontsize=14)

                    center_circle = plt.Circle((0, 0), 0.70, fc='white')
                    fig.gca().add_artist(center_circle)

                    ax.legend(wedges, fast_songs, title="Fast Songs",
                            loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    buf.seek(0)

                    file = discord.File(fp=buf, filename="top5_fast_songs.png")
                    await ctx.send(file=file)

                    buf.close()
                    plt.clf()
                else:
                    await ctx.send("No data available for fast songs.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="weeklymusic", help="Show a bar chart of how many songs were played each day over the past week.")
    async def songs_per_day_week(self, ctx):
        """Generate and display a bar chart of songs played per day over the past week."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT DATE(timestamp), COUNT(*)
                    FROM user_actions
                    WHERE timestamp >= DATE('now', '-7 days') AND action = 'request'
                    GROUP BY DATE(timestamp)
                    ORDER BY DATE(timestamp)
                ''')
                data = cursor.fetchall()
                
                if data:
                    dates, counts = zip(*data)

                    fig, ax = plt.subplots(figsize=(8, 4))
                    ax.bar(dates, counts, color='skyblue')
                    plt.xticks(rotation=45, ha='right')
                    plt.xlabel('Date')
                    plt.ylabel('Number of Songs')
                    plt.title('Songs Played Per Day Over the Past Week')

                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    buf.seek(0)

                    file = discord.File(fp=buf, filename="songs_per_day_week.png")
                    await ctx.send(file=file)

                    buf.close()
                    plt.clf()
                else:
                    await ctx.send("No data available for the past week.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")
            
    @commands.hybrid_command(name="monthlymusic", help="Show a bar chart of how many songs were played each day over the past month.")
    async def songs_per_day_month(self, ctx):
        """Generate and display a bar chart of songs played per day over the past month."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT DATE(timestamp), COUNT(*)
                    FROM user_actions
                    WHERE timestamp >= DATE('now', '-30 days') AND action = 'request'
                    GROUP BY DATE(timestamp)
                    ORDER BY DATE(timestamp)
                ''')
                data = cursor.fetchall()

                if data:
                    dates, counts = zip(*data)

                    fig, ax = plt.subplots(figsize=(8, 4))
                    ax.bar(dates, counts, color='lightcoral')
                    plt.xticks(rotation=45, ha='right')
                    plt.xlabel('Date')
                    plt.ylabel('Number of Songs')
                    plt.title('Songs Played Per Day Over the Past Month')

                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    buf.seek(0)

                    file = discord.File(fp=buf, filename="songs_per_day_month.png")
                    await ctx.send(file=file)

                    buf.close()
                    plt.clf()
                else:
                    await ctx.send("No data available for the past month.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="hypeweekly", help="Show a heatmap of song requests over the past week by hour.")
    async def request_heatmap(self, ctx):
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                now = datetime.now()
                one_week_ago = now - timedelta(days=7)

                cursor.execute('''
                    SELECT timestamp FROM user_actions 
                    WHERE action = 'request' AND timestamp >= ? ORDER BY timestamp
                ''', (one_week_ago,))

                data = cursor.fetchall()

                if data:
                    heatmap_data = np.zeros((7, 24))

                    for row in data:
                        timestamp = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                        days_ago = (now - timestamp).days
                        hour_of_day = timestamp.hour

                        heatmap_data[days_ago, hour_of_day] += 1

                    heatmap_data = np.flipud(heatmap_data)

                    fig, ax = plt.subplots(figsize=(10, 6))
                    cax = ax.imshow(
                        heatmap_data, interpolation='nearest', cmap='Blues', aspect='auto')

                    ax.set_xlabel('Hour of Day')
                    ax.set_ylabel('Days Ago')
                    ax.set_xticks(np.arange(24))
                    ax.set_yticks(np.arange(7))
                    ax.set_yticklabels([f'{i} day(s) ago' for i in range(7)])

                    fig.colorbar(cax)

                    plt.title('Song Requests Heatmap (Past Week)', fontsize=16)

                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    buf.seek(0)

                    file = discord.File(fp=buf, filename="heatmap.png")
                    await ctx.send(file=file)

                    buf.close()
                    plt.clf()

                else:
                    await ctx.send("No data available for the past week's song requests.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")
            
    @commands.hybrid_command(name="hypeday", help="Show a bar chart of the average number of song requests per day of the week.")
    async def weekly_average(self, ctx):
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT timestamp FROM user_actions WHERE action = 'request'
                ''')

                data = cursor.fetchall()

                if data:
                    day_of_week_counts = np.zeros(7)
                    total_days = np.zeros(7)

                    for row in data:
                        timestamp = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                        day_of_week = timestamp.weekday()  # Monday = 0, Sunday = 6

                        day_of_week_counts[day_of_week] += 1
                        total_days[day_of_week] = 1

                    average_requests_per_day = day_of_week_counts / total_days

                    days_labels = ['Monday', 'Tuesday', 'Wednesday',
                                'Thursday', 'Friday', 'Saturday', 'Sunday']

                    fig, ax = plt.subplots(figsize=(8, 6))
                    ax.bar(days_labels, average_requests_per_day, color='royalblue')

                    ax.set_xlabel('Day of the Week')
                    ax.set_ylabel('Average Number of Requests')
                    ax.set_title('Average Song Requests by Day of the Week')

                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    buf.seek(0)

                    file = discord.File(fp=buf, filename="weekly_average.png")
                    await ctx.send(file=file)

                    buf.close()
                    plt.clf()

                else:
                    await ctx.send("No data available to calculate weekly averages.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="hypetime", help="Show a donut chart of the top 5 hours of the day for song requests.")
    async def top_times(self, ctx):
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT timestamp FROM user_actions WHERE action = 'request'
                ''')

                data = cursor.fetchall()

                if data:
                    hourly_counts = np.zeros(24)

                    for row in data:
                        timestamp = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                        # Get the hour of the day (0 to 23)
                        hour_of_day = timestamp.hour

                        hourly_counts[hour_of_day] += 1

                    top_5_hours = np.argsort(hourly_counts)[-5:][::-1]
                    top_5_counts = hourly_counts[top_5_hours]

                    hours_labels = [
                        f'{hour}:00 - {hour + 1}:00' for hour in top_5_hours]

                    fig, ax = plt.subplots(figsize=(6, 4))

                    colors = plt.cm.get_cmap('tab10', len(top_5_hours))

                    wedges, texts, autotexts = ax.pie(top_5_counts, labels=None, autopct='%1.1f%%',
                                                    startangle=90, colors=colors(np.linspace(0, 1, len(top_5_hours))),
                                                    wedgeprops=dict(width=0.3))

                    plt.setp(autotexts, size=10, weight="bold")

                    center_circle = plt.Circle((0, 0), 0.70, fc='white')
                    fig.gca().add_artist(center_circle)

                    ax.legend(wedges, hours_labels, title="Time of Day",
                            loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

                    plt.title('Top 5 Request Times (By Hour)', fontsize=16)

                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    buf.seek(0)

                    file = discord.File(fp=buf, filename="top_times.png")
                    await ctx.send(file=file)

                    buf.close()
                    plt.clf()

                else:
                    await ctx.send("No data available to calculate top request times.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="hypeusers", help="Show a bar chart of unique requesters per day and highlight the day with the most unique requesters.")
    async def most_unique_requesters(self, ctx):
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT user_id, timestamp FROM user_actions WHERE action = 'request'
                ''')

                data = cursor.fetchall()
                
                if data:
                    day_unique_requesters = {}

                    for row in data:
                        user_id = row[0]
                        timestamp = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
                        day = timestamp.date()  # Get the date (YYYY-MM-DD)

                        if day not in day_unique_requesters:
                            day_unique_requesters[day] = set()
                        day_unique_requesters[day].add(user_id)

                    days = sorted(day_unique_requesters.keys())
                    unique_requester_counts = [
                        len(day_unique_requesters[day]) for day in days]

                    max_unique_day = days[np.argmax(unique_requester_counts)]
                    max_unique_count = max(unique_requester_counts)

                    fig, ax = plt.subplots(figsize=(10, 6))

                    bars = ax.bar(days, unique_requester_counts, color='royalblue')

                    bars[np.argmax(unique_requester_counts)].set_color('red')

                    ax.set_xlabel('Date')
                    ax.set_ylabel('Unique Requesters')
                    ax.set_title('Unique Requesters Per Day')

                    ax.text(max_unique_day, max_unique_count, f'Most Unique: {max_unique_count}',
                            ha='center', va='bottom', fontsize=12, color='red')

                    fig.autofmt_xdate()

                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    buf.seek(0)

                    file = discord.File(
                        fp=buf, filename="most_unique_requesters.png")
                    await ctx.send(file=file)

                    buf.close()
                    plt.clf()

                else:
                    await ctx.send("No data available to calculate unique requesters.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="hypeuniquesongs", help="Show a bar chart of unique songs requested per day and highlight the day with the most unique songs.")
    async def most_unique_songs(self, ctx):
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, timestamp FROM user_actions WHERE action = 'request'
                ''')

                data = cursor.fetchall()

                if data:
                    day_unique_songs = {}

                    for row in data:
                        song_title = row[0]
                        timestamp = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
                        day = timestamp.date()  # Get the date (YYYY-MM-DD)

                        if day not in day_unique_songs:
                            day_unique_songs[day] = set()
                        day_unique_songs[day].add(song_title)

                    days = sorted(day_unique_songs.keys())
                    unique_song_counts = [len(day_unique_songs[day])
                                        for day in days]

                    max_unique_day = days[np.argmax(unique_song_counts)]
                    max_unique_count = max(unique_song_counts)

                    fig, ax = plt.subplots(figsize=(10, 6))

                    bars = ax.bar(days, unique_song_counts, color='royalblue')

                    bars[np.argmax(unique_song_counts)].set_color('red')

                    ax.set_xlabel('Date')
                    ax.set_ylabel('Unique Songs Requested')
                    ax.set_title('Unique Songs Requested Per Day')

                    ax.text(max_unique_day, max_unique_count, f'Most Unique: {max_unique_count}',
                            ha='center', va='bottom', fontsize=12, color='red')

                    fig.autofmt_xdate()

                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    buf.seek(0)

                    file = discord.File(fp=buf, filename="most_unique_songs.png")
                    await ctx.send(file=file)

                    buf.close()
                    plt.clf()

                else:
                    await ctx.send("No data available to calculate unique songs.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="totallikes", help="Show the total number of likes across all songs.")
    async def total_likes(self, ctx):
        """Show the total number of likes."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute(
                    'SELECT COUNT(*) FROM user_actions WHERE action = "like"')
                result = cursor.fetchone()

                total_likes = result[0] if result else 0
                await ctx.send(f"The total number of likes across all songs is **{total_likes}**.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")


    @commands.hybrid_command(name="topuserlikes", help="Show the user who has given the most likes.")
    async def top_user_likes(self, ctx):
        """Show the user who has given the most likes."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT user_id, user_name, COUNT(*) AS count
                    FROM user_actions
                    WHERE action = "like"
                    GROUP BY user_id, user_name
                    ORDER BY count DESC
                    LIMIT 1
                ''')
                result = cursor.fetchone()

                if result:
                    user_id, user_name, count = result
                    await ctx.send(f"The user with the most likes is **{user_name}** (ID: {user_id}) with **{count}** likes.")
                else:
                    await ctx.send("No data for this yet.. Go do the thing! :rocket:")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")
            
    @commands.hybrid_command(name="songdurations", help="Show the average duration of songs requested.")
    async def average_song_duration(self, ctx):
        """Show the average duration of songs requested."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute(
                    'SELECT AVG(duration) FROM user_actions WHERE action = "request"')
                result = cursor.fetchone()

                avg_duration = result[0] if result else 0
                await ctx.send(f"The average duration of requested songs is **{avg_duration:.2f}** seconds.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="longestsong", help="Show the longest song requested.")
    async def longest_song(self, ctx):
        """Show the longest song requested."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, duration
                    FROM user_actions
                    WHERE action = "request"
                    ORDER BY duration DESC
                    LIMIT 1
                ''')
                result = cursor.fetchone()

                if result:
                    song_title, song_url, duration = result
                    await ctx.send(f"The longest song requested is [{song_title}]({song_url}) with a duration of **{duration}** seconds.")
                else:
                    await ctx.send("No data for this yet.. Go do the thing! :rocket:")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="mostconsistentdj", help="Show the most consistent requester over the past week.")
    async def most_consistent_dj(self, ctx):
        """Show the user with the most consistent requests."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT user_id, user_name, COUNT(DISTINCT DATE(timestamp)) AS request_days
                    FROM user_actions
                    WHERE action = "request" AND timestamp >= DATE('now', '-7 days')
                    GROUP BY user_id, user_name
                    HAVING request_days = 7
                    ORDER BY request_days DESC
                    LIMIT 1
                ''')
                result = cursor.fetchone()

                if result:
                    user_id, user_name, request_days = result
                    await ctx.send(f"The most consistent requester over the past week is **{user_name}** (ID: {user_id}), with requests made every day.")
                else:
                    await ctx.send("No data for this yet.. Go do the thing! :rocket:")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="requestgrowthchart", help="Show the growth rate of song requests over time.")
    async def request_growth_chart(self, ctx):
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT DATE(timestamp) AS day, COUNT(*) AS requests
                    FROM user_actions
                    WHERE action = 'request'
                    GROUP BY day
                    ORDER BY day
                ''')
                data = cursor.fetchall()

                if data:
                    days, requests = zip(*data)

                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.plot(days, requests, marker='o', color='blue')

                    ax.set_xlabel('Date')
                    ax.set_ylabel('Number of Requests')
                    ax.set_title('Song Request Growth Over Time')

                    fig.autofmt_xdate()

                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight')
                    buf.seek(0)

                    file = discord.File(fp=buf, filename="request_growth_chart.png")
                    await ctx.send(file=file)

                    buf.close()
                    plt.clf()

                else:
                    await ctx.send("No data available to calculate growth.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="requestfrequency", help="Show the request frequency per user.")
    async def request_frequency(self, ctx):
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT user_id, user_name, COUNT(*) AS request_count, 
                        (julianday('now') - julianday(MIN(timestamp))) AS days_active
                    FROM user_actions
                    WHERE action = 'request'
                    GROUP BY user_id, user_name
                    HAVING days_active > 0
                    ORDER BY request_count / days_active DESC
                    LIMIT 10
                ''')
                data = cursor.fetchall()

                if data:
                    result_lines = [f"**{user_name}** (ID: {user_id}) - {request_count} requests over {days_active:.2f} days (avg {request_count/days_active:.2f} per day)"
                                    for user_id, user_name, request_count, days_active in data]
                    await ctx.send("\n".join(result_lines))
                else:
                    await ctx.send("No data for this yet.. Go do the thing! :rocket:")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="topsongduration", help="Show the most requested song by total playback time.")
    async def top_song_duration(self, ctx):
        """Show the most requested song by total playback time."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, song_url, SUM(duration) AS total_duration, COUNT(*) AS count
                    FROM user_actions
                    WHERE action = 'request'
                    GROUP BY song_title, song_url
                    ORDER BY total_duration DESC
                    LIMIT 1
                ''')

                result = cursor.fetchone()

                if result:
                    song_title, song_url, total_duration, count = result
                    await ctx.send(f"The most requested song by total playback time is [{song_title}]({song_url}) with **{count}** requests and a total playback time of **{total_duration}** seconds.")
                else:
                    await ctx.send("No data for this yet.. Go do the thing! :rocket:")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="toplikeduser", help="Show the user whose requests have received the most likes.")
    async def top_liked_user(self, ctx):
        """Show the user whose requests have received the most likes."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT user_id, user_name, COUNT(*) AS like_count
                    FROM user_actions
                    WHERE action = 'like'
                    GROUP BY user_id, user_name
                    ORDER BY like_count DESC
                    LIMIT 1
                ''')
                result = cursor.fetchone()
                
                if result:
                    user_id, user_name, like_count = result
                    await ctx.send(f"The user whose requests have received the most likes is **{user_name}** (ID: {user_id}) with **{like_count}** likes.")
                else:
                    await ctx.send("No data for this yet.. Go do the thing! :rocket:")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="useractivity", help="Show user request activity over time.")
    async def user_activity(self, ctx):
        """Show user request activity over time."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT user_name, DATE(timestamp), COUNT(*)
                    FROM user_actions
                    WHERE action = 'request'
                    GROUP BY user_name, DATE(timestamp)
                    ORDER BY DATE(timestamp) ASC
                ''')
                data = cursor.fetchall()

                if data:
                    activity_lines = [f"**{user_name}** - {request_date}: {request_count} requests"
                                    for user_name, request_date, request_count in data]
                    await ctx.send("\n".join(activity_lines))
                else:
                    await ctx.send("No activity data available.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="repeatrequests", help="Show songs that were requested multiple times in a short period.")
    async def repeat_requests(self, ctx):
        """Show songs that were requested repeatedly in a short period."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT song_title, COUNT(*) AS request_count
                    FROM user_actions
                    WHERE action = 'request' AND timestamp >= DATETIME('now', '-1 hour')
                    GROUP BY song_title
                    HAVING request_count > 1
                    ORDER BY request_count DESC
                ''')
                data = cursor.fetchall()
                
                if data:
                    repeat_lines = [f"**{song_title}** - {request_count} requests in the past hour"
                                    for song_title, request_count in data]
                    await ctx.send("\n".join(repeat_lines))
                else:
                    await ctx.send("No repeat request data available.")
        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

async def setup(bot: "Bot"):
    """Loads the cog."""
    try:
        await bot.add_cog(MusicStatsCog(bot))
    except Exception as e:
        log_error(bot, f"Error loading MusicStatsCog: {e}")
