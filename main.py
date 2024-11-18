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
# yobot: A Cog-driven Discord bot written in Python.
# Thanks and have fun yall! -RareMojo


async def main():
    """
    Main entry point for the bot. Sets up paths, builds the bot, and starts it.
    """
    src_dir = Path(__file__).parent.absolute()
    paths = {
        "root": src_dir,
        "bot": src_dir / "discord_bot",
        "configs": src_dir / "configs",
        "src": src_dir,
        "data": src_dir / "data",
        "assets": src_dir / "assets",
        "logs": src_dir / "data" / "logs",
        "cogs": src_dir / "cogs",
    }

    make_filepaths(paths)

    builder = BuildBot(paths)
    bot = builder.build_bot()

    if bot:
        try:
            await bot.start_bot()
        except KeyboardInterrupt:
            bot.log.info("KeyboardInterrupt detected. Shutting down the bot...")
            await bot.shutdown_cleanup()
        except Exception as e:
            bot.log.error(f"Unexpected error: {str(e)}")
    else:
        print("Bot failed to build or start.")
        input("Press ENTER to EXIT.")


if __name__ == "__main__":
    asyncio.run(main())
