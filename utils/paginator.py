from discord.ext import commands
import discord
import math

class Paginator(discord.ui.View):
    """A paginator class that makes pages with buttons to navigate through them."""
    def __init__(self, ctx, pages, title="Paginator", timeout=60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.pages = pages
        self.title = title
        self.current_page = 0
        self.message = None

    async def update_embed(self, interaction):
        """Update the embed with the current page."""
        embed = discord.Embed(
            title=f"{self.title} - Page {self.current_page + 1}/{len(self.pages)}",
            description=self.pages[self.current_page],
            color=discord.Color.blurple()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        """Create a button that goes to the previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_embed(interaction)
        else:
            await interaction.response.defer() # first page

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        """Create a button that goes to the next page."""
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_embed(interaction)
        else:
            await interaction.response.defer() # last page

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Prevent other users from interacting with the paginator."""
        return interaction.user == self.ctx.author

    async def on_timeout(self):
        """Disable the buttons after the timeout."""
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    async def start(self):
        """Start the paginator."""
        embed = discord.Embed(
            title=f"{self.title} - Page 1/{len(self.pages)}",
            description=self.pages[0],
            color=discord.Color.blurple()
        )
        self.message = await self.ctx.send(embed=embed, view=self)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        """Create a button that stops the paginator."""
        await interaction.response.defer()
        self.stop()
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)
