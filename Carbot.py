import discord
from discord.ext import commands
import json

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Gamenight Varaibles:

bot.MaxLine = 30  # default = 30
bot.MinTime = 15  # default = 15
bot.WaitForCoHost = 60  # default = 60

bot.SERVICE_ACCOUNT_FILE = "BotCreds.json"
bot.SPREADSHEET_ID = "1Q8x4Qa9_8k7RpjqVnojw-BDeOeTEq1gnhYmrQdvqIr4"

# Load your cogs here
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    # Load the GameNight Cog (adjusted to include the cogs folder)
    await bot.load_extension("cogs.gamenights")  # Assuming the cog file is named 'gamenights.py' and is in the 'cogs' folder
    await bot.load_extension("cogs.shoutouts")

# Get IDS/Bot info
with open("config.json", "r") as file:
    config = json.load(file)

# Choose which token to use (main or test)
bot.USE_TEST_MODE = True
BotToken = config["test_token"] if bot.USE_TEST_MODE else config["main_token"]


bot.run(BotToken)