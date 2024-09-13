from utils.logger import log_debug, log_error


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

