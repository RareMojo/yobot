import discord
import sqlite3
import datetime
from discord.ext import commands
from utils.logger import log_debug, log_error
from utils.tools import format_time, generate_bar_chart, generate_pie_chart


class MusicStatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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


async def setup(bot: commands.Bot):
    """Loads the cog."""
    try:
        await bot.add_cog(MusicStatsCog(bot))
    except Exception as e:
        log_error(bot, f"Error loading MusicStatsCog: {str(e)}")
