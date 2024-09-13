from discord.ext import commands
from discord import Forbidden, HTTPException
from utils.tools import update_with_discord, welcome_to_bot
from utils.logger import log_debug, log_error, log_info

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord_bot.bot import Bot


class CoreCog(commands.Cog, name="Core Cog", description="The core cog for the bot."):

    def __init__(self, bot: "Bot"):
        self.bot = bot

    @commands.hybrid_command(name="prune", description="Delete a specified number of the bot's messages.")
    @commands.has_permissions(manage_messages=True)
    async def prune(self, ctx: commands.Context, amount: int):
        """
        Deletes a specified number of the bot's own messages from the current channel.
        Only the bot owner can issue this command.
        Args:
            ctx (commands.Context): The context of the command.
            amount (int): The number of the bot's messages to delete.
        """

        if amount < 1:
            await ctx.send("You must specify a number greater than 0.")
            return

        def is_bot_message(message):
            return message.author == self.bot.user

        try:
            # Fetch only up to 'amount' of the bot's own messages
            deleted = []
            async for message in ctx.channel.history(limit=100):
                if len(deleted) >= amount:
                    break
                if is_bot_message(message):
                    await message.delete()
                    deleted.append(message)

            await ctx.send(f"Deleted {len(deleted)} of my own messages.", delete_after=5)
        except Forbidden:
            await ctx.send("I don't have permission to delete messages in this channel.")
        except HTTPException as e:
            await ctx.send(f"An error occurred while trying to delete messages: {e}")

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

async def setup(bot: "Bot"):
    try:
        await bot.add_cog(CoreCog(bot))
        log_debug(bot, "CoreCog loaded.")
    except Exception as e:
        log_error(bot, f"Error loading CoreCog: {e}")
