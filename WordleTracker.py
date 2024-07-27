'''Written by Cael Shoop.'''

import os
import json
import random
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv
from discord import (app_commands, Intents, Client, File, Message,
                     Interaction, TextChannel, SelectOption, utils)
from discord.ui import Select, View
from discord.ext import tasks

load_dotenv()


def get_log_time():
    time = datetime.now().astimezone()
    output = ''
    if time.hour < 10:
        output += '0'
    output += f'{time.hour}:'
    if time.minute < 10:
        output += '0'
    output += f'{time.minute}:'
    if time.second < 10:
        output += '0'
    output += f'{time.second}'
    return output


def get_guesses(player):
    return player.guesses


def is_dst(dt=None, timezone="America/New_York"):
    timezone = pytz.timezone(timezone)
    if dt is None:
        dt = datetime.now().astimezone(tz=timezone)
    timezone_aware_date = timezone.localize(dt, is_dst=False)
    return timezone_aware_date.tzinfo._dst.seconds != 0


class TimezoneMenu(Select):
    def __init__(self):
        options = [
            SelectOption(label='Europe/Berlin', description='EU Central Timezone'),
            SelectOption(label='Canada/Atlantic', description='CA Atlantic Timezone'),
            SelectOption(label='US/Eastern', description='US Eastern Timezone'),
            SelectOption(label='US/Central', description='US Central Timezone'),
            SelectOption(label='US/Mountain', description='US Mountain Timezone'),
            SelectOption(label='US/Pacific', description='US Pacific Timezone'),
        ]
        super().__init__(placeholder='Select a timezone...', options=options)

    async def callback(self, interaction: Interaction):
        content = 'Failed to find you in the players list. Are you registered?'
        for player in client.players:
            if player.name == interaction.user.name:
                timezone = pytz.timezone(self.values[0])
                player.resetTime = datetime.now().astimezone(tz=timezone).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                print(f'{get_log_time()}> reset time for {player.name} is now {player.resetTime.isoformat()}')
                content = f'Successfully set timezone to {self.values[0]}!'
                break
        await interaction.response.send_message(content=content, ephemeral=True)


class TimezoneMenuView(View):
    def __init__(self):
        super().__init__()
        self.add_item(TimezoneMenu())


class WordleTrackerClient(Client):
    FILENAME = 'info.json'

    class Player():
        def __init__(self, name):
            self.name = name
            self.guesses = 0
            self.newGuesses = 0
            self.winCount = 0
            self.registered = True
            self.completedToday = False
            self.completedYesterday = False
            self.succeededToday = False
            self.succeededYesterday = False
            self.filePath = ''
            self.newFilePath = ''
            self.messageContent = ''
            self.newMessageContent = ''
            self.resetTime: datetime = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            self.sentWarning = False

        async def send_warning(self, curTime: datetime) -> None:
            if self.registered and not self.completedToday and not self.sentWarning and curTime + timedelta(hours=1) >= self.resetTime:
                user = utils.get(client.users, name=self.name)
                await user.send(f'You have one hour left to do (or skip) Wordle #{client.game_number}!')

        def past_reset_time(self, curTime: datetime) -> bool:
            if curTime >= self.resetTime:
                return True
            return False

        def shift_data(self) -> None:
            self.guesses = self.newGuesses
            self.newGuesses = 0
            self.completedYesterday = self.completedToday
            self.completedToday = False
            self.succeededYesterday = self.succeededToday
            self.succeededToday = False
            self.filePath = self.newFilePath
            self.newFilePath = ''
            self.messageContent = self.newMessageContent
            self.newMessageContent = ''
            self.resetTime += timedelta(days=1)
            self.sentWarning = False

        async def notify_of_wordle(self) -> None:
            user = utils.get(client.users, name=self.name)
            content = f'It\'s time to do Wordle #{client.game_number}!\n'
            content += 'https://www.nytimes.com/games/wordle/index.html\n'
            await user.send(content=content)
            if client.random_letter_starting:
                content = f'__**Your first word must start with the letter "{client.letter}"**__'
                await user.send(content=content)

    def __init__(self, intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.text_channel: TextChannel = None
        self.random_letter_starting = False
        self.current_letter = ''
        self.last_letters = ['K', 'B', 'C', 'D', 'Z', 'F']
        self.game_number: int = 0
        self.scored_today = False
        self.midnight_called = False
        self.players = []

    def read_json_file(self):
        '''Reads player information from the json file and puts it in the players list'''
        if os.path.exists(self.FILENAME):
            with open(self.FILENAME, 'r', encoding='utf-8') as file:
                print(f'{get_log_time()}> Reading {self.FILENAME}')
                data = json.load(file)
                for firstField, secondField in data.items():
                    if firstField == 'text_channel':
                        self.text_channel = self.get_channel(int(secondField['text_channel']))
                        print(f'{get_log_time()}> Got text channel id of {self.text_channel.id}')
                    elif firstField == 'game_number':
                        self.game_number = int(secondField['game_number'])
                    elif firstField == 'scored_today':
                        self.scored_today = secondField['scored_today']
                        print(f'{get_log_time()}> Scored today: {self.scored_today}')
                    elif firstField == 'random_letter':
                        self.random_letter_starting = secondField['random_letter']
                        print(f'{get_log_time()}> Got random letter starting value of {self.random_letter_starting}')
                    elif firstField == 'current_letter':
                        self.current_letter = secondField['current_letter']
                        print(f'{get_log_time()}> Got current letter as ')
                    elif firstField == 'last_letters':
                        self.last_letters.clear()
                        self.last_letters.append(secondField['0'])
                        self.last_letters.append(secondField['1'])
                        self.last_letters.append(secondField['2'])
                        self.last_letters.append(secondField['3'])
                        self.last_letters.append(secondField['4'])
                        self.last_letters.append(secondField['5'])
                        print(f'{get_log_time()}> Got last letters of {self.last_letters[0]}, {self.last_letters[1]}, {self.last_letters[2]}, {self.last_letters[3]}, {self.last_letters[4]}, {self.last_letters[5]}')
                    else:
                        player_exists = False
                        for player in self.players:
                            if firstField == player.name:
                                player_exists = True
                                break
                        if not player_exists:
                            load_player = self.Player(firstField)
                            load_player.winCount = secondField['winCount']
                            load_player.guesses = secondField['guesses']
                            try:
                                load_player.newGuesses = secondField['newGuesses']
                            except Exception as e:
                                print(f"{load_player.name} had no newGuesses, setting to 0: {e}")
                                load_player.newGuesses = 0
                            load_player.registered = secondField['registered']
                            load_player.completedToday = secondField['completedToday']
                            try:
                                load_player.completedYesterday = secondField['completedYesterday']
                            except:
                                load_player.completedYesterday = load_player.completedToday
                            load_player.succeededToday = secondField['succeededToday']
                            try:
                                load_player.succeededYesterday = secondField['succeededYesterday']
                            except:
                                load_player.succeededYesterday = load_player.succeededToday
                            try:
                                load_player.messageContent = secondField['messageContent']
                            except:
                                load_player.messageContent = ''
                            try:
                                load_player.newMessageContent = secondField['newMessageContent']
                            except:
                                load_player.newMessageContent = load_player.messageContent
                            try:
                                load_player.resetTime = datetime.fromisoformat(secondField['resetTime'])
                            except Exception as e:
                                print(f'{load_player.name} had no resetTime, defaulting to ET: {e}')
                                load_player.resetTime = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                            try:
                                load_player.sentWarning = secondField['sentWarning']
                            except Exception as e:
                                print(f'{load_player.name} had no sentWarning, defaulting to False: {e}')
                            self.players.append(load_player)
                            print(f'{get_log_time()}> Loaded player {load_player.name}\n'
                                  f'\twins: {load_player.winCount}\n'
                                  f'\tguesses: {load_player.guesses}\n'
                                  f'\tnew guesses: {load_player.newGuesses}\n'
                                  f'\tregistered: {load_player.registered}\n'
                                  f'\tcompleted today: {load_player.completedToday}\n'
                                  f'\tcompleted yesterday: {load_player.completedYesterday}\n'
                                  f'\tsucceeded today: {load_player.succeededToday}\n'
                                  f'\tsucceeded yesterday: {load_player.succeededYesterday}\n'
                                  f'\tmessage content: {load_player.messageContent}\n'
                                  f'\tnew message content: {load_player.newMessageContent}\n'
                                  f'\treset time: {load_player.resetTime.strftime("%d/%m %H:%M")}\n'
                                  f'\tsent warning: {load_player.sentWarning}')
                print(f'{get_log_time()}> Successfully loaded {self.FILENAME}')

    def write_json_file(self):
        '''Writes player information from the players list to the json file'''
        data = {}
        data['text_channel'] = {'text_channel': self.text_channel.id}
        data['game_number'] = {'game_number': self.game_number}
        data['scored_today'] = {'scored_today': self.scored_today}
        data['random_letter'] = {'random_letter': self.random_letter_starting}
        data['current_letter'] = {'current_letter': self.current_letter}
        data['last_letters'] = {'0': self.last_letters[0],
                                '1': self.last_letters[1],
                                '2': self.last_letters[2],
                                '3': self.last_letters[3],
                                '4': self.last_letters[4],
                                '5': self.last_letters[5]}
        for player in self.players:
            data[player.name] = {'winCount': player.winCount,
                                 'guesses': player.guesses,
                                 'newGuesses': player.newGuesses,
                                 'registered': player.registered,
                                 'completedToday': player.completedToday,
                                 'completedYesterday': player.completedYesterday,
                                 'succeededToday': player.succeededToday,
                                 'succeededYesterday': player.succeededYesterday,
                                 'messageContent': player.messageContent,
                                 'newMessageContent': player.newMessageContent,
                                 'resetTime': player.resetTime.isoformat(),
                                 'sentWarning': player.sentWarning}
        json_data = json.dumps(data, indent=4)
        print(f'{get_log_time()}> Writing {self.FILENAME}')
        with open(self.FILENAME, 'w+', encoding='utf-8') as file:
            file.write(json_data)

    def get_previous_answers(self) -> None:
        for player in self.players:
            if os.path.exists(f'{player.name}.png'):
                player.filePath = f'{player.name}.png'
                print(f'{get_log_time()}> Found {player.name}\'s answers as file {player.filePath}')
            if os.path.exists(f'{player.name}_new.png'):
                player.newFilePath = f'{player.name}_new.png'
                print(f'{get_log_time()}> Found {player.name}\'s new answers as file {player.newFilePath}')

    def get_new_letter(self) -> None:
        letter = chr(random.randint(ord("A"), ord("Z")))
        while letter in client.last_letters:
            letter = chr(random.randint(ord("A"), ord("Z")))
        found = False
        for i in range(len(client.last_letters)):
            if found:
                client.last_letters[i] = 'X'
                found = False
                break
            if client.last_letters[i] == 'X':
                client.last_letters[i] = letter
                found = True
        if found:
            client.last_letters[0] = 'X'
        self.current_letter = letter
        client.write_json_file()

    async def process(self, message: Message, player: Player):
        try:
            parseGuesses = message.content.split('/')
            parseGuesses[0] = parseGuesses[0].replace(' 🎉', '').replace(',', '')
            parseGuesses = parseGuesses[0].split(' ', -1)
            if int(parseGuesses[1]) != self.game_number:
                message.channel.send(f'You sent results for Wordle #{parseGuesses[1]}; I\'m currently only accepting results for Wordle #{self.game_number}.')
                return
            if parseGuesses[2] == 'X':
                player.newGuesses = 6
                player.succeededToday = False
            else:
                player.newGuesses = int(parseGuesses[2])
                player.succeededToday = True
            print(f'{get_log_time()}> Player {player.name} - newGuesses: {player.newGuesses}, succeeded: {player.succeededToday}')

            player.completedToday = True
            client.write_json_file()
            response = ''
            if player.succeededToday:
                response += f'{message.author.name} guessed the word in {player.newGuesses} guesses.\n'
            else:
                response += f'{message.author.name} did not guess the word.\n'
            if player.newFilePath == '' and not message.attachments:
                response += 'Please send a screenshot of your guesses as a spoiler attachment, **NOT** a link.'
            await message.channel.send(response)
        except:
            print(f'{get_log_time()}> User {player.name} submitted invalid result message')
            await message.channel.send(f'{player.name}, you sent a Wordle results message with invalid syntax. Please try again.')

    def tally_scores(self):
        '''Sorts players and returns a list of strings to send as Discord messages'''
        if not self.players:
            print('No players to score')
            return

        print(f'{get_log_time()}> Tallying guesses')
        winners = []  # list of winners - the one/those with the lowest score
        losers = []  # list of losers - people who didn't successfully guess the word
        results = []  # list of strings - the scoreboard to print out
        results.append(f'WORDLE #{self.game_number} COMPLETE!\n\n**SCOREBOARD:**\n')

        # sort the players
        wordle_players = []
        for player in self.players:
            if player.registered and player.completedYesterday:
                wordle_players.append(player)
        wordle_players.sort(key=get_guesses)
        if wordle_players[0].guesses == 6:
            for wordle_player in wordle_players:
                if wordle_player.succeededToday:
                    winners.append(wordle_player)
        else:
            if wordle_players[0].succeededToday:
                # if the player(s) with the lowest score successfully
                # guessed the game, they are the first winner
                first_winner = wordle_players[0]
                winners.append(first_winner)
                # for the rest of the players, check if they're tied
                for player_it in wordle_players[1:]:
                    if player_it.guesses == first_winner.guesses and player_it.succeededToday:
                        winners.append(player_it)
                    else:
                        break
        self.scored_today = True

        place_counter = 1
        prev_guesses = 0
        for player in wordle_players:
            if not player.registered:
                continue
            print(f'{get_log_time()}> {place_counter}. {player.name} ({player.winCount} wins) with {player.guesses} guesses')
            if player in winners:
                player.winCount += 1
                if player.winCount == 1:
                    if player.guesses == 1:
                        results.append(f'1. {player.name} (1 win) wins by guessing the word in one guess! WOW!\n')
                    else:
                        results.append(f'1. {player.name} (1 win) wins by guessing the word in {player.guesses} guesses!\n')
                else:
                    if player.guesses == 1:
                        results.append(f'1. {player.name} ({player.winCount} wins) wins by guessing the word in one guess! WOW!\n')
                    else:
                        results.append(f'1. {player.name} ({player.winCount} wins) wins by guessing the word in {player.guesses} guesses!\n')
            elif player.succeededToday:
                if player.winCount == 1:
                    results.append(f'{place_counter}. {player.name} (1 win) guessed the word in {player.guesses} guesses.\n')
                else:
                    results.append(f'{place_counter}. {player.name} ({player.winCount} wins) guessed the word in {player.guesses} guesses.\n')
            else:
                if player.winCount == 1:
                    losers.append(f'{player.name} (1 win) did not successfully guess the word.\n')
                else:
                    losers.append(f'{player.name} ({player.winCount} wins) did not successfully guess the word.\n')
            if prev_guesses != player.guesses:
                place_counter += 1
            prev_guesses = player.guesses

        self.write_json_file()
        return results + losers

    async def setup_hook(self):
        await self.tree.sync()


discord_token = os.getenv('DISCORD_TOKEN')
client = WordleTrackerClient(intents=Intents.all())
client.read_json_file()
client.get_previous_answers()


@client.event
async def on_ready():
    if not midnight_call.is_running():
        midnight_call.start()
    print(f'{get_log_time()}> {client.user} has connected to Discord!')


@client.event
async def on_message(message: Message):
    '''Client on_message event'''
    if message.author.bot:
        return
    try:
        if message.channel != client.text_channel:
            return
    except Exception as e:
        print(f'{get_log_time()}> could not check, no text_channel was set: {e}')
        client.text_channel = message.channel

    if 'Wordle' in message.content and '/' in message.content and ('⬛' in message.content or '🟨' in message.content or '🟩' in message.content):
        await message.delete()
        # no registered players
        if not client.players:
            await message.channel.send(f'{message.author.mention}, there are no registered players! Please register and resend your results to be the first.')
            return
        # find player in memory
        player: client.Player
        foundPlayer = False
        for player_it in client.players:
            if message.author.name == player_it.name:
                foundPlayer = True
                player = player_it
        # player is not registered
        if not foundPlayer:
            await message.channel.send(f'{message.author.name}, you are not registered! Please register and resend your results.')
            return
        # player has already sent results
        if player.completedToday:
            print(f'{get_log_time()}> {player.name} tried to resubmit results')
            await message.channel.send(f'{player.name}, you have already submitted your results today.')
            return

        client.write_json_file()

        # process player's results
        await client.process(message, player)

    if message.attachments and message.attachments[0].is_spoiler():
        for player in client.players:
            if message.author.name == player.name:
                if player.newFilePath == '':
                    response = f'Received image from {message.author.name}.\n'
                else:
                    response = f'Received replacement image from {message.author.name}.\n'
                player.newFilePath = f'{message.author.name}_new.png'
                with open(player.newFilePath, 'wb') as file:
                    await message.attachments[0].save(file)
                player.newMessageContent = message.content
                if not player.completedToday:
                    response += 'Please copy and send your Wordle-generated results.'
                await message.channel.send(response)
                await message.delete()
                break

    if client.scored_today:
        return
    for player in client.players:
        if player.registered and (not player.completedYesterday or player.filePath == ''):
            print(f'{get_log_time()}> Waiting for {player.name}')
            return
    await client.text_channel.edit(name=f'letter-{client.current_letter}-wordle')
    scoreboard = ''
    for line in client.tally_scores():
        scoreboard += line
    await message.channel.send(scoreboard)
    for player in client.players:
        if player.registered and player.filePath != '':
            await message.channel.send(content=f'__{player.name}:__\n{player.messageContent}', file=File(player.filePath))
            try:
                os.remove(player.filePath)
            except OSError as e:
                print(f'{get_log_time()}> Error deleting {player.filePath}: {e}')
            player.filePath = ''
            player.messageContent = ''


@client.tree.command(name='register', description='Register for Wordle tracking.')
async def register_command(interaction: Interaction):
    '''Command to register a player'''
    client.text_channel = interaction.channel
    response = ''
    playerFound = False
    view = None
    for player in client.players:
        if interaction.user.name == player.name:
            if player.registered:
                print(f'{get_log_time()}> User {interaction.user.name} attempted to re-register for tracking')
                response += 'You are already registered for Wordle tracking!\n'
            else:
                print(f'{get_log_time()}> Registering user {interaction.user.name} for tracking')
                player.registered = True
                response += 'You have been registered for Wordle tracking.\n'
            playerFound = True
    if not playerFound:
        print(f'{get_log_time()}> Registering user {interaction.user.name} for tracking')
        player_obj = client.Player(interaction.user.name)
        client.players.append(player_obj)
        response += 'You have been registered for Wordle tracking.\n'
        view = TimezoneMenuView()
    client.write_json_file()
    await interaction.response.send_message(content=response, view=view, ephemeral=True)


@client.tree.command(name='deregister', description='Deregister from Wordle tracking. Use twice to delete saved data.')
async def deregister_command(interaction: Interaction):
    '''Command to deregister a player'''
    client.text_channel = interaction.channel
    players_copy = client.players.copy()
    response = ''
    playerFound = False
    for player in players_copy:
        if player.name == interaction.user.name:
            if player.registered:
                player.registered = False
                print(f'{get_log_time()}> Deregistered user {player.name}')
                response += 'You have been deregistered for Wordle tracking.'
            else:
                client.players.remove(player)
                print(f'{get_log_time()}> Deleted data for user {player.name}')
                response += 'Your saved data has been deleted for Wordle tracking.'
            playerFound = True
    if not playerFound:
        print(f'{get_log_time()}> Non-existant user {interaction.user.name} attempted to deregister')
        response += 'You have no saved data for Wordle tracking.'
    client.write_json_file()
    await interaction.response.send_message(content=response, ephemeral=True)


@client.tree.command(name='timezone', description='Change your timezone for scoring and notification purposes.')
async def timezone_command(interaction: Interaction):
    '''Command to allow users to set their timezone'''
    print(f'{get_log_time()}> {interaction.user.name} is setting their timezone')
    content = 'Select a timezone:'
    view = TimezoneMenuView()
    await interaction.response.send_message(content=content, view=view, ephemeral=True)


@client.tree.command(name='randomletterstart', description='State a random letter to start the Wordle guessing with.')
@app_commands.describe(random_letters='Whether you want forced starting with a random letter.')
async def randomletterstart_command(interaction: Interaction, random_letters: bool = True):
    '''Command to enable random letter starts'''
    client.text_channel = interaction.channel
    client.random_letter_starting = random_letters
    client.get_new_letter()
    client.write_json_file()
    print(f'{get_log_time()}> Random letter starting set to {client.random_letter_starting}; letter is "{client.letter}"')
    if client.random_letter_starting:
        content = f'Random letter starting has been enabled; the current letter is "{client.current_letter}".'
        channelName = f'letter-{client.letter}-wordle'
    else:
        content = 'Random letter starting has been disabled.'
        channelName = 'wordle'
    await interaction.response.send_message(content=content)
    await client.text_channel.edit(name=channelName)


@tasks.loop(seconds=1)
async def midnight_call():
    '''Midnight call loop task that is run every second with a midnight check.'''
    if not client.players:
        return

    curTime = datetime.now().astimezone().replace(microsecond=0)

    # Warnings
    for player in client.players:
        await player.send_warning(curTime)

    # Update wordle number and required letter to earliest user timezone
    for player in client.players():
        if not client.midnight_called and player.past_reset_time():
            client.midnight_called = True
            client.game_number += 1
            if client.random_letter_starting:
                oldLetter = client.text_channel.name.split('-')[1]
                client.get_new_letter()
                await client.text_channel.edit(name=f'letter-{client.letter}-{oldLetter}-wordle')

    # Mention users when it passes midnight for them
    for player in client.players:
        if player.past_reset_time():
            player.shift_data()
            await player.notify_of_wordle()

    # Midnight/All answered - Ready for scoring?
    for player in client.players:
        if not player.past_reset_time(curTime) and not player.completedToday:
            return

    print(f'{get_log_time()}> Everyone is past midnight or has answered, sending daily scoreboard')

    # Score players
    shamed = ''
    for player in client.players:
        if player.registered and not player.completedToday:
            user = utils.get(client.users, name=player.name)
            if user:
                shamed += f'{user.mention} '
            else:
                print(f'{get_log_time()}> Failed to mention user {player.name}')
    if shamed != '':
        await client.text_channel.send(f'SHAME ON {shamed} FOR NOT DOING WORDLE #{client.game_number}!')
    await client.text_channel.edit(name='wordle')
    scoreboard = ''
    for line in client.tally_scores():
        scoreboard += line
    await client.text_channel.send(scoreboard)
    for player in client.players:
        if player.registered and player.filePath != '':
            await client.text_channel.send(content=f'__{player.name}:__\n{player.messageContent}', file=File(player.filePath))
            try:
                os.remove(player.filePath)
            except OSError as e:
                print(f'Error deleting {player.filePath}: {e}')
            player.filePath = ''
            player.messageContent = ''

    # Reset resetTimes
    client.scored_today = False
    everyone = ''
    for player in client.players:
        player.guesses = 0
        player.completedToday = False
        player.succeededToday = False
        player.resetTime += timedelta(days=1)
        player.sentWarning = False
        user = utils.get(client.users, name=player.name)
        if user:
            if player.registered:
                everyone += f'{user.mention} '
        else:
            print(f'{get_log_time()}> Failed to mention user {player.name}')

    client.write_json_file()

client.run(discord_token)
