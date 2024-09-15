from discord.ext import commands
import discord
from discord import Forbidden, HTTPException
from utils.tools import update_with_discord, welcome_to_bot
from utils.logger import log_debug, log_error, log_info
import sqlite3
from datetime import datetime, timedelta

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord_bot.bot import Bot


class CoreCog(commands.Cog, name="CoreCog", description="The core cog for the bot."):

    def __init__(self, bot: "Bot"):
        self.bot = bot
        self.initialize_core_db()

    def initialize_core_db(self):
        """Initialize the SQLite database and create the required tables."""
        with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
            cursor = conn.cursor()

            # idk some foreign key support
            cursor.execute('PRAGMA foreign_keys = ON;')

            # commands tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS command_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_name TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()

    @commands.Cog.listener()
    async def on_connect(self):
        try:
            await update_with_discord(self.bot)
            log_debug(self.bot, "Bot connected to Discord.")
        except Exception as e:
            log_error(self.bot, f"Error updating Bot: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await welcome_to_bot(self.bot)
            await self.bot.start_terminal_command_loop()
        except Exception as e:
            log_error(self.bot, f"Error welcoming Bot: {e}")

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
    @commands.has_permissions(manage_messages=True)
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
            log_error(self.bot, f"Error in prune: {e}")

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        """Log command usage when any command is invoked."""
        command_name = ctx.command.name if ctx.command else "unknown"
        user_id = str(ctx.author.id)
        user_name = ctx.author.display_name

        # log command usage
        with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO command_usage (command_name, user_id, user_name)
                VALUES (?, ?, ?)
            ''', (command_name, user_id, user_name))

        conn.commit()

    @commands.hybrid_command(name="commandstats", help="Show how often commands have been executed.")
    async def command_stats(self, ctx):
        """Show how often each command has been requested."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT command_name, COUNT(*) AS count 
                    FROM command_usage
                    GROUP BY command_name
                    ORDER BY count DESC
                ''')
                results = cursor.fetchall()

                if results:
                    embed = discord.Embed(
                        title="Command Usage Statistics", color=discord.Color.green())
                    for command_name, count in results:
                        embed.add_field(name=command_name,
                                        value=f"{count} times", inline=False)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("No command usage data available.")

        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(
                self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(
                self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="commandstatsweek", help="Show detailed stats of commands executed in the past week.")
    async def command_stats_week(self, ctx):
        """Show detailed stats of command usage in the past week."""
        try:
            one_week_ago = datetime.now() - timedelta(days=7)

            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as con:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT command_name, COUNT(*) AS count
                    FROM command_usage
                    WHERE timestamp >= ?
                    GROUP BY command_name
                    ORDER BY count DESC
                ''', (one_week_ago,))

                results = cursor.fetchall()

                if results:
                    embed = discord.Embed(
                        title="Command Usage in the Past Week",
                        description="Here’s a breakdown of the most used commands in the past 7 days:",
                        color=discord.Color.blue()
                    )

                    for command_name, count in results:
                        embed.add_field(name=command_name,
                                        value=f"{count} times", inline=False)

                    await ctx.send(embed=embed)

                else:
                    await ctx.send("No command usage data available for the past week.")

        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(
                self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(
                self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="usercommandstatsweek", help="Show command usage stats for a specific user over the past week.")
    async def user_command_stats_week(self, ctx, user: discord.User = None):
        """Show the command usage stats for a specific user over the past week."""
        try:
            if user is None:
                user = ctx.author

            user_id = str(user.id)

            one_week_ago = datetime.now() - timedelta(days=7)

            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as con:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT command_name, COUNT(*) AS count
                    FROM command_usage
                    WHERE user_id = ? AND timestamp >= ?
                    GROUP BY command_name
                    ORDER BY count DESC
                ''', (user_id, one_week_ago))

                results = cursor.fetchall()

                if results:
                    embed = discord.Embed(
                        title=f"Command Usage for {user.display_name} (Past Week)",
                        description=f"Here’s a breakdown of the commands used by {user.mention} in the past 7 days:",
                        color=discord.Color.blue()
                    )

                    for command_name, count in results:
                        embed.add_field(name=command_name,
                                        value=f"{count} times", inline=False)

                    await ctx.send(embed=embed)

                else:
                    await ctx.send(f"No command usage data available for {user.mention} in the past week.")

        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(
                self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(
                self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")

    @commands.hybrid_command(name="usercommandstats", help="Show all-time command usage stats for a specific user or yourself.")
    async def user_command_stats(self, ctx, user: discord.User = None):
        """Show all-time command usage statistics for a specific user or yourself."""
        try:
            if user is None:
                user = ctx.author

            user_id = str(user.id)

            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as con:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT command_name, COUNT(*) AS count
                    FROM command_usage
                    WHERE user_id = ?
                    GROUP BY command_name
                    ORDER BY count DESC
                ''', (user_id,))

                results = cursor.fetchall()

                if results:
                    embed = discord.Embed(
                        title=f"All-Time Command Usage for {user.display_name}",
                        description=f"Here’s a breakdown of all-time command usage by {user.mention}:",
                        color=discord.Color.green()
                    )

                    for command_name, count in results:
                        embed.add_field(name=command_name,
                                        value=f"{count} times", inline=False)

                    await ctx.send(embed=embed)

                else:
                    await ctx.send(f"No command usage data available for {user.mention}.")

        except sqlite3.Error as e:
            await ctx.send(f"An error occurred with the database:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(
                self.bot, f"Database error in command {ctx.command}: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(
                self.bot, f"Unexpected error in command {ctx.command}: {str(e)}")


async def setup(bot: "Bot"):
    try:
        await bot.add_cog(CoreCog(bot))
        log_debug(bot, "CoreCog loaded.")
    except Exception as e:
        log_error(bot, f"Error loading CoreCog: {e}")
