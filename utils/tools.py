
import discord
import matplotlib.pyplot as plt
import numpy as np
import json
import traceback
import asyncio
from discord.ext import commands
from discord import Forbidden, HTTPException, NotFound
from io import BytesIO
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable


async def welcome_to_bot(bot: commands.Bot) -> None:
    """
    Prints bot instance details and a welcome message.
    Args:
      bot (Bot): The bot instance.
    Returns:
      None
    Examples:
      >>> welcome_to_bot(bot)
      Bot Instance Details:
      Display name: BotName
      Presence: Playing a game
      Linked with Guild | ID: 123456789
      Bot is online and ready.
      Welcome to BotName!
      Be sure to check out the documentation at the GitHub repository.
      Type 'help' for a list of terminal commands.
    """
    bot_name = bot.config.get("bot_name")
    presence = bot.config.get("presence")
    owner_name = bot.config.get("owner_name")

    try:
        bot.log.debug("Starting welcome_to_bot function...")
        bot.log.info("Bot Instance Details:")
        bot.log.info(f"Display name: {bot_name}")
        bot.log.info(f"Presence: {presence}")

        for guild in bot.guilds:
            bot.log.info(f"Linked with {guild} | ID: {guild.id}")

        bot.log.info("Bot is online and ready.")

        if bot.config.get("update_bot") == False:
            bot.log.info(f"Welcome back to {bot_name}, {owner_name}!")
            bot.log.info("Type 'help' for a list of terminal commands.")
        else:
            bot.log.info(f"Welcome to {bot_name}!")
            bot.log.info(
                "Be sure to check out the documentation at the GitHub repository."
            )
            bot.log.info("Type 'help' for a list of terminal commands.")

    except Exception as e:
        bot.log.error(f"Error in welcome_to_bot function: {str(e)}")


def get_new_config():
    """
    Generates a new configuration dictionary.
    Args:
      None
    Returns:
      dict: A new configuration dictionary.
    Examples:
      >>> get_new_config()
      {
          "owner_name": "",
          "owner_id": "",
          "prefix": "",
          "bot_name": "",
          "presence": "",
          "music_volume": 25,
          "music_channel_ids": ["", ""],
          "ffmpeg": "",
          "log_level": "INFO",
          "update_bot": True,
      }
    """
    return {
        "owner_name": input("Owner Name: "),
        "owner_id": int(input("Owner ID: ")),
        "prefix": "/",
        "bot_name": input("Bot Name: "),
        "presence": input("Presence: "),
        "music_volume": 25,
        "music_channel_ids": [int(input("Music Channel ID: ")), 12345678],
        "ffmpeg": "",
        "log_level": "INFO",
        "update_bot": True,
    }


def update_config(config_file, new_data):
    """
    Updates a configuration file with new data.
    Args:
      config_file (str): The path to the configuration file.
      new_data (dict): The new data to add to the configuration file.
    Returns:
      None
    Side Effects:
      Updates the configuration file with the new data.
    Examples:
      >>> update_config('config.json', {'update_bot': False})
    """
    with open(config_file, "r") as file:
        config_data = json.load(file)

    config_data.update(new_data)

    with open(config_file, "w") as file:
        updated_config = {**config_data, **new_data}
        json.dump(updated_config, file, indent=4)


async def update_with_discord(bot: commands.Bot) -> None:
    """
    Updates the bot's settings with Discord.
    Args:
      bot (Bot): The bot object.
    Returns:
      None
    Side Effects:
      Updates the bot's settings with Discord.
    Examples:
      >>> update_with_discord(bot)
    """
    successful = True
    bot.log.debug("Starting update_with_discord function...")
    bot.log.debug("Checking for updates to bot settings...")
    update = bot.config.get("update_bot")
    bot_name = bot.config.get("bot_name")
    presence = bot.config.get("presence")

    if update == True:
        bot.log.info("First run or changes detected!")
        bot.log.info("Setting name, presence, and avatar to config values.")
        bot.log.warning(
            "This action is rate limited, so to change it later, edit the config file."
        )
        bot.log.warning(
            "You may also manually set these attributes with the terminal.")

        try:
            with open(bot.avatar_file, "rb") as f:
                new_avatar = f.read()
                await bot.user.edit(avatar=new_avatar)
            await bot.user.edit(username=bot_name)
            await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name=presence))

        except Exception as e:
            bot.log.error("Error: {}".format(e))
            bot.log.error("Failed to synchronize bot settings with Discord.")
            bot.log.warning(
                "Bot name, avatar, or presence not changed on Discord servers."
            )
            bot.log.warning("This will be run again on next startup.")
            successful = False

        if successful == True:
            update = False
            bot.log.debug(
                "Successfully synchronized bot settings with Discord.")
            bot.config["update_bot"] = update

            with open(bot.config_file, "w") as f:
                json.dump(bot.config, f, indent=4)
    else:
        bot.log.info("Bot settings are up to date.")
        bot.log.info("Connected to Discord.")
    bot.log.debug("Exiting update_bot function...")


def get_boolean_input(bot: commands.Bot, prompt: str) -> bool:
    """
    Gets a boolean input from the user.
    Args:
      bot (Bot): The bot object.
      prompt (str): The prompt to display to the user.
    Returns:
      bool: The boolean input from the user.
    Examples:
      >>> get_boolean_input(bot, 'Would you like to download extra extensions? (y/n) ')
      True
    """
    while True:
        try:
            user_input = input(prompt)

            if user_input.lower() in ["true", "t", "yes", "y"]:
                return True

            elif user_input.lower() in ["false", "f", "no", "n"]:
                return False

            else:
                bot.log.warning("Invalid input. Try again.")

        except Exception as e:
            bot.log.error(f"Error occurred while getting boolean input: {str(e)}")
            bot.log.debug(f"Error details: {traceback.format_exc()}")
            bot.log.warning("Invalid input. Try again.")


def make_filepaths(paths: dict):
    """
    Creates file paths from a dictionary.
    Args:
      paths (dict): A dictionary of file paths.
    Returns:
      None
    Side Effects:
      Creates the file paths in the dictionary.
    Examples:
      >>> make_filepaths({'config': Path('config.json'), 'cogs': Path('cogs')})
    """
    for path in paths.values():
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)
            

def create_embed(title: str, description: str, color: discord.Color, thumbnail: str = None):
    """
    Creates a Discord embed.
    Args:
      title (str): The title of the embed.
      description (str): The description of the embed.
      color (discord.Color): The color of the embed.
      thumbnail (str): The URL of the thumbnail.
    Returns:
        discord.Embed: The Discord embed.
    Examples:
        >>> create_embed("Title", "Description", discord.Color.green())
    """
    embed = discord.Embed(title=title, description=description, color=color)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    embed.set_footer(text="  yobot | " +
                     datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') + " UTC")
    return embed


def format_time(seconds):
    """
    Formats seconds into minutes and seconds.
    Args:
      seconds (int): The number of seconds.
    Returns:
        str: The formatted time string.
    Examples:
        >>> format_time(65)
        '1:05'
    """
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes}:{seconds:02d}"


async def generate_bar_chart(ctx, data, title=None, xlabel=None, ylabel=None, group='song'):
    """
    Generates a bar chart from the given data and sends it to the channel.
    Args:
        ctx (Context): The Discord context.
        data (list): The data to plot.
        title (str): The title of the chart.
        xlabel (str): The x-axis label.
        ylabel (str): The y-axis label.
        group (str): The group to plot.
    Returns:
        None
    Examples:
        >>> await generate_bar_chart(ctx, data, title='Song Count', xlabel='Song Title', ylabel='Count', group='song')
    """
    if not data:
        await ctx.send("No data available to generate the chart.")
        return

    try:
        if group == 'song':
            labels = [row[0] for row in data]  # media_title
            values = [row[2] for row in data]  # count
        elif group == 'hour':
            # Format hour as 'HH:00'
            labels = [f"{int(row[0]):02d}:00" for row in data]
            values = [row[1] for row in data]  # count
        elif group == 'day':
            day_mapping = ['Sunday', 'Monday', 'Tuesday',
                           'Wednesday', 'Thursday', 'Friday', 'Saturday']
            # Convert day number to name
            labels = [day_mapping[int(row[0])] for row in data]
            values = [row[1] for row in data]  # count
        else:
            await ctx.send("Data format not recognized.")
            return
    except IndexError:
        await ctx.send("Data format not recognized.")
        return

    plt.figure(figsize=(10, 6))
    bars = plt.bar(labels, values, color='skyblue')
    plt.xlabel(xlabel if xlabel else '')
    plt.ylabel(ylabel if ylabel else '')
    plt.title(title if title else '')
    plt.xticks(rotation=45, ha='right')

    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval +
                 0.05, int(yval), ha='center', va='bottom')

    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()

    file = discord.File(fp=buffer, filename='bar_chart.png')

    await ctx.send(file=file)


async def generate_pie_chart(ctx, data, title=None, group='song'):
    """
    Generates a pie chart from the given data and sends it to the channel.
    Args:
        ctx (Context): The Discord context.
        data (list): The data to plot.
        title (str): The title of the chart.
        group (str): The group to plot.
    Returns:
        None
    Examples:
        >>> await generate_pie_chart(ctx, data, title='Song Count', group='song')
    """
    if not data:
        await ctx.send("No data available to generate the chart.")
        return

    try:
        if group == 'song':
            labels = [row[0] for row in data]  # media_title
            values = [row[2] for row in data]  # count
        elif group == 'hour':
            # Format hour as 'HH:00'
            labels = [f"{int(row[0]):02d}:00" for row in data]
            values = [row[1] for row in data]  # count
        elif group == 'day':
            day_mapping = ['Sunday', 'Monday', 'Tuesday',
                           'Wednesday', 'Thursday', 'Friday', 'Saturday']
            # Convert day number to name
            labels = [day_mapping[int(row[0])] for row in data]
            values = [row[1] for row in data]  # count
        else:
            await ctx.send("Data format not recognized.")
            return
    except IndexError:
        await ctx.send("Data format not recognized.")
        return

    plt.figure(figsize=(8, 8))
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.title(title if title else '')

    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()

    file = discord.File(fp=buffer, filename='pie_chart.png')

    await ctx.send(file=file)


def generate_progress_bar(progress_percentage):
    """
    Generates a progress bar with filled and unfilled blocks

    Args:
        progress_percentage (float): The percentage of the progress bar that should be filled.

    Returns:
        str: The progress bar string.
    Examples:
        >>> generate_progress_bar(0.5)
        '▰▰▰▰▰▱▱▱▱▱'
    """
    total_bars = 10
    filled_bars = int(progress_percentage * total_bars)
    return "▰" * filled_bars + "▱" * (total_bars - filled_bars)

async def join_voice_channel(bot: commands.Bot, ctx, allowed_text_channels: list):
    """
    Joins the voice channel of the user.
    Args:
        bot (Bot): The bot instance.
        ctx (Context): The Discord context.
        allowed_text_channels (list): The list of allowed text channels.
    Returns:
        VoiceClient: The voice client.
    Examples:
        >>> await join_voice_channel(bot, ctx, allowed_text_channels)
    """    
    if ctx.author.voice is None:
        await ctx.send("You need to be in a voice channel to use this command!", delete_after=12)
        return None
    elif ctx.message.channel.id not in allowed_text_channels:
        await ctx.send("You need type in the music chat to use this command!", delete_after=12)
        return None

    voice_channel = ctx.author.voice.channel
    voice_client = discord.utils.get(
        bot.voice_clients, guild=ctx.guild)

    if voice_client is None:
        try:
            voice_client = await voice_channel.connect()
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(
                bot, f"Unexpected error in join_voice_channel: {str(e)}")
            return None
    elif voice_client.channel != voice_channel:
        try:
            await voice_client.move_to(voice_channel)
        except Exception as e:
            await ctx.send(f"An unexpected error occurred:\n{str(e)}\n\nReport this to your server admin if you think this is a bug.")
            log_error(
                bot, f"Unexpected error in join_voice_channel: {str(e)}")
            return None

    return voice_client