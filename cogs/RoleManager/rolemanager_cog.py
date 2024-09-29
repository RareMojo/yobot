import discord
from discord.ext import commands
from discord.ui import View, Button, Select
from utils.logger import log_debug, log_error, log_info
import json
import os

class RoleManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.weapon_roles = {
            'Sword and Shield': '🛡️',
            'Staff': '🔮',
            'Wand': '✨',
            'Bow': '🏹',
            'Crossbow': '🎯',
            'Greatsword': '🔪',
            'Daggers': '⚔️'
        }

        self.game_roles = {
            'Tank': '🛡️',
            'Healer': '❤️',
            'DPS': '🗡️'
        }

        self.game_styles = {
            'PvE': '🐲',
            'PvP': '☠️',
            'PvX': '🌐'
        }

        self.rolemanager_channel_ids = self.bot.config['rolemanager_channel_ids']

    @commands.Cog.listener()
    async def on_ready(self):
        await self.setup_role_messages()

    async def setup_role_messages(self):
        for channel_id in self.rolemanager_channel_ids:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                log_debug(f"Channel with ID {channel_id} not found.")
                continue

            await self.send_weapon_embed(channel)
            await self.send_role_embed(channel)
            await self.send_style_embed(channel)

    def create_embed(self, title, description):
        embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
        return embed

    async def send_weapon_embed(self, channel):
        description = "Choose up to **2 weapons** by selecting them from the menu below."
        embed = self.create_embed("Select Your Class", description)
        options = [discord.SelectOption(label=role, emoji=emoji) for role, emoji in self.weapon_roles.items()]
        select = Select(placeholder="Select your weapons...", min_values=1, max_values=2, options=options)

        async def weapon_callback(interaction):
            await self.update_roles(interaction.user, interaction.data['values'], self.weapon_roles)
            await interaction.response.send_message("Your weapon roles have been updated!", ephemeral=True)

        select.callback = weapon_callback
        view = View()
        view.add_item(select)
        await channel.send(embed=embed, view=view)

    async def send_role_embed(self, channel):
        description = "Choose **1 role** by clicking the button below."
        embed = self.create_embed("Select Your Role", description)
        buttons = [Button(label=role, emoji=emoji) for role, emoji in self.game_roles.items()]

        for button in buttons:
            async def role_callback(interaction, button=button):
                await self.update_roles(interaction.user, [button.label], self.game_roles)
                await interaction.response.send_message("Your game role has been updated!", ephemeral=True)
            button.callback = role_callback

        view = View()
        for button in buttons:
            view.add_item(button)
        await channel.send(embed=embed, view=view)

    async def send_style_embed(self, channel):
        description = "Choose **1 style** by clicking the button below."
        embed = self.create_embed("Select Your Style", description)
        buttons = [Button(label=style, emoji=emoji) for style, emoji in self.game_styles.items()]

        for button in buttons:
            async def style_callback(interaction, button=button):
                await self.update_roles(interaction.user, [button.label], self.game_styles)
                await interaction.response.send_message("Your game style has been updated!", ephemeral=True)
            button.callback = style_callback

        view = View()
        for button in buttons:
            view.add_item(button)
        await channel.send(embed=embed, view=view)

    async def update_roles(self, member, selected_roles, role_dict):
        guild_roles = {role.name: role for role in member.guild.roles}
        role_names = role_dict.keys()

        roles_to_remove = [guild_roles[role_name] for role_name in role_names if role_name in guild_roles and guild_roles[role_name] in member.roles]
        await member.remove_roles(*roles_to_remove)

        roles_to_add = [guild_roles[role_name] for role_name in selected_roles if role_name in guild_roles]
        await member.add_roles(*roles_to_add)


async def setup(bot: commands.Bot):
    try:
        await bot.add_cog(RoleManager(bot))
        log_debug(bot, "RoleManager loaded.")
    except Exception as e:
        log_error(bot, f"Error loading RoleManager: {str(e)}")
