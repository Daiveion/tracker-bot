import discord
from discord.ext import commands, tasks
import datetime

ShoutoutsChannelID = 1338257302230401055

class Shoutouts(commands.Cog):  
    def __init__(self, bot):
        self.bot = bot  
        self.hello_world_task.start()  # Start the background task when the cog loads

    def cog_unload(self):
        """Stops the task when the cog is unloaded"""
        self.hello_world_task.cancel()

    @tasks.loop(minutes=1)  # Check every minute
    async def hello_world_task(self):
        now = datetime.datetime.utcnow()  # Get current time in UTC
        if now.weekday() == 0 and now.hour == 12 and now.minute == 0:  # Monday 12:00 UTC
            await self.send_hello_world()

    @hello_world_task.before_loop
    async def before_hello_world_task(self):
        """Waits until the bot is ready before starting the loop"""
        await self.bot.wait_until_ready()

    async def send_hello_world(self, ctx=None):
        """Function to send 'Hello, world!' message"""
        channel = self.bot.get_channel(ShoutoutsChannelID)  # Replace with your channel ID
        if channel:
            await channel.send("Hello, world! 🌍")
            if ctx:  # If called by a command, send confirmation
                await ctx.send("Message sent!")

    @commands.command(name="supdate")  # Command to manually trigger the message
    async def send_update(self, ctx):
        """Command that allows users to manually trigger the message"""
        await self.send_hello_world(ctx)

async def setup(bot):
    await bot.add_cog(Shoutouts(bot))  # Add this cog to the bot
