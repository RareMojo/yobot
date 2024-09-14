import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import sqlite3
from discord.ext import commands
import discord
from utils.logger import log_debug, log_error
from cogs.Music.music_utils import format_time

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord_bot.bot import Bot


class MusicStatsCog(commands.Cog, name="MusicStatsCog", description="Displays music statistics."):
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log_debug(bot, "MusicStatsCog initialized.")
    
    @commands.hybrid_command(name="topsong", help="Show the most requested song.")
    async def most_requested(self, ctx):
        """Show the most requested song."""
        conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT song_title, song_url, COUNT(*) AS count 
            FROM user_requests 
            GROUP BY song_title, song_url 
            ORDER BY count DESC 
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()

        if result:
            song_title, song_url, count = result
            await ctx.send(f"The most requested song is [{song_title}]({song_url}) with **{count}** requests.")
        else:
            await ctx.send("No data available.")

    @commands.hybrid_command(name="topslowsong", help="Show the most requested slow song.")
    async def most_requested_slow(self, ctx):
        """Show the most requested slow song (<= 0.9x speed)."""
        conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT song_title, song_url, COUNT(*) AS count 
            FROM user_requests 
            WHERE playback_speed <= 0.9
            GROUP BY song_title, song_url 
            ORDER BY count DESC 
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()

        if result:
            song_title, song_url, count = result
            await ctx.send(f"The most requested slow song (<= 0.9x speed) is [{song_title}]({song_url}) with **{count}** requests.")
        else:
            await ctx.send("No data available for slow songs.")

    @commands.hybrid_command(name="topfastsong", help="Show the most requested fast song.")
    async def most_requested_fast(self, ctx):
        """Show the most requested fast song (>= 1.1x speed)."""
        conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT song_title, song_url, COUNT(*) AS count 
            FROM user_requests 
            WHERE playback_speed >= 1.1
            GROUP BY song_title, song_url 
            ORDER BY count DESC 
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()

        if result:
            song_title, song_url, count = result
            await ctx.send(f"The most requested fast song (>= 1.1x speed) is [{song_title}]({song_url}) with **{count}** requests.")
        else:
            await ctx.send("No data available for fast songs.")

    @commands.hybrid_command(name="topliked", help="Show the most liked song.")
    async def most_liked(self, ctx):
        """Show the most liked song."""
        conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT ur.song_title, ur.song_url, COUNT(*) AS like_count
            FROM song_likes sl
            JOIN user_requests ur ON sl.song_id = ur.id
            GROUP BY ur.song_title, ur.song_url
            ORDER BY like_count DESC
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()

        if result:
            song_title, song_url, like_count = result
            await ctx.send(f"The most liked song **EVER** is [{song_title}]({song_url}) with **{like_count}** likes.")
        else:
            await ctx.send("No data available.")

    @commands.hybrid_command(name="topsongtoday", help="Show the most requested song of the day.")
    async def top_song_of_the_day(self, ctx):
        """Show the most requested song of the day."""
        conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
        cursor = conn.cursor()
        
        # Query to get the most requested song for the current day
        cursor.execute('''
            SELECT song_title, song_url, COUNT(*) AS count 
            FROM user_requests 
            WHERE DATE(timestamp) = DATE('now')
            GROUP BY song_title, song_url 
            ORDER BY count DESC 
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()

        if result:
            song_title, song_url, count = result
            await ctx.send(f"The most requested song **TODAY** is [{song_title}]({song_url}) with **{count}** requests.")
        else:
            await ctx.send("No data available for today.")
            
    @commands.hybrid_command(name="topsongweek", help="Show the most requested song of the week.")
    async def top_song_of_the_week(self, ctx):
        """Show the most requested song of the week."""
        try:
            conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
            cursor = conn.cursor()

            # Query to get the most requested song for the past week
            cursor.execute('''
                SELECT song_title, song_url, COUNT(*) AS count 
                FROM user_requests 
                WHERE timestamp >= DATE('now', '-7 days')
                GROUP BY song_title, song_url 
                ORDER BY count DESC 
                LIMIT 1
            ''')
            result = cursor.fetchone()
            conn.close()

            if result:
                song_title, song_url, count = result
                await ctx.send(f"The most requested song **THIS WEEK** is [{song_title}]({song_url}) with **{count}** requests.")
            else:
                await ctx.send("No data available for this week.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            
    @commands.hybrid_command(name="topsongmonth", help="Show the most requested song of the month.")
    async def top_song_of_the_month(self, ctx):
        """Show the most requested song of the month."""
        try:
            conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
            cursor = conn.cursor()

            # Query to get the most requested song for the past month
            cursor.execute('''
                SELECT song_title, song_url, COUNT(*) AS count 
                FROM user_requests 
                WHERE timestamp >= DATE('now', '-30 days')
                GROUP BY song_title, song_url 
                ORDER BY count DESC 
                LIMIT 1
            ''')
            result = cursor.fetchone()
            conn.close()

            if result:
                song_title, song_url, count = result
                await ctx.send(f"The most requested song **THIS MONTH** is [{song_title}]({song_url}) with **{count}** requests.")
            else:
                await ctx.send("No data available for this month.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.hybrid_command(name="topdj", help="Show the user with the most song requests.")
    async def top_user(self, ctx):
        """Show the user with the most song requests."""
        conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT user_name, COUNT(*) AS count 
            FROM user_requests 
            GROUP BY user_id 
            ORDER BY count DESC 
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()

        if result:
            user_name, count = result
            await ctx.send(f"The top user is **{user_name}** with **{count}** song requests.")
        else:
            await ctx.send("No data available.")

    @commands.hybrid_command(name="topdjweek", help="Show the user with the most song requests this week.")
    async def top_user_week(self, ctx):
        """Show the user with the most song requests for the current week."""
        conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT user_name, COUNT(*) AS count
            FROM user_requests
            WHERE strftime('%W', request_time) = strftime('%W', 'now')
            GROUP BY user_id
            ORDER BY count DESC
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()

        if result:
            user_name, count = result
            await ctx.send(f"The top user this week is **{user_name}** with **{count}** song requests.")
        else:
            await ctx.send("No data available for this week.")

    @commands.hybrid_command(name="topdjmonth", help="Show the user with the most song requests this month.")
    async def top_user_month(self, ctx):
        """Show the user with the most song requests for the current month."""
        conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT user_name, COUNT(*) AS count
            FROM user_requests
            WHERE strftime('%m', request_time) = strftime('%m', 'now')
            GROUP BY user_id
            ORDER BY count DESC
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()

        if result:
            user_name, count = result
            await ctx.send(f"The top user this month is **{user_name}** with **{count}** song requests.")
        else:
            await ctx.send("No data available for this month.")

    @commands.hybrid_command(name="totalsongs", help="Show the total number of songs requested.")
    async def total_songs(self, ctx):
        """Show the total number of songs requested."""
        conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM user_requests')
        result = cursor.fetchone()
        conn.close()

        total_songs = result[0] if result else 0
        await ctx.send(f"A total of **{total_songs}** songs have been requested.")

    @commands.hybrid_command(name="musictime", help="Show the total time spent listening to songs.")
    async def total_time(self, ctx):
        """Show the total time spent listening to songs."""
        conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
        cursor = conn.cursor()

        cursor.execute('SELECT SUM(playback_speed * duration) FROM user_requests')
        result = cursor.fetchone()
        conn.close()

        total_seconds = result[0] if result else 0
        total_time = format_time(total_seconds)
        await ctx.send(f"The total time spent listening to songs is **{total_time}**.")

    @commands.hybrid_command(name="songstats", help="Show generic stats for song requests and likes.")
    async def songstats(self, ctx):
        """Display general statistics about song requests and likes."""
        try:
            conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
            cursor = conn.cursor()

            # Total number of song requests
            cursor.execute('SELECT COUNT(*) FROM user_requests')
            total_requests = cursor.fetchone()[0]

            # Total number of likes
            cursor.execute('SELECT COUNT(*) FROM song_likes')
            total_likes = cursor.fetchone()[0]

            # Number of unique users
            cursor.execute('SELECT COUNT(DISTINCT user_id) FROM user_requests')
            unique_users = cursor.fetchone()[0]

            # Most requested and most liked songs
            cursor.execute('''
                SELECT song_title, COUNT(*) AS count
                FROM user_requests
                GROUP BY song_title
                ORDER BY count DESC
                LIMIT 1
            ''')
            most_requested_song = cursor.fetchone()

            cursor.execute('''
                SELECT ur.song_title, COUNT(*) AS like_count
                FROM song_likes sl
                JOIN user_requests ur ON sl.song_id = ur.id
                GROUP BY ur.song_title
                ORDER BY like_count DESC
                LIMIT 1
            ''')
            most_liked_song = cursor.fetchone()

            conn.close()

            message = (f"**Song Request and Like Stats**\n\n"
                    f"**Total Song Requests:** {total_requests}\n"
                    f"**Total Likes:** {total_likes}\n"
                    f"**Unique Users:** {unique_users}\n"
                    f"**Most Requested Song:** {most_requested_song[0]} ({most_requested_song[1]} requests)\n"
                    f"**Most Liked Song:** {most_liked_song[0]} ({most_liked_song[1]} likes)")

            await ctx.send(message)

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.hybrid_command(name="musicstats", help="Show stats for a specific user's requests and likes.")
    async def user_stats(self, ctx, user: discord.Member):
        """Show stats for a specific user regarding requests and likes."""
        conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
        cursor = conn.cursor()

        # Query for total songs requested, total likes given, and total listening time
        cursor.execute('SELECT COUNT(*), SUM(playback_speed * duration) FROM user_requests WHERE user_id = ?', (str(user.id),))
        total_songs, total_time = cursor.fetchone()

        cursor.execute('SELECT COUNT(*) FROM song_likes WHERE user_id = ?', (str(user.id),))
        total_likes = cursor.fetchone()[0]

        # Query for the most requested and most liked songs by this user
        cursor.execute('SELECT song_title, COUNT(*) FROM user_requests WHERE user_id = ? GROUP BY song_title ORDER BY COUNT(*) DESC LIMIT 1', (str(user.id),))
        top_requested_song = cursor.fetchone()

        cursor.execute('''
            SELECT ur.song_title, COUNT(*)
            FROM song_likes sl
            JOIN user_requests ur ON sl.song_id = ur.id
            WHERE sl.user_id = ?
            GROUP BY ur.song_title
            ORDER BY COUNT(*) DESC
            LIMIT 1
        ''', (str(user.id),))
        top_liked_song = cursor.fetchone()

        conn.close()

        total_time = format_time(total_time) if total_time else "0:00"
        message = (f"**Stats for {user.display_name}**\n"
                f"**Total Songs Requested:** {total_songs}\n"
                f"**Total Likes Given:** {total_likes}\n"
                f"**Total Listening Time:** {total_time}\n"
                f"**Most Requested Song:** {top_requested_song[0]} ({top_requested_song[1]} requests)\n"
                f"**Most Liked Song:** {top_liked_song[0]} ({top_liked_song[1]} likes)")

        await ctx.send(message)

    @commands.hybrid_command(name="usersongchart", help="Show a donut chart of the number of requests for each user.")
    async def user_distribution(self, ctx):
        """Generate and display a donut chart of user request distribution."""
        try:
            conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
            cursor = conn.cursor()

            # Fetch top 5 users with the most song requests for the donut chart
            cursor.execute('''
                SELECT user_name, COUNT(*) AS count
                FROM user_requests
                GROUP BY user_name
                ORDER BY count DESC
                LIMIT 5
            ''')
            data = cursor.fetchall()
            conn.close()

            if data:
                # Separate the data into user names and counts
                users, counts = zip(*data)

                fig, ax = plt.subplots(figsize=(6, 4))

                colors = plt.cm.get_cmap('tab10', len(users))

                wedges, texts, autotexts = ax.pie(counts, labels=None, autopct='%1.1f%%',
                                                startangle=90, colors=colors(np.linspace(0, 1, len(users))),
                                                wedgeprops=dict(width=0.3))

                plt.setp(autotexts, size=10, weight="bold")

                center_circle = plt.Circle((0, 0), 0.70, fc='white')
                fig.gca().add_artist(center_circle)

                ax.legend(wedges, users, title="Users", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
                
                plt.title('Top 5 Users by Song Requests', fontsize=16)

                # Save the chart to a buffer
                buf = BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)

                file = discord.File(fp=buf, filename="user_distribution.png")
                await ctx.send(file=file)

                # Close the buffer and clear the plot
                buf.close()
                plt.clf()
            else:
                await ctx.send("No data available for user distribution.")

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.hybrid_command(name="likechart", help="Show a donut chart of the number of likes for each song.")
    async def like_distribution(self, ctx):
        """Generate and display a donut chart of song like distribution."""
        try:
            conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
            cursor = conn.cursor()

            # Fetch top 5 most liked songs for the donut chart
            cursor.execute('''
                SELECT ur.song_title, COUNT(*) AS like_count
                FROM song_likes sl
                JOIN user_requests ur ON sl.song_id = ur.id
                GROUP BY ur.song_title
                ORDER BY like_count DESC
                LIMIT 5
            ''')
            data = cursor.fetchall()
            conn.close()

            if data:
                # Separate the data into song titles and like counts
                songs, like_counts = zip(*data)

                fig, ax = plt.subplots(figsize=(6, 4))

                colors = plt.cm.get_cmap('tab10', len(songs))

                wedges, texts, autotexts = ax.pie(like_counts, labels=None, autopct='%1.1f%%',
                                                startangle=90, colors=colors(np.linspace(0, 1, len(songs))),
                                                wedgeprops=dict(width=0.3))

                plt.setp(autotexts, size=10, weight="bold")

                center_circle = plt.Circle((0, 0), 0.70, fc='white')
                fig.gca().add_artist(center_circle)

                ax.legend(wedges, songs, title="Songs", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
                
                plt.title('Top 5 Most Liked Songs', fontsize=16)
                ax.text(0, 0, '', horizontalalignment='center', verticalalignment='center', fontsize=14)

                # Save the chart to a buffer
                buf = BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)

                file = discord.File(fp=buf, filename="like_distribution.png")
                await ctx.send(file=file)

                # Close the buffer and clear the plot
                buf.close()
                plt.clf()
            else:
                await ctx.send("No data available for song like distribution.")

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.hybrid_command(name="songchart", help="Show a donut chart of the number of requests for each song.")
    async def song_distribution(self, ctx):
        """Generate and display a donut chart of song request distribution."""
        try:
            conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
            cursor = conn.cursor()

            # Fetch top 5 most requested songs for the donut chart
            cursor.execute('''
                SELECT song_title, COUNT(*) AS count
                FROM user_requests
                GROUP BY song_title
                ORDER BY count DESC
                LIMIT 5
            ''')
            data = cursor.fetchall()
            conn.close()

            if data:
                # Separate the data into song titles and counts
                songs, counts = zip(*data)

                fig, ax = plt.subplots(figsize=(6, 4))

                colors = plt.cm.get_cmap('tab10', len(songs))

                wedges, texts, autotexts = ax.pie(counts, labels=None, autopct='%1.1f%%',
                                                startangle=90, colors=colors(np.linspace(0, 1, len(songs))),
                                                wedgeprops=dict(width=0.3))

                plt.setp(autotexts, size=10, weight="bold")

                center_circle = plt.Circle((0, 0), 0.70, fc='white')
                fig.gca().add_artist(center_circle)

                ax.legend(wedges, songs, title="Songs", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
                
                plt.title('Top 5 Most Requested Songs', fontsize=16)
                ax.text(0, 0, '', horizontalalignment='center', verticalalignment='center', fontsize=14)

                # Save the chart to a buffer
                buf = BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)

                file = discord.File(fp=buf, filename="song_distribution.png")
                await ctx.send(file=file)

                # Close the buffer and clear the plot
                buf.close()
                plt.clf()
            else:
                await ctx.send("No data available for song distribution.")

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.hybrid_command(name="songspeedchart", help="Show a donut chart of playback speed distribution.")
    async def playback_speed_distribution(self, ctx):
        """Generate and display a donut chart of playback speed distribution."""
        try:
            conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
            cursor = conn.cursor()

            # Fetch counts for different speed categories
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN playback_speed < 0.9 THEN 1 ELSE 0 END) AS slow,
                    SUM(CASE WHEN playback_speed BETWEEN 0.9 AND 1.1 THEN 1 ELSE 0 END) AS normal,
                    SUM(CASE WHEN playback_speed > 1.1 THEN 1 ELSE 0 END) AS fast
                FROM user_requests
            ''')
            data = cursor.fetchone()
            conn.close()

            if data:
                speed_categories = ['Slow', 'Normal', 'Fast']
                counts = list(data)  # Fetch results as a list

                fig, ax = plt.subplots(figsize=(6, 4))

                colors = plt.cm.get_cmap('tab10', len(speed_categories))

                wedges, texts, autotexts = ax.pie(counts, labels=None, autopct='%1.1f%%',
                                                startangle=90, colors=colors(np.linspace(0, 1, len(speed_categories))),
                                                wedgeprops=dict(width=0.3))

                plt.setp(autotexts, size=10, weight="bold")

                center_circle = plt.Circle((0, 0), 0.70, fc='white')
                fig.gca().add_artist(center_circle)

                ax.legend(wedges, speed_categories, title="Playback Speed", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
                plt.title('Playback Speed Distribution', fontsize=16)

                # Save the chart to a buffer
                buf = BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)

                file = discord.File(fp=buf, filename="playback_speed_distribution.png")
                await ctx.send(file=file)

                # Close the buffer and clear the plot
                buf.close()
                plt.clf()
            else:
                await ctx.send("No data available for playback speed distribution.")

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.hybrid_command(name="slowsongchart", help="Show a donut chart for the top 5 slow songs.")
    async def most_slow_songs_chart(self, ctx):
        """Generate and display a donut chart of the top 5 slow songs (<= 0.9x speed)."""
        try:
            conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
            cursor = conn.cursor()

            # Fetch the top 5 slow songs (<= 0.9x speed)
            cursor.execute('''
                SELECT song_title, COUNT(*) AS count 
                FROM user_requests 
                WHERE playback_speed <= 0.9
                GROUP BY song_title
                ORDER BY count DESC 
                LIMIT 5
            ''')
            slow_data = cursor.fetchall()
            conn.close()

            if slow_data:
                # Prepare slow songs data for chart
                slow_songs = [row[0] for row in slow_data]
                slow_counts = [row[1] for row in slow_data]

                # Create donut chart for slow songs
                fig, ax = plt.subplots(figsize=(6, 4))

                wedges, texts, autotexts = ax.pie(slow_counts, labels=None, autopct='%1.1f%%',
                                                startangle=90, wedgeprops=dict(width=0.3))
                ax.set_title("Top 5 Slow Songs (<= 0.9x)", fontsize=14)

                center_circle = plt.Circle((0, 0), 0.70, fc='white')
                fig.gca().add_artist(center_circle)

                ax.legend(wedges, slow_songs, title="Slow Songs", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

                # Save the chart to a buffer
                buf = BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)

                file = discord.File(fp=buf, filename="top5_slow_songs.png")
                await ctx.send(file=file)

                # Close the buffer and clear the plot
                buf.close()
                plt.clf()
            else:
                await ctx.send("No data available for slow songs.")

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.hybrid_command(name="fastsongchart", help="Show a donut chart for the top 5 fast songs.")
    async def most_fast_songs_chart(self, ctx):
        """Generate and display a donut chart of the top 5 fast songs (>= 1.1x speed)."""
        try:
            conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
            cursor = conn.cursor()

            # Fetch the top 5 fast songs (>= 1.1x speed)
            cursor.execute('''
                SELECT song_title, COUNT(*) AS count 
                FROM user_requests 
                WHERE playback_speed >= 1.1
                GROUP BY song_title
                ORDER BY count DESC 
                LIMIT 5
            ''')
            fast_data = cursor.fetchall()
            conn.close()

            if fast_data:
                # Prepare fast songs data for chart
                fast_songs = [row[0] for row in fast_data]
                fast_counts = [row[1] for row in fast_data]

                # Create donut chart for fast songs
                fig, ax = plt.subplots(figsize=(6, 4))

                wedges, texts, autotexts = ax.pie(fast_counts, labels=None, autopct='%1.1f%%',
                                                startangle=90, wedgeprops=dict(width=0.3))
                ax.set_title("Top 5 Fast Songs (>= 1.1x)", fontsize=14)

                center_circle = plt.Circle((0, 0), 0.70, fc='white')
                fig.gca().add_artist(center_circle)

                ax.legend(wedges, fast_songs, title="Fast Songs", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

                # Save the chart to a buffer
                buf = BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)

                file = discord.File(fp=buf, filename="top5_fast_songs.png")
                await ctx.send(file=file)

                # Close the buffer and clear the plot
                buf.close()
                plt.clf()
            else:
                await ctx.send("No data available for fast songs.")

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.hybrid_command(name="weeklymusic", help="Show a bar chart of how many songs were played each day over the past week.")
    async def songs_per_day_week(self, ctx):
        """Generate and display a bar chart of songs played per day over the past week."""
        try:
            conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
            cursor = conn.cursor()

            # Fetch song counts for each day over the past 7 days
            cursor.execute('''
                SELECT DATE(timestamp), COUNT(*)
                FROM user_requests
                WHERE timestamp >= DATE('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY DATE(timestamp)
            ''')
            data = cursor.fetchall()
            conn.close()

            if data:
                # Extract dates and counts
                dates, counts = zip(*data)

                fig, ax = plt.subplots(figsize=(8, 4))
                ax.bar(dates, counts, color='skyblue')
                plt.xticks(rotation=45, ha='right')
                plt.xlabel('Date')
                plt.ylabel('Number of Songs')
                plt.title('Songs Played Per Day Over the Past Week')

                # Save the chart to a buffer
                buf = BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)

                file = discord.File(fp=buf, filename="songs_per_day_week.png")
                await ctx.send(file=file)

                # Close the buffer and clear the plot
                buf.close()
                plt.clf()
            else:
                await ctx.send("No data available for the past week.")

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.hybrid_command(name="monthlymusic", help="Show a bar chart of how many songs were played each day over the past month.")
    async def songs_per_day_month(self, ctx):
        """Generate and display a bar chart of songs played per day over the past month."""
        try:
            conn = sqlite3.connect(self.bot.data_dir / 'music_stats.db')
            cursor = conn.cursor()

            # Fetch song counts for each day over the past 30 days
            cursor.execute('''
                SELECT DATE(timestamp), COUNT(*)
                FROM user_requests
                WHERE timestamp >= DATE('now', '-30 days')
                GROUP BY DATE(timestamp)
                ORDER BY DATE(timestamp)
            ''')
            data = cursor.fetchall()
            conn.close()

            if data:
                # Extract dates and counts
                dates, counts = zip(*data)

                fig, ax = plt.subplots(figsize=(8, 4))
                ax.bar(dates, counts, color='lightcoral')
                plt.xticks(rotation=45, ha='right')
                plt.xlabel('Date')
                plt.ylabel('Number of Songs')
                plt.title('Songs Played Per Day Over the Past Month')

                # Save the chart to a buffer
                buf = BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)

                file = discord.File(fp=buf, filename="songs_per_day_month.png")
                await ctx.send(file=file)

                # Close the buffer and clear the plot
                buf.close()
                plt.clf()
            else:
                await ctx.send("No data available for the past month.")

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")


async def setup(bot: "Bot"):
    """Loads the cog."""
    try:
        await bot.add_cog(MusicStatsCog(bot))
    except Exception as e:
        log_error(bot, f"Error loading MusicStatsCog: {e}")