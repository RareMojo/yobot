import sqlite3
import discord
import math
from discord.ext import commands
from utils.paginator import Paginator
from utils.logger import log_debug, log_error, log_info


class QuotesCog(commands.Cog, name="QuotesCog", description="A cog for managing quotes."):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._initialize_quotes_db()

    def _initialize_quotes_db(self):
        """Initialize the SQLite database and create the required tables."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                # Enable foreign key support
                cursor.execute('PRAGMA foreign_keys = ON;')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS quotes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        user_name TEXT NOT NULL,
                        quote_title TEXT NOT NULL,
                        quote TEXT NOT NULL,
                        author TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute(
                    'CREATE INDEX IF NOT EXISTS idx_quotes_guild_id ON quotes (guild_id)'
                )

                conn.commit()
        except sqlite3.Error as e:
            log_error(self.bot, f"Error initializing quotes database: {str(e)}")
        except Exception as e:
            log_error(self.bot, f"Error initializing quotes database: {str(e)}")

    @commands.hybrid_command(name="quote", help="Get a random quote from the database.")
    async def quote(self, ctx: commands.Context):
        """Get a random quote from the database."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute(
                    'SELECT * FROM quotes WHERE guild_id = ? ORDER BY RANDOM() LIMIT 1',
                    (ctx.guild.id,)
                )

                quote = cursor.fetchone()

                if not quote:
                    await ctx.send("No quotes found.")
                    return

                await ctx.send(f"{quote[5]} -{quote[6]}")  # quote, -author
        except sqlite3.Error as e:
            await ctx.send("An error occurred while fetching a quote. Please try again later.")
            log_error(self.bot, f"Error getting quote: {e}")
        except Exception as e:
            await ctx.send("An unexpected error occurred. Please contact the server administrator.")
            log_error(self.bot, f"Error getting quote: {e}")

    @commands.hybrid_command(name="getquote", help="Get a quote from the database by id or title or author.")
    async def get_quote(self, ctx: commands.Context, quote_id: int = None, quote_title: str = None, author: str = None):
        """Fetch a quote from the database by id or title or author."""
        try:
            provided_args = [arg for arg in [quote_id, quote_title, author] if arg is not None]
            if len(provided_args) != 1:
                await ctx.send("Please provide exactly one of quote id, title, or author.", delete_after=12)
                return

            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                if quote_id:
                    cursor.execute(
                        'SELECT * FROM quotes WHERE id = ? AND guild_id = ?',
                        (quote_id, ctx.guild.id)
                    )
                elif quote_title:
                    cursor.execute(
                        'SELECT * FROM quotes WHERE quote_title = ? AND guild_id = ?',
                        (quote_title, ctx.guild.id)
                    )
                elif author:
                    cursor.execute(
                        'SELECT * FROM quotes WHERE author = ? AND guild_id = ?',
                        (author, ctx.guild.id)
                    )
                else:
                    await ctx.send("Please provide a quote id or title or author.")
                    return

                quote = cursor.fetchone()

                if not quote:
                    await ctx.send("No quote found.")
                    return

                await ctx.send(f"{quote[5]} -{quote[6]}")  # quote, -author
        except sqlite3.Error as e:
            await ctx.send("An error occurred while fetching a quote. Please try again later.")
            log_error(self.bot, f"Error getting quote: {e}")
        except Exception as e:
            await ctx.send("An unexpected error occurred. Please contact the server administrator.")
            log_error(self.bot, f"Error getting quote: {e}")

    @commands.hybrid_command(name="addquote", help="Add a quote to the database.")
    async def add_quote(self, ctx: commands.Context, quote_title: str, quote: str, author: str):
        """Add a quote to the database."""
        try:
            if not all([quote_title, quote, author]):
                await ctx.send("Please provide a quote title, quote, and author.", delete_after=12)
                return

            invalid_chars = ['@', '#', ':', '`', '>', '<', '&']
            max_lengths = {'quote title': 256, 'quote': 2000, 'author name': 256}
            fields = {
                'quote title': quote_title,
                'quote': quote,
                'author name': author
            }

            for field_name, field_value in fields.items():
                if len(field_value) > max_lengths[field_name]:
                    await ctx.send(f"{field_name.capitalize()} is too long. Please keep it under {max_lengths[field_name]} characters.", delete_after=12)
                    return
                if any(char in field_value for char in invalid_chars):
                    await ctx.send(f"{field_name.capitalize()} contains invalid characters. Please remove them.", delete_after=12)
                    return

            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute(
                    'INSERT INTO quotes (guild_id, user_id, user_name, quote_title, quote, author) VALUES (?, ?, ?, ?, ?, ?)',
                    (
                        ctx.guild.id,
                        ctx.author.id,
                        ctx.author.display_name,
                        quote_title,
                        quote,
                        author
                    )
                )

                conn.commit()

                await ctx.send(f"Quote added for {author} by {ctx.author.mention} with title: {quote_title}\n**Quote ID:** {cursor.lastrowid}")
                log_info(self.bot, f"Quote added by {ctx.author}.")
        except sqlite3.Error as e:
            await ctx.send("An error occurred while adding a quote. Please try again later.")
            log_error(self.bot, f"Error adding quote: {e}")
        except Exception as e:
            await ctx.send("An unexpected error occurred. Please contact the server administrator.")
            log_error(self.bot, f"Error adding quote: {e}")

    @commands.hybrid_command(name="delquote", help="Delete a quote from the database by id or title.")
    @commands.has_guild_permissions(manage_messages=True)
    async def del_quote(self, ctx: commands.Context, quote_id: int = None, quote_title: str = None):
        """Delete a quote from the database by id or title."""
        try:
            provided_args = [arg for arg in [quote_id, quote_title] if arg is not None]
            if len(provided_args) != 1:
                await ctx.send("Please provide exactly one of quote id or title.", delete_after=12)
                return
            
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                if quote_id:
                    cursor.execute(
                        'DELETE FROM quotes WHERE id = ? AND guild_id = ?',
                        (quote_id, ctx.guild.id)
                    )
                elif quote_title:
                    cursor.execute(
                        'DELETE FROM quotes WHERE quote_title = ? AND guild_id = ?',
                        (quote_title, ctx.guild.id)
                    )
                else:
                    await ctx.send("Please provide a quote id or title.")
                    return

                conn.commit()
                
                if cursor.rowcount == 0:
                    await ctx.send("No quote found to delete.")
                    return

                await ctx.send(f"**Quote deleted.**\n\nRemoved: `{quote_id if quote_id else quote_title}`")
                log_info(self.bot, f"Quote deleted by {ctx.author}.")
        except sqlite3.Error as e:
            await ctx.send("An error occurred while deleting a quote. Please try again later.")
            log_error(self.bot, f"Error deleting quote: {e}")
        except Exception as e:
            await ctx.send("An unexpected error occurred. Please contact the server administrator.")
            log_error(self.bot, f"Error deleting quote: {e}")
    
    @commands.hybrid_command(name="listquotes", help="List all quotes in a list by id and title.")
    async def list_quotes(self, ctx: commands.Context):
        """List all quotes in a list by id and title in an embed, if there are more than 10 lines, use buttons to change pages."""
        try:
            with sqlite3.connect(self.bot.data_dir / 'server_stats.db') as conn:
                cursor = conn.cursor()

                cursor.execute(
                    'SELECT id, quote_title FROM quotes WHERE guild_id = ?',
                    (ctx.guild.id,)
                )

                quotes = cursor.fetchall()

                if not quotes:
                    await ctx.send("No quotes found.")
                    return

                # to make discord happy, 10 per page
                quotes_per_page = 10
                total_pages = math.ceil(len(quotes) / quotes_per_page)
                pages = []

                for i in range(total_pages):
                    start = i * quotes_per_page
                    end = start + quotes_per_page
                    page_quotes = quotes[start:end]
                    quotes_list = "\n".join([f"**{quote[0]}** - {quote[1]}" for quote in page_quotes])
                    pages.append(quotes_list)
                    
                if total_pages == 1:
                    embed = discord.Embed(
                        title="Quotes",
                        description=pages[0],
                        color=discord.Color.blue()
                    )
                    await ctx.send(embed=embed)
                else:    
                    paginator = Paginator(ctx, pages, title="Quotes")
                    await paginator.start()
        except sqlite3.Error as e:
            await ctx.send("An error occurred while listing quotes. Please try again later.")
            log_error(self.bot, f"Error listing quotes: {e}")
        except Exception as e:
            await ctx.send("An unexpected error occurred. Please contact the server administrator.")
            log_error(self.bot, f"Error listing quotes: {e}")


async def setup(bot: commands.Bot):
    try:
        await bot.add_cog(QuotesCog(bot))
        log_debug(bot, "QuotesCog loaded.")
    except Exception as e:
        log_error(bot, f"Error loading QuotesCog: {str(e)}")
