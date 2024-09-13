import asyncio
import json
import os
from typing import TYPE_CHECKING

from discord.ext import commands
from dotenv import load_dotenv

from discord_bot.terminal import terminal_command_loop

load_dotenv()

BOT_CHAT_CHANNEL = int(os.getenv("BOT_CHAT_CHANNEL", 0))
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

if TYPE_CHECKING:
    from discord import Intents
    from utils.logger import Logger


class Bot(commands.Bot):
    """Main Bot class that handles the bot's initialization and startup.

    Attributes:
        intents (discord.Intents): The bot's intents.
        logger (Logger): The bot's logger.
    """

    def __init__(self, intents: "Intents", paths: dict, logger: "Logger"):
        """
        Initializes the Bot class.
        Args:
          intents (discord.Intents): The bot's intents.
          paths (dict): A dictionary of paths.
          logger (Logger): The bot's logger.
        Side Effects:
          Sets the bot's logger, paths, config file, avatar file, cogs directory, guild ID, owner ID, chatbot category ID, chatbot threads ID, Discord token, OpenAI API key, OpenAI model, Pinecone API key, Pinecone environment, and Pinecone index.
          Loads the config file.
          Sets the bot's display name.
        Examples:
          >>> bot = Bot(intents, paths, logger)
          Bot built.
          Bot initialized.
        """
        self.log = logger
        self.log.debug("Bot built.")
        self.paths = paths
        self.config_file = self.paths["configs"] / "config.json"
        self.avatar_file = self.paths["assets"] / "images" / "avatar.png"
        self.cogs_dir = self.paths["cogs"]
        self.guild_id = int(GUILD_ID) if GUILD_ID else None
        self.bot_chat_channel = BOT_CHAT_CHANNEL
        self.discord_token = str(DISCORD_TOKEN)
        self.ffmpeg_path = 'ffmpeg'

        with open(self.config_file, "r") as f:
            self.config = json.load(f)

        self.display_name = self.config.get("bot_name")

        super().__init__(command_prefix=self.config.get("prefix"), intents=intents)
        self.log.debug("Bot initialized.")
        self.running = True

    async def start_bot(self):
        """Starts bot."""
        self.log.info("Bot starting...")
        await self.load_cogs()

        bot_task = asyncio.create_task(self.start(self.discord_token), name="bot")

        try:
            while self.running:
                await asyncio.sleep(2)

        except Exception as e:
            self.log.error(f"Bot encountered an error: {e}")

        finally:
            bot_task.cancel()
            
    async def start_terminal_command_loop(self):
        """Starts the terminal command loop."""
        self.log.debug("Starting terminal command loop...")
        
        terminal_task = asyncio.create_task(terminal_command_loop(self), name="terminal")
        
        try:
            while self.running:
                await asyncio.sleep(2)
        
        except Exception as e:
            self.log.error(f"Terminal encountered an error: {e}")
        
        finally:
            terminal_task.cancel()

    def stop_bot(self):
        """Stops bot."""
        self.log.info("Bot stopping...")
        self.running = False

    async def load_cogs(self):
        """Loads all cogs in the cogs directory and its subdirectories."""
        self.log.debug("Loading cogs...")
        total_loaded_extensions = 0
        cog_name = None
        try:
            for dirpath, dirnames, filenames in os.walk(self.cogs_dir):
                loaded_extensions = []
                for filename in filenames:
                    if filename.endswith("cog.py"):
                        rel_path = os.path.relpath(dirpath, self.cogs_dir)
                        if rel_path == '.':
                            cog_name = f"cogs.{filename[:-3]}"
                        else:
                            cog_name = f"cogs.{rel_path.replace(os.sep, '.')}.{filename[:-3]}"
                        if cog_name in self.extensions:
                            continue
                        await self.load_extension(cog_name)
                        loaded_extensions.append(filename[:-3])
                        total_loaded_extensions += 1
                if loaded_extensions:
                    package_name = "Standalone Cogs" if dirpath == self.cogs_dir else os.path.basename(dirpath)
                    self.log.debug("Loaded:")
                    self.log.debug(f"Package Name: {package_name}")
                    self.log.debug(f"Extensions: {', '.join(loaded_extensions)}")
        except Exception as e:
            raise e
        self.log.info(f"Loaded total {total_loaded_extensions} cogs.")
