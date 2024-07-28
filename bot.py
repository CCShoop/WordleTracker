'''Written by Cael Shoop.'''

import os
import random
import asyncio
import logging
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv
from discord import (app_commands, Intents, Client, Message, Guild,
                     File, Interaction, TextChannel, SelectOption)
from discord.ui import Select, View
from discord.ext import tasks

from persistence import Persistence
from player import Player
from data import TrackerData

# .env
load_dotenv()

# Logger setup
logger = logging.getLogger("Event Scheduler")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(fmt="[%(asctime)s] [%(levelname)s\t] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

file_handler = logging.FileHandler("scheduler.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Persistence
persist = Persistence("info.json")


class Tracker:
    def __init__(self,
                 guild: Guild,
                 textChannel: TextChannel,
                 players: list,
                 prevData: TrackerData,
                 data: TrackerData):
        self.guild = guild
        self.textChannel = textChannel
        if players is not None:
            self.players = players
        else:
            self.players = []
        self.prevData = prevData
        self.data = data

    def shift_data(self) -> None:
        self.prevData = self.data
        self.data.reset()
        for player in self.players:
            player.shift_data()

    def to_dict(self) -> dict:
        payload = {}
        return payload

    @classmethod
    def from_dict(cls, payload: dict):
        try:
            textChannel = client.get_channel(payload["textChannelId"])
        except:
            textChannel = None
        return cls(
            guild=payload["guild"],
            textChannel=textChannel,
            players=[Player.from_dict(playerData) for playerData in payload["players"]]
        )

class TimezoneMenu(Select):
    def __init__(self):
        options = [
            SelectOption(label="Europe/Berlin", description="EU Central Timezone"),
            SelectOption(label="Canada/Atlantic", description="CA Atlantic Timezone"),
            SelectOption(label="US/Eastern", description="US Eastern Timezone"),
            SelectOption(label="US/Central", description="US Central Timezone"),
            SelectOption(label="US/Mountain", description="US Mountain Timezone"),
            SelectOption(label="US/Pacific", description="US Pacific Timezone"),
        ]
        super().__init__(placeholder="Select a timezone...", options=options)

    async def callback(self, interaction: Interaction):
        content = "Failed to find you in the players list. Are you registered?"
        tracker = client.get_tracker_for_channel(interaction.channel)
        for player in tracker.players:
            if player.name == interaction.user.name:
                timezone = pytz.timezone(self.values[0])
                player.resetTime = datetime.now().astimezone(tz=timezone).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                logger.info(f"Reset time for {player.name} is now {player.resetTime.isoformat()}")
                content = f"Successfully set timezone to {self.values[0]}!"
                break
        await interaction.response.send_message(content=content, ephemeral=True)


class TimezoneMenuView(View):
    def __init__(self):
        super().__init__()
        self.add_item(TimezoneMenu())


class WordleTracker(Client):
    FILENAME = "data.json"

    def __init__(self, intents: Intents) -> None:
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.trackers = []

    def get_tracker_for_channel(self, channel: TextChannel) -> Tracker:
        for tracker in self.trackers:
            if tracker.textChannel == channel:
                return tracker
        return None

    def add_tracker(self, data: dict) -> None:
        tracker = Tracker.from_dict(data)
        self.trackers.append(tracker)

    def remove_tracker(self, tracker: Tracker) -> None:
        self.trackers.remove(tracker)


discord_token = os.getenv("DISCORD_TOKEN")
client = WordleTracker(intents=Intents.all())
client.read_json_file()
client.get_previous_answers()


async def setup_hourly_call():
    if midnight_call.is_running():
        return
    curTime = datetime.now()
    nextHour = curTime.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    offset = (nextHour - curTime).total_seconds()
    await asyncio.sleep(offset)
    await midnight_call.start()


@client.event
async def on_ready():
    await setup_hourly_call()
    logger.info(f"{client.user} has connected to Discord!")

@client.event
async def on_message(message: Message):
    # Return if message isn't in a tracked channel
    tracker = client.get_tracker_for_channel(message.channel)
    if tracker is None:
        return
    # TODO

@client.tree.command(name="register", description="Register for Wordle tracking.")
async def register_command(interaction: Interaction):
    tracker = client.get_tracker_for_channel(interaction.channel)
    if tracker is None:
        return
    # TODO

@client.tree.command(name="deregister", description="Deregister from Wordle tracking. Use twice to delete saved data.")
async def deregister_command(interaction: Interaction):
    tracker = client.get_tracker_for_channel(interaction.channel)
    if tracker is None:
        return
    # TODO

@client.tree.command(name="timezone", description="Change your timezone for scoring and notification purposes.")
async def timezone_command(interaction: Interaction):
    tracker = client.get_tracker_for_channel(interaction.channel)
    if tracker is None:
        return
    # TODO

@client.tree.command(name="randomletterstart", description="State a random letter to start the Wordle guessing with.")
@app_commands.describe(random_letters="Whether you want forced starting with a random letter.")
async def randomletterstart_command(interaction: Interaction, random_letters: bool = True):
    tracker = client.get_tracker_for_channel(interaction.channel)
    if tracker is None:
        return
    # TODO

@client.tree.command(name="textchannel", description="Set the text channel for Wordle Tracker.")
async def textchannel_command(interaction: Interaction):
    client.textChannel = interaction.channel
    content = f"WordleTracker in this server will now operate in {interaction.channel.mention}."
    await interaction.response.send_message(content=content)

@tasks.loop(hours=1)
async def midnight_call():
    # TODO
    pass
