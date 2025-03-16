import discord
from discord.ext import commands
from discord import EventStatus
from discord.ui import Button, View

import time
import datetime

import asyncio

import gspread
from google.oauth2.service_account import Credentials

import json


class GameNightCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Your existing setup code (replacing globals with instance variables)
        self.SERVICE_ACCOUNT_FILE = bot.SERVICE_ACCOUNT_FILE 
        self.SPREADSHEET_ID = bot.SPREADSHEET_ID 

        self.MaxLine = bot.MaxLine 
        self.MinTime = bot.MinTime 
        self.WaitForCoHost = bot.WaitForCoHost 

        self.is_timer_running = False
        self.members_in_vc = {}

        # Get IDs/Bot info
        with open("config.json", "r") as file:
            self.config = json.load(file)

        # Choose which token to use (main or test)
        self.guild_id = self.config["test_guild_id"] if bot.USE_TEST_MODE else self.config["main_guild_id"]
        self.ReportChannelID = self.config["test_ReportChannelID"] if bot.USE_TEST_MODE else self.config["main_ReportChannelID"]
        self.TrackedVoiceChannelID = self.config["test_TrackedVoiceChannelID"] if bot.USE_TEST_MODE else self.config["main_TrackedVoiceChannelID"]

        self.creds = Credentials.from_service_account_file(self.SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        self.client = gspread.authorize(self.creds)
        self.sheet = self.client.open_by_key(self.SPREADSHEET_ID).worksheet("Import")

        self.gamenight_message = None

        self.start_time = None
        self.end_time = None
        self.cohost = None

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Logged in as {self.bot.user}!")

        guild = self.bot.get_guild(self.guild_id)
        if guild:
            print(f"Connected to the correct guild: {guild.name} ({guild.id})")
        else:
            print("The bot is not connected to the expected guild")

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before, after):
        if after.guild.id != self.guild_id:
            return

        if before.status != after.status:
            guild = self.bot.get_guild(self.guild_id)
            if not guild:
                print(f"Unable to find the guild with ID {self.guild_id}")
                return
            
            channel = guild.get_channel(self.ReportChannelID)
            if not channel:
                print(f"Unable to find the channel with ID {self.ReportChannelID}")
                return
            
            GamenightVoiceChannel = guild.get_channel(self.TrackedVoiceChannelID)
            if not GamenightVoiceChannel:
                print(f"Unable to find the channel with ID {self.TrackedVoiceChannelID}")
                return

            host = after.creator if after.creator else None

            embed1 = discord.Embed()
            view = discord.ui.View(timeout=None)

            new_gamenight_info = None
            rounded_hours = 0
            unrounded_hours = 0
            rounded_minutes = 0
            unrounded_minutes = 0

            join_button = discord.ui.Button(label="Join as CoHost", style=discord.ButtonStyle.primary)
            remove_button = discord.ui.Button(label="Remove CoHost", style=discord.ButtonStyle.danger)

            async def join_button_callback(interaction):
                if interaction.user.id == host.id:
                    await interaction.response.send_message("You cannot assign yourself as the CoHost because you are the host!", ephemeral=True, delete_after=5)
                    return

                self.cohost = interaction.user  # Assign the new cohost
                await interaction.response.send_message(f"CoHost assigned: {self.cohost.mention}", ephemeral=True, delete_after=5)

                if self.is_timer_running:
                    new_gamenight_info = f"""
                    Gamenight Overview:
                    Name: {after.name}
                    Host: {host.display_name}
                    CoHost: {self.cohost.display_name}
                    Duration: <a:Green:1335416471521857566> Pending
                    Date: {self.start_time.strftime('%Y-%m-%d')}
                    """
                else:
                    new_gamenight_info = f"""
                    Gamenight Overview:
                    Name: {after.name}
                    Host: {host.display_name}
                    CoHost: {self.cohost.display_name}
                    Duration: {rounded_hours}h {rounded_minutes}m
                    Date: {self.start_time.strftime('%Y-%m-%d')}
                    """

                embed1.description = new_gamenight_info
                embed1.set_image(url=after.cover_image.url if after.cover_image else None)

                view = discord.ui.View(timeout=None)
                view.add_item(join_button)
                view.add_item(remove_button)
                await interaction.message.edit(embeds=[embed1], view=view)

            async def remove_button_callback(interaction):
                if self.cohost:
                    await interaction.response.send_message(f"CoHost removed: {self.cohost.mention}", ephemeral=True, delete_after=5)
                    self.cohost = None  # Remove cohost
                else:
                    await interaction.response.send_message("No CoHost to remove!", ephemeral=True, delete_after=5)

                if self.is_timer_running:
                    new_gamenight_info = f"""
                    Gamenight Overview:
                    Name: {after.name}
                    Host: {host.display_name}
                    Duration: <a:Green:1335416471521857566> Pending
                    Date: {self.start_time.strftime('%Y-%m-%d')}
                    """
                else:
                    new_gamenight_info = f"""
                    Gamenight Overview:
                    Name: {after.name}
                    Host: {host.display_name}
                    Duration: {rounded_hours}h {rounded_minutes}m
                    Date: {self.start_time.strftime('%Y-%m-%d')}
                    """
                    
                embed1.description = new_gamenight_info
                embed1.set_image(url=after.cover_image.url if after.cover_image else None)

                view = discord.ui.View(timeout=None)
                view.add_item(join_button)
                view.add_item(remove_button)
                await interaction.message.edit(embeds=[embed1], view=view)

            join_button.callback = join_button_callback
            remove_button.callback = remove_button_callback

            # --- EVENT STARTED ---
            if after.status == EventStatus.active:

                overwrite = GamenightVoiceChannel.overwrites_for(guild.default_role)
                overwrite.connect = True
                await GamenightVoiceChannel.set_permissions(guild.default_role, overwrite=overwrite)

                self.start_time = datetime.datetime.now()
                self.is_timer_running = True
                self.members_in_vc = {}

                for member in guild.members:
                    if member.voice and member.voice.channel and member.voice.channel.id == self.TrackedVoiceChannelID:
                        self.members_in_vc[member.id] = [{
                            "start_time": discord.utils.utcnow().timestamp(),
                            "total_time": 0,
                        }]
                
                GamenightInfoTable = f"""
                Gamenight Overview:
                Name: {after.name}
                Host: {host.display_name}
                Duration: <a:Green:1335416471521857566> Pending
                Date: {self.start_time.strftime('%Y-%m-%d')}
                """
                embed1.description = GamenightInfoTable

                if after.cover_image:
                    embed1.set_image(url=after.cover_image.url)

                view.add_item(join_button)
                view.add_item(remove_button)

                self.gamenight_message = await channel.send(embeds=[embed1], view=view)

            # --- EVENT ENDED ---
            elif after.status == EventStatus.completed:
                overwrite = GamenightVoiceChannel.overwrites_for(guild.default_role)
                overwrite.connect = False
                await GamenightVoiceChannel.set_permissions(guild.default_role, overwrite=overwrite)

                self.end_time = datetime.datetime.now()
                self.is_timer_running = False
                results_list = []

                for member_id, sessions in self.members_in_vc.items():
                    member = await self.fetch_member(guild, member_id)
                    total_time = sum(session["total_time"] for session in sessions)

                    if member and member.voice and member.voice.channel and member.voice.channel.id == self.TrackedVoiceChannelID:
                        last_session = sessions[-1]
                        total_time += discord.utils.utcnow().timestamp() - last_session["start_time"]

                    total_minutes = int(total_time // 60)

                    if total_minutes < self.MinTime:
                        continue

                    unrounded_hours, unrounded_remainder = divmod(int(total_time), 3600)
                    unrounded_minutes, _ = divmod(unrounded_remainder, 60)

                    rounded_hours = unrounded_hours
                    rounded_minutes = unrounded_minutes

                    if unrounded_minutes < self.MinTime:
                        rounded_minutes = 0
                    elif self.MinTime <= unrounded_minutes < 45:
                        rounded_minutes = 30
                    elif 45 <= unrounded_minutes <= 60:
                        rounded_minutes = 0
                        rounded_hours += 1
                        unrounded_hours += 1

                    results_list.append({
                        "name": member.name if member else member.display_name if member else "Unknown Member", 
                        "display_name": member.display_name if member else "Unknown Member",
                        "actual_name": member.name if member else "Unknown Member",
                        "mention": member.mention if member else f"<@{member_id}>",
                        "id": member_id,
                        "time": f"{rounded_hours}h {rounded_minutes}m",
                        "unrounded_time": f"{unrounded_hours}h {unrounded_minutes}m",
                        "unrounded_minutes": total_minutes,
                    })

                results_list = sorted(results_list, key=lambda x: x["display_name"].lower())

                participants_info = "\n".join([f"### {entry['display_name']} (ID: {entry['id']}): {entry['time']}" for entry in results_list])
                embed = discord.Embed(
                    title="Participants Overview",
                    description=participants_info,
                    color=discord.Color.blue()
                )

                event_duration_seconds = (self.end_time - self.start_time).total_seconds()

                unrounded_hours, unrounded_remainder = divmod(int(event_duration_seconds), 3600)
                unrounded_minutes, _ = divmod(unrounded_remainder, 60)

                rounded_hours = unrounded_hours
                rounded_minutes = unrounded_minutes

                if unrounded_minutes < self.MinTime:
                    rounded_minutes = 0
                elif self.MinTime <= unrounded_minutes < 45:
                    rounded_minutes = 30
                elif 45 <= unrounded_minutes <= 60:
                    rounded_minutes = 0
                    rounded_hours += 1
                    unrounded_hours += 1

                new_gamenight_info = f"""
                Gamenight Overview:
                Name: {after.name}
                Host: {host.display_name}
                CoHost: {self.cohost.display_name if self.cohost else 'None'}
                Duration: {rounded_hours}h {rounded_minutes}m
                Date: {self.start_time.strftime('%Y-%m-%d')}
                """
                embed1.description = new_gamenight_info
                embed1.set_image(url=after.cover_image.url if after.cover_image else None)
                embed1.set_thumbnail(url="https://cdn.discordapp.com/attachments/1292176893738614856/1335751326558060605/EventFinished.png?ex=67a14edd&is=679ffd5d&hm=165deeed8a3900265ff24c13b475d4ab4abc43c18c67be83a8e64093a1fbdd82&")

                view = discord.ui.View(timeout=None)
                view.add_item(join_button)
                view.add_item(remove_button)

                await self.gamenight_message.edit(embeds=[embed1], view=view)
                await channel.send(embed=embed)

                await asyncio.sleep(self.WaitForCoHost)

                self.save_results_to_google_sheets(after, host, f"{unrounded_hours}h {unrounded_hours}m", self.end_time.strftime('%Y-%m-%d'), results_list, self.cohost)

    async def fetch_member(self, guild, member_id):
        member = guild.get_member(member_id)
        if not member:
            try:
                member = await guild.fetch_member(member_id)
            except discord.NotFound:
                return None
        return member

    def save_results_to_google_sheets(self, event, host, duration_str, end_date, results_list, cohost=None):
        duration_parts = duration_str.split('h')
        gamenight_hours = int(duration_parts[0].strip()) if duration_parts[0].strip() else 0
        gamenight_minutes = int(duration_parts[1].replace('m', '').strip()) if len(duration_parts) > 1 else 0
        total_gamenight_minutes = gamenight_hours * 60 + gamenight_minutes

        rows_for_gsheets = []

        for entry in results_list:
            participant_role = "Participant"
            if entry['id'] == host.id:
                participant_role = "Host"
            elif cohost and entry['id'] == cohost.id:
                participant_role = "CoHost"

            total_minutes = entry["unrounded_minutes"]

            row = [end_date, event.name, str(event.id), total_gamenight_minutes, participant_role, entry["display_name"], str(entry["id"]), total_minutes]
            rows_for_gsheets.append(row)

        if rows_for_gsheets:
            rows_for_gsheets.sort(key=lambda x: x[5].lower())
            self.sheet.append_rows(rows_for_gsheets, value_input_option="RAW")
            print("Data successfully saved to Google Sheets (Import sheet).")
        else:
            print("No participant data to save.")

async def setup(bot):
    await bot.add_cog(GameNightCog(bot))

