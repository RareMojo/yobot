from utils.logger import log_debug
from cogs.Music.music_player import MusicPlayer

class MusicManager:
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def get_player(self, guild):
        """Retrieve the MusicPlayer for a guild, creating one if it doesn't exist."""
        if guild.id not in self.players:
            self.players[guild.id] = self.create_player(guild)
        return self.players[guild.id]
    
    def create_player(self, guild):
        """Method to create a MusicPlayer instance for a guild."""
        return MusicPlayer(self.bot, guild, self)
    
    def cleanup_player(self, guild_id):
        """Remove the MusicPlayer instance for a guild."""
        if guild_id in self.players:
            del self.players[guild_id]
            log_debug(self.bot, f"Cleaned up MusicPlayer for guild ID: {guild_id}")