from discord.ext import commands
from discord import Forbidden, HTTPException
from utils.tools import update_with_discord, welcome_to_bot
from utils.logger import log_debug, log_error, log_info

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord_bot.bot import Bot


class CoreCog(commands.Cog, name="CoreCog", description="The core cog for the bot."):

    def __init__(self, bot: "Bot"):
        self.bot = bot

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
                cog_name = command.cog_name or "Uncategorized"  # Use "Uncategorized" if no cog
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
                command_line = f"/{command.name:<15} - {command.help or 'No description available.'}\n"
                commands_list += command_line
            commands_list += "\n"

        # Split the command list into clean chunks, avoid breaking commands in half
        commands_per_message = 1800  # Allow room for clean splits in the message (below Discord's 2000 limit)
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
            await ctx.send("I couldn’t send you a DM. Please check your DM settings.", delete_after=8)

    @commands.hybrid_command(name="prune", description="Delete a specified number of the bot's messages.")
    @commands.has_permissions(manage_messages=True)
    async def prune(self, ctx: commands.Context, amount: int):
        """Deletes a specified number of the bot's own messages in the current channel."""
        await ctx.send("Deleting messages...", delete_after=5)
    
        if amount < 1:
            await ctx.send("You must specify a number greater than 0.")
            return

        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send("I don't have permissions to delete messages here.")
            return

        def is_bot_message(message):
            return message.author == self.bot.user

        try:
            to_delete = []
            async for message in ctx.channel.history(limit=None):
                if len(to_delete) >= amount:
                    break
                if is_bot_message(message):
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
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")


async def setup(bot: "Bot"):
    try:
        await bot.add_cog(CoreCog(bot))
        log_debug(bot, "CoreCog loaded.")
    except Exception as e:
        log_error(bot, f"Error loading CoreCog: {e}")
