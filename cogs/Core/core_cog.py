import discord
import sqlite3
from discord.ext import commands
from discord import Forbidden, HTTPException
from utils.tools import update_with_discord, welcome_to_bot, generate_bar_chart, generate_pie_chart
from utils.logger import log_debug, log_error, log_info
from datetime import datetime, timedelta


class CoreCog(commands.Cog, name="CoreCog", description="The core cog for the bot."):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._initialize_core_db()

    def _initialize_core_db(self):
        """Initialize the SQLite database and create the required tables."""
        with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
            cursor = conn.cursor()

            # some foreign key support
            cursor.execute('PRAGMA foreign_keys = ON;')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS command_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    user_name TEXT NOT NULL,
                    command_name TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_command_usage_guild_id ON command_usage (guild_id);')

            conn.commit()

    @commands.Cog.listener()
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {round(error.retry_after, 2)} seconds.")
        else:
            raise error # re-raise the error so it can be logged

    @commands.Cog.listener()
    async def on_connect(self):
        try:
            await update_with_discord(self.bot)
            log_debug(self.bot, "Bot connected to Discord.")
        except Exception as e:
            log_error(self.bot, f"Error updating Bot: {str(e)}")

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await welcome_to_bot(self.bot)
            await self.bot.start_terminal_command_loop()
        except Exception as e:
            log_error(self.bot, f"Error welcoming Bot: {str(e)}")

    @commands.Cog.listener()
    async def block_dms(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    @commands.hybrid_command(name="helpyobot", help="Displays help with available commands.")
    async def help_command(self, ctx: commands.Context):
        """Sends the help command with available commands to the user via DM, grouped by cog."""

        text_logo = self.bot.text_logo.read_text()

        commands_by_cog = {}

        for command in self.bot.commands:
            if not command.hidden:
                cog_name = command.cog_name or "Uncategorized"
                if cog_name not in commands_by_cog:
                    commands_by_cog[cog_name] = []
                commands_by_cog[cog_name].append(command)

        if "Uncategorized" in commands_by_cog:
            if len(commands_by_cog["Uncategorized"]) == 1 and commands_by_cog["Uncategorized"][0].name == "help":
                del commands_by_cog["Uncategorized"]

        commands_list = ""
        for cog_name, commands in commands_by_cog.items():
            if cog_name.endswith("Cog"):
                cog_name = cog_name[:-3]
            commands_list += f"-= {cog_name} Commands =-\n\n"
            for command in commands:
                command_line = f"/{command.name:<20} - {command.help or 'No description available.'}\n"
                commands_list += command_line
            commands_list += "\n"

        commands_per_message = 1800
        chunks = []
        current_chunk = ""

        for line in commands_list.splitlines():
            if len(current_chunk) + len(line) + 1 > commands_per_message:
                chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += line + "\n"

        if current_chunk:
            chunks.append(current_chunk)

        try:
            await ctx.author.send(f"```{text_logo}```")

            for chunk in chunks:
                await ctx.author.send(f"```{chunk}```")
            await ctx.send("I’ve sent you a DM with the available commands!", delete_after=8)
        except discord.Forbidden:
            await ctx.send("I couldn’t send you a DM. Please check your DM settings or contact an Admin.", delete_after=8)
            log_debug(self.bot, "User or server has DMs disabled.")

    @commands.hybrid_command(name="prune", description="Delete a specified number of the bot's messages, except for certain command responses.")
    @commands.has_guild_permissions(manage_messages=True)
    async def prune(self, ctx: commands.Context, amount: int):
        """Deletes a specified number of the bot's own messages in the current channel, excluding certain command replies."""
        await ctx.send("Deleting messages...", delete_after=5)

        if amount < 1:
            await ctx.send("You must specify a number greater than 0.")
            return

        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send("I don't have permissions to delete messages here.")
            return

        def is_bot_message(message):
            return message.author == self.bot.user

        # a means of protecting certain messages from deletion
        protected_phrases = [
            "Song Requested",  # music requests
            "Added song",  # music requests
            "Added to queue",  # legacy music requests
            "added to the queue",  # legacy music requests
            "Now Playing",  # music player
            "Progress",  # music player fail over
        ]

        def is_protected_message(message):
            return any(phrase in message.content for phrase in protected_phrases)

        try:
            to_delete = []
            async for message in ctx.channel.history(limit=None):
                if len(to_delete) >= amount:
                    break
                if is_bot_message(message) and not is_protected_message(message):
                    to_delete.append(message)

            if len(to_delete) > 0:
                await ctx.channel.delete_messages(to_delete)
                await ctx.send(f"Deleted {len(to_delete)} of my own messages.", delete_after=5)
            else:
                await ctx.send("No messages to delete.", delete_after=5)
        except commands.errors.NotFound:
            await ctx.send("Some messages were not found.")
        except commands.errors.Forbidden:
            await ctx.send("I don't have permission to delete messages in this channel.")
            log_debug(
                self.bot, "Bot doesn't have permission to delete message in this channel.")
        except Exception as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(self.bot, f"Error in prune: {str(e)}")

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        """Log command usage when any command is invoked."""
        command_name = ctx.command.name if ctx.command else "unknown"
        user_id = ctx.author.id
        user_name = ctx.author.display_name
        guild_id = ctx.guild.id if ctx.guild else "DM"

        with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO command_usage (guild_id, command_name, user_id, user_name)
                VALUES (?, ?, ?, ?)
            ''', (guild_id, command_name, user_id, user_name))

            conn.commit()

    @commands.hybrid_command(
        name="commandstats",
        help="timeframe: all/today/week/month | group: command/hour/day | command_name: command | chart: bar/pie"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def command_stats(self, ctx, timeframe: str = "all", user: discord.User = None, command_name: str = None, chart: str = None, group: str = "command"):
        """
        Consolidated command to show command usage stats based on timeframe, user, command_name, or chart.
        """
        valid_timeframes = ["all", "today", "week", "month"]
        valid_charts = ["bar", "pie", None]
        valid_groups = ["command", "hour", "day"]

        if timeframe not in valid_timeframes:
            await ctx.send(f"Invalid timeframe: {timeframe}. Valid options are: 'all', 'today', 'week', 'month'.", delete_after=12)
            return

        if chart not in valid_charts:
            await ctx.send(f"Invalid chart type: {chart}. Valid options are: 'bar', 'pie'.", delete_after=12)
            return

        if group not in valid_groups:
            await ctx.send(f"Invalid group: {group}. Valid options are: 'command', 'hour', 'day'.", delete_after=12)
            return

        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                params = [ctx.guild.id]
                if group == 'command':
                    select_clause = "SELECT command_name, COUNT(*) AS count"
                    group_clause = "GROUP BY command_name"
                elif group == 'hour':
                    select_clause = "SELECT strftime('%H', timestamp) as hour, COUNT(*) AS count"
                    group_clause = "GROUP BY hour"
                elif group == 'day':
                    select_clause = "SELECT strftime('%w', timestamp) as day_of_week, COUNT(*) AS count"
                    group_clause = "GROUP BY day_of_week"

                query = f"{select_clause} FROM command_usage WHERE guild_id = ?"

                if timeframe == "today":
                    query += " AND DATE(timestamp) = DATE('now')"
                elif timeframe == "week":
                    query += " AND timestamp >= DATE('now', '-7 days')"
                elif timeframe == "month":
                    query += " AND timestamp >= DATE('now', '-30 days')"

                if user:
                    query += " AND user_id = ?"
                    params.append(str(user.id))

                if command_name:
                    query += " AND command_name = ?"
                    params.append(command_name)

                query += f" {group_clause} ORDER BY count DESC"

                cursor.execute(query, params)
                results = cursor.fetchall()

                if results:
                    if chart == "bar":
                        title = f"Command Usage Stats by {group.title()} ({timeframe})"
                        xlabel = group.title()
                        ylabel = "Usage Count"
                        await generate_bar_chart(ctx, results, title=title, xlabel=xlabel, ylabel=ylabel, group=group)
                    elif chart == "pie":
                        title = f"Command Usage Distribution by {group.title()} ({timeframe})"
                        await generate_pie_chart(ctx, results, title=title, group=group)
                    else:
                        await self._send_text_stats(ctx, results, timeframe, user, command_name, group)
                else:
                    await ctx.send(f"No command usage data available for the selected filters.")

        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}")
            log_error(
                self.bot, f"Database error in command {ctx.command}: {str(e)}")

    async def _send_text_stats(self, ctx, results, timeframe, user, command_name, group):
        """
        Sends the command usage stats as a text message.
        """
        user_info = f" for {user.display_name}" if user else ""
        command_info = f" for command '{command_name}'" if command_name else ""
        message = f"**Command Usage Stats by {group.title()} ({timeframe}){user_info}{command_info}:**\n"

        if group == 'command':
            for command_name, count in results:
                message += f"- `{command_name}`: {count} uses\n"
        elif group == 'hour':
            for hour, count in results:
                message += f"- Hour {hour}: {count} uses\n"
        elif group == 'day':
            day_mapping = ['Sunday', 'Monday', 'Tuesday',
                           'Wednesday', 'Thursday', 'Friday', 'Saturday']
            for day_of_week, count in results:
                day_name = day_mapping[int(day_of_week)]
                message += f"- {day_name}: {count} uses\n"

        await ctx.send(message)


async def setup(bot: commands.Bot):
    try:
        await bot.add_cog(CoreCog(bot))
        log_debug(bot, "CoreCog loaded.")
    except Exception as e:
        log_error(bot, f"Error loading CoreCog: {str(e)}")
