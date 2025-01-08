import os
import dotenv
import discord
from discord.ext import commands

dotenv.load_dotenv()
token = os.environ["BOT_TOKEN"]
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.run(token)
