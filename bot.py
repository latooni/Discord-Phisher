import discord, asyncio, asqlite, json
from discord.ext import commands
from rich.console import Console
from typing import Literal, Optional

from ticket import Confirm, View

cmd = Console()

with open("config.json") as r:
    r = json.load(r)

    DhookChannel = r["DhookChannelID"]
    Owners = r["Owners"]
    token = r["BotToken"]
    WhitelistedServers = r["WhitelistedServersIDs"]
    PremiumRoleID = r["PremiumRoleID"]
    VerifyRoleID = r["VerifyRoleID"]

class PersistentViewBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix=commands.when_mentioned_or('.'), intents=intents, status=discord.Status.online)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')

bot = PersistentViewBot()

bot.help_command = None


discord.utils.setup_logging()

tree = bot.tree

@bot.command(hidden=True)
async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    if ctx.author.id not in Owners:
        return
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


# ------------------------------------------------------------------------------------------------------- # 


@tree.command(name='premium')
async def premium(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id not in Owners:
        embed = discord.Embed(title = 'You cannot use this command in this server.')
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    async with asqlite.connect('database/database.db') as conn:
        await conn.execute("INSERT OR REPLACE INTO premium VALUES (?, ?)", (True, int(member.id)))
        await conn.commit()
        await member.add_roles(interaction.guild.get_role(PremiumRoleID))
        embed = discord.Embed(title=f"Gave {member.name} premium ✅")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command()
async def profile(interaction: discord.Interaction, member: discord.Member=None):
    if interaction.guild.id not in WhitelistedServers:
        embed = discord.Embed(title = 'You cannot use this command in this server.')
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    interaction.user if member is None else member

    async with asqlite.connect('database/database.db') as conn:
        e = await conn.fetchone("SELECT * FROM premium WHERE UserID = ?", (int(member.id)))
        r = await conn.fetchone("SELECT * FROM webhooks WHERE UserID = ?", (int(member.id)))


    embed = discord.Embed(title=f"{member.name}'s Profile")
    embed.add_field(name='Premium', value='```False```' if e is None else '```True```')

    if r is None:
        await interaction.response.send_message(embed=embed, view=Remove_Premium(member), ephemeral=True) if e is not None else await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, view=Both(member), ephemeral=True) if e is not None else await interaction.response.send_message(embed=embed, view=Show_webhook(member), ephemeral=True)


class Show_webhook(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member
    
    @discord.ui.button(label='Webhook', style=discord.ButtonStyle.gray, custom_id='webhook')
    async def Confirm(self, interaction: discord.Interaction, button: discord.Button):
        if interaction.guild.id in WhitelistedServers:
            if interaction.user.guild_permissions.administrator == True:
                async with asqlite.connect('database/database.db') as conn:
                    r = await conn.fetchone("SELECT * FROM webhooks WHERE UserID = ?", (int(self.member.id)))
                    if r is None:
                        embed = discord.Embed(title='Webhook does not exist.')
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                    embed = discord.Embed(title=f"{self.member.display_name}'s Webhook", description=f"```{r[0]}```")
                await interaction.response.send_message(embed=embed, view=Delete_webhook(self.member), ephemeral=True)
            else:
                embed = discord.Embed('You are missing permissions to view this webhook. ❌')
                await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title='You cannot use this in this server. ❌')
            await interaction.response.send_message(embed=embed, ephemeral=True)

class Both(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member
    
    @discord.ui.button(label='Webhook', style=discord.ButtonStyle.gray, custom_id='webhook')
    async def Confirm(self, interaction: discord.Interaction, button: discord.Button):
        if interaction.guild.id not in WhitelistedServers:
            if interaction.user.guild_permissions.administrator == True:
                async with asqlite.connect('database/database.db') as conn:
                    r = await conn.fetchone("SELECT * FROM webhooks WHERE UserID = ?", (int(self.member.id)))
                    if r is None:
                        embed = discord.Embed(title='Webhook does not exist.')
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                    embed = discord.Embed(title=f"{self.member.display_name}'s Webhook", description=f"```{r[0]}```")
                await interaction.response.send_message(embed=embed, view=Delete_webhook(self.member), ephemeral=True)
            else:
                embed = discord.Embed('You are missing permissions to view this webhook. ❌')
                await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title='You cannot use this in this server. ❌')
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='Remove Premium', style=discord.ButtonStyle.red, custom_id='remove_premium')
    async def Remove(self, interaction: discord.Interaction, button: discord.Button):
        if interaction.guild.id in WhitelistedServers:
            if interaction.user.guild_permissions.administrator == True:
                async with asqlite.connect('database/database.db') as conn:
                    r = await conn.fetchone("SELECT * FROM premium WHERE UserID = ?", (int(self.member.id)))
                    if r is None:
                        embed = discord.Embed(title='User does not have premium. ❌')
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                    else:
                        async with asqlite.connect('database/database.db') as conn:
                            await conn.execute("DELETE FROM premium WHERE UserID = ?", (int(self.member.id)))
                            await self.member.remove_roles(interaction.guild.get_role(PremiumRoleID))
                            embed = discord.Embed(title=f'Removed premium from {self.member.display_name}')
                            await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed('You are missing permissions to do this. ❌')
                await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title='You cannot use this in this server. ❌')
            await interaction.response.send_message(embed=embed, ephemeral=True)

class Delete_webhook(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member
    
    @discord.ui.button(label='Delete', style=discord.ButtonStyle.red, custom_id='delete')
    async def Delete(self, interaction: discord.Interaction, button: discord.Button):
        async with asqlite.connect('database/database.db') as conn:
            r = await conn.fetchone("SELECT * FROM webhooks WHERE UserID = ?", (int(self.member.id)))

        if r is None:
            embed = discord.Embed(title='Webhook does not exist.')
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        async with asqlite.connect('database/database.db') as conn:
            await conn.execute("DELETE FROM webhooks WHERE UserID = ?", (int(self.member.id)))
            embed = discord.Embed(title="Webhook has been deleted. ✅")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class Remove_Premium(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member
    
    @discord.ui.button(label='Remove Premium', style=discord.ButtonStyle.red, custom_id='remove_premium')
    async def Remove(self, interaction: discord.Interaction, button: discord.Button):
        if interaction.guild.id in WhitelistedServers:
            if interaction.user.guild_permissions.administrator == True:
                async with asqlite.connect('database/database.db') as conn:
                    r = await conn.fetchone("SELECT * FROM premium WHERE UserID = ?", (int(self.member.id)))
                    if r is None:
                        embed = discord.Embed(title='User does not have premium.')
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                    else:
                        async with asqlite.connect('database/database.db') as conn:
                            await conn.execute("DELETE FROM premium WHERE UserID = ?", (int(self.member.id)))
                            await self.member.remove_roles(interaction.guild.get_role(PremiumRoleID))
                            embed = discord.Embed(title=f'Removed premium from {self.member.display_name}')
                            await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed('You are missing permissions to do this. ❌')
                await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title='You cannot use this in this server. ❌')
            await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command()
async def verify(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild.id not in WhitelistedServers:
        embed = discord.Embed(title = 'You cannot use this command in this server.')
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await member.add_roles(interaction.guild.get_role(VerifyRoleID))
    embed = discord.Embed(title='✅ Verified', description=f"**{member.name}** has been successfully been manually verified.")
    await interaction.response.send_message(embed=embed, ephemeral=True)



async def main():
    await bot.start(token)

asyncio.run(main())