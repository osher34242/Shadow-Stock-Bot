import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
from keep_alive import keep_alive
keep_alive()

TOKEN = "MTM1MTIxMzU2MjQ3OTI1MTQ1Ng.GyIS0c.LTRRRs4TMaUD8OGyN04wnVoJL1aNUuDb616SUU"
GUILD_ID =  1344363987978162289# Server's ID
ROLE_ID = {1344375066506301460,1350467039097126983}  # Role ID for restocking
LOG_CHANNEL_ID = 1351214938051444757  # Log channel ID
AUTHORIZED_USERS = {1180052033399705610,1312350434966372363}  # Authorized user IDs

class PrimeFNBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.messages = True
        intents.guilds = True
        intents.invites = True
        intents.message_content = True
        super().__init__(command_prefix=".", intents=intents)
        self.invite_cache = {}
        self.joined_members = set()

    async def setup_hook(self):
        guild = self.get_guild(GUILD_ID)
        if guild:
            await self.update_invite_tracker()
        self.tree.clear_commands(guild=discord.Object(id=GUILD_ID))
        self.tree.copy_global_to(guild=discord.Object(id=GUILD_ID))
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))

    async def update_invite_tracker(self):
        guild = self.get_guild(GUILD_ID)
        if guild:
            invites = await guild.invites()
            self.invite_cache = {invite.code: invite.uses for invite in invites}
        print("Updated invite tracker:", self.invite_cache)

bot = PrimeFNBot()
invite_tracker = {}

def pop_account():
    try:
        with open("stock.txt", "r") as file:
            accounts = file.read().splitlines()
        if accounts:
            account = accounts.pop(0)
            with open("stock.txt", "w") as file:
                file.write("\n".join(accounts))
            return account
    except FileNotFoundError:
        return None

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=" Made By OSHAGI"))
    print(f"Logged in as {bot.user}")
    await bot.update_invite_tracker()

@bot.event
async def on_member_join(member):
    if not member.guild:
        return

    if member.id in bot.joined_members:
        print(f"{member} rejoined. No invite counted.")
        return
    bot.joined_members.add(member.id)

    print(f"New member joined: {member}")
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    account_age = (now - member.created_at.replace(tzinfo=datetime.timezone.utc)).days
    invites_before = bot.invite_cache.copy()
    invites_after = await member.guild.invites()
    bot.invite_cache = {invite.code: invite.uses for invite in invites_after}

    print("Current invite cache:", invites_before)
    print("Invites after join:", bot.invite_cache)

    inviter = None
    for invite in invites_after:
        if invite.uses > invites_before.get(invite.code, 0):
            inviter = invite.inviter
            break

    if inviter:
        print(f"Inviter found: {inviter}")
        if account_age < 14:
            print(f"{inviter} invited an alt ({member}). No invite counted.")
        else:
            invite_tracker[inviter.id] = invite_tracker.get(inviter.id, 0) + 1
            print(f"{inviter} now has {invite_tracker[inviter.id]} invites.")
    await bot.update_invite_tracker()

@bot.tree.command(name="starfn", description="Get free Fortnite accounts!")
@app_commands.checks.has_permissions(administrator=True)
async def primefn_slash(interaction: discord.Interaction):
    await send_primefn_message(interaction)

async def send_primefn_message(interaction):
    embed = discord.Embed(
        title="Earn Fortnite Accounts",
        description=(
            "Get __FREE__ accounts for every friend you invite!\n\n"
            "**# 1 Invites = 1 Account**\n\n"
        ),
        color=discord.Color.blue()
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1345080802161066015/1350433528700993536/IMG_7527.png?ex=67d6b8bb&is=67d5673b&hm=8ac0a1f90f9bfb8a2bf17a0d4f83dbf94a8687679db3d05f736ad1c3043e2a6b&")

    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Get Account", style=discord.ButtonStyle.blurple, custom_id="get_account"))
    view.add_item(discord.ui.Button(label="Check Invites", style=discord.ButtonStyle.gray, custom_id="check_invites"))

    await interaction.response.send_message(embed=embed, view=view)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    user = interaction.user
    custom_id = interaction.data.get("custom_id", "")
    print(f"Interaction received: {custom_id} from {user}")

    if custom_id == "check_invites":
        invites = invite_tracker.get(user.id, 0)
        await interaction.response.send_message(f"You have **{invites}** invites. Start inviting friends!", ephemeral=True)

    elif custom_id == "get_account":
        invites = invite_tracker.get(user.id, 0)
        if invites < 1:
            await interaction.response.send_message("You have **0 invites**. Start inviting friends!", ephemeral=True)
        else:
            account = pop_account()
            if account:
                invite_tracker[user.id] -= 1
                await interaction.response.send_message(f"Here is your Fortnite account:\n```{account}```", ephemeral=True)
                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(f"{user.mention} generated an account.")
                print(f"{user} generated an account: {account}")
            else:
                await interaction.response.send_message("No more accounts left in stock!", ephemeral=True)

@bot.tree.command(name="restock", description="Restock stock.txt")
async def restock(interaction: discord.Interaction, file: discord.Attachment):
    if interaction.user.id not in AUTHORIZED_USERS:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return

    if file.filename.endswith(".txt"):
        content = await file.read()
        accounts = content.decode().splitlines()
        with open("stock.txt", "a") as stock_file:
            stock_file.writelines(f"{account}\n" for account in accounts)
        await interaction.response.send_message(f"Restocked with **{len(accounts)}** accounts!", ephemeral=True)
    else:
        await interaction.response.send_message("Please upload a valid .txt file.", ephemeral=True)

bot.run(TOKEN)
