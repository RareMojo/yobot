from utils.logger import log_debug, log_error
import hashlib
from rapidfuzz import fuzz, process
import sqlite3

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord_bot.bot import Bot
    

def get_similar_titles(path, title, threshold=80):
    """Fetches song titles from the database and returns ones similar to the provided title."""
    conn = sqlite3.connect(path / 'music_stats.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT song_title, url_hash FROM user_requests")
    song_data = cursor.fetchall()
    
    similar_titles = []
    
    for song_title, url_hash in song_data:
        similarity = fuzz.ratio(title.lower(), song_title.lower())
        if similarity >= threshold:
            similar_titles.append((song_title, url_hash, similarity))
    
    conn.close()
    return similar_titles

def merge_similar_titles(song_list):
    """Merges songs that have similar titles."""
    merged_titles = {}
    
    for song_title, url_hash, similarity in song_list:
        if song_title not in merged_titles:
            merged_titles[song_title] = [(song_title, url_hash)]
        else:
            merged_titles[song_title].append((song_title, url_hash))
    
    return merged_titles

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
