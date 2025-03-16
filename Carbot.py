import discord
from discord.ext import commands
import json

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="đ", intents=intents)

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
USE_TEST_MODE = False  # Change this to False for production/pushing to main branch
guild_id = config["test_guild_id"] if USE_TEST_MODE else config["main_guild_id"]
ReportChannelID = config["test_ReportChannelID"] if USE_TEST_MODE else config["main_ReportChannelID"]
TrackedVoiceChannelID = config["test_TrackedVoiceChannelID"] if USE_TEST_MODE else config["main_TrackedVoiceChannelID"]
BotToken = config["test_token"] if USE_TEST_MODE else config["main_token"]

bot.run(BotToken)