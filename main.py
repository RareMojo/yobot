import asyncio
from pathlib import Path

from discord_bot.build import BuildBot
from utils.tools import make_filepaths

#                     __                 __
#                    /\ \               /\ \__
#  __  __      ___   \ \ \____    ___   \ \ ,_\
# /\ \/\ \    / __`\  \ \ '__`\  / __`\  \ \ \/
# \ \ \_\ \  /\ \L\ \  \ \ \L\ \/\ \L\ \  \ \ \_
#  \/`____ \ \ \____/   \ \_,__/\ \____/   \ \__\
#   `/___/> \ \/___/     \/___/  \/___/     \/__/
#      /\___/
#      \/__/
#
# yobot: A Cog driven Discord bot written in Python.
# Thanks and have fun yall! -RareMojo


def launch_bot():
    """
    Ensures that the bot's files are set up, then builds and starts the bot.

    Launch this file to start the bot. Run: `python main.py` in the command line.
    """
    src_dir = Path(__file__).parent.absolute()
    bot_dir = Path(src_dir / "discord_bot")
    configs_dir = Path(src_dir / "configs")
    data_dir = Path(src_dir / "data")
    assets = Path(src_dir / "assets")
    logs_dir = Path(data_dir / "logs")
    cogs_dir = Path(src_dir / "cogs")

    paths = {
        "root": src_dir,
        "bot": bot_dir,
        "configs": configs_dir,
        "src": src_dir,
        "data": data_dir,
        "assets": assets,
        "logs": logs_dir,
        "cogs": cogs_dir,
    }

    make_filepaths(paths)

    builder = BuildBot(paths)
    bot = builder.build_bot()

    if bot:
        asyncio.run(bot.start_bot())
    else:
        print("Bot failed to build or start.")
        input("Press ENTER to EXIT.")


if __name__ == "__main__":
    launch_bot()
