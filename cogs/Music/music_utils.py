from utils.logger import log_debug, log_error
import hashlib
from rapidfuzz import fuzz, process
import sqlite3
import re
import requests

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord_bot.bot import Bot


def find_similar_song_title(cursor, new_title):
    cursor.execute(
        "SELECT song_title FROM user_actions WHERE action = 'request'")
    existing_titles = [row[0] for row in cursor.fetchall()]

    match = process.extractOne(
        new_title, existing_titles, scorer=fuzz.ratio, score_cutoff=85)
    if match:
        return match[0]
    return None


def generate_progress_bar(progress_percentage):
    """Generates a progress bar string."""
    total_bars = 10
    filled_bars = int(progress_percentage * total_bars)
    return "▰" * filled_bars + "▱" * (total_bars - filled_bars)


def format_time(seconds):
    """Formats time in mm:ss format."""
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{int(minutes):02}:{int(seconds):02}"
