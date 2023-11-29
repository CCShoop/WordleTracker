'''Written by Cael Shoop.'''

import os
import json
import random
import discord
import datetime
from dotenv import load_dotenv
from discord import app_commands, Intents, Client
from discord.ext import tasks

load_dotenv()


def get_time():
    ct = str(datetime.datetime.now())
    hour = int(ct[11:13])
    minute = int(ct[14:16])
    return hour, minute


def get_log_time():
    time = datetime.datetime.now().astimezone()
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


def main():
    class WordleTrackerClient(Client):
        FILENAME = 'info.json'

        class Player():
            def __init__(self, name):
                self.name = name
                self.guesses = 0
                self.winCount = 0
                self.registered = True
                self.completedToday = False
                self.succeededToday = False
                self.attachments = []

        def __init__(self, intents):
            super(WordleTrackerClient, self).__init__(intents=intents)
            self.tree = app_commands.CommandTree(self)
            self.text_channel = 0
            self.random_letter_starting = False
            self.scored_today = False
            self.players = []

        def read_json_file(self):
            '''Reads player information from the json file and puts it in the players list'''
            if os.path.exists(self.FILENAME):
                with open(self.FILENAME, 'r', encoding='utf-8') as file:
                    print(f'{get_log_time()}> Reading {self.FILENAME}')
                    data = json.load(file)
                    for firstField, secondField in data.items():
                        if firstField == 'text_channel':
                            self.text_channel = secondField['text_channel']
                            print(f'{get_log_time()}> Got text channel id of {self.text_channel}')
                        elif firstField == 'random_letter':
                            self.random_letter_starting = secondField['random_letter']
                            print(f'{get_log_time()}> Got random letter starting value of {self.random_letter_starting}')
                        else:
                            load_player = self.Player(firstField)
                            load_player.winCount = secondField['winCount']
                            load_player.guesses = secondField['guesses']
                            load_player.registered = secondField['registered']
                            load_player.completedToday = secondField['completedToday']
                            load_player.succeededToday = secondField['succeededToday']
                            self.players.append(load_player)
                            print(f'{get_log_time()}> Loaded player {load_player.name} - '
                                  f'wins: {load_player.winCount}, '
                                  f'guesses: {load_player.guesses}, '
                                  f'registered: {load_player.registered}, '
                                  f'completed: {load_player.completedToday}, '
                                  f'succeeded: {load_player.succeededToday}')
                    print(f'{get_log_time()}> Successfully loaded {self.FILENAME}')

        def write_json_file(self):
            '''Writes player information from the players list to the json file'''
            data = {}
            data['text_channel'] = {'text_channel': self.text_channel}
            data['random_letter'] = {'random_letter': self.random_letter_starting}
            for player in self.players:
                data[player.name] = {'winCount': player.winCount,
                                     'guesses': player.guesses,
                                     'registered': player.registered,
                                     'completedToday': player.completedToday,
                                     'succeededToday': player.succeededToday}
            json_data = json.dumps(data)
            print(f'{get_log_time()}> Writing {self.FILENAME}')
            with open(self.FILENAME, 'w+', encoding='utf-8') as file:
                file.write(json_data)

        async def process(self, message: discord.Message, player: Player):
            parseGuesses = message.content.split('/')
            parseGuesses = parseGuesses[0].split(' ', -1)
            player.guesses = int(parseGuesses[2])

            parseSuccess = message.content.splitlines()[-1].strip()
            player.succeededToday = parseSuccess == '🟩🟩🟩🟩🟩'
            print(f'{get_log_time()}> Player {player.name} - guesses: {player.guesses}, succeeded: {player.succeededToday}')

            player.completedToday = True
            client.write_json_file()
            message.delete()

            allPlayersGuessed = True
            for player in client.players:
                if player.registered:
                    allPlayersGuessed = allPlayersGuessed and player.completedToday
            if allPlayersGuessed:
                scoreboard = ''
                for line in client.tally_scores():
                    scoreboard += line
                await message.channel.send(scoreboard)
                for player in client.players:
                    await message.channel.send(f'__{player.name}:__')
                    for attachment in player.attachments:
                        await message.channel.send(file=attachment)
                    player.attachments.clear()

        def tally_scores(self):
            '''Sorts players and returns a list of strings to send as Discord messages'''
            if not self.players:
                print('No players to score')
                return

            print(f'{get_log_time()}> Tallying scores')
            winners = [] # list of winners - the one/those with the lowest score
            losers = [] # list of losers - people who didn't successfully guess the word
            results = [] # list of strings - the scoreboard to print out
            results.append('WORDLING COMPLETE!\n\n**SCOREBOARD:**\n')

            # sort the players
            self.players.sort(key=get_guesses)
            if self.players[0].succeededToday:
                # if the player(s) with the lowest score successfully
                # guessed the game, they are the first winner
                first_winner = self.players[0]
                winners.append(first_winner)
                # for the rest of the players, check if they're tied
                for player_it in self.players[1:]:
                    if player_it.guesses == first_winner.guesses:
                        winners.append(player_it)
                    else:
                        break

            place_counter = 1
            prev_guesses = 0
            for player in self.players:
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

    @client.event
    async def on_ready():
        client.read_json_file()
        if not midnight_call.is_running():
            midnight_call.start()
        print(f'{get_log_time()}> {client.user} has connected to Discord!')

    @client.event
    async def on_message(message):
        '''Client on_message event'''
        # message is from this bot
        if message.author == client.user:
            return

        if 'Wordle' in message.content and '/' in message.content and ('⬛' in message.content or '🟨' in message.content or '🟩' in message.content):
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

            # set channel
            client.text_channel = int(message.channel.id)
            client.write_json_file()

            # process player's results
            await client.process(message, player)
        elif message.attachments:
            for player in client.players:
                if message.author.name == player.name:
                    player.attachments.append(message.attachments)
                    message.delete()

    @client.tree.command(name='register', description='Register for Wordle tracking.')
    async def register_command(interaction):
        '''Command to register a player'''
        client.text_channel = int(interaction.channel.id)
        client.write_json_file()
        response = ''
        playerFound = False
        for player in client.players:
            if interaction.user.name.strip() == player.name.strip():
                if player.registered:
                    print(f'{get_log_time()}> User {interaction.user.name.strip()} attempted to re-register for tracking')
                    response += 'You are already registered for Wordle tracking!\n'
                else:
                    print(f'{get_log_time()}> Registering user {interaction.user.name.strip()} for tracking')
                    player.registered = True
                    client.write_json_file()
                    response += 'You have been registered for Wordle tracking.\n'
                playerFound = True
        if not playerFound:
            print(f'{get_log_time()}> Registering user {interaction.user.name.strip()} for tracking')
            player_obj = client.Player(interaction.user.name.strip())
            client.players.append(player_obj)
            client.write_json_file()
            response += 'You have been registered for Wordle tracking.\n'
        await interaction.response.send_message(response)


    @client.tree.command(name='deregister', description='Deregister from Wordle tracking. Use twice to delete saved data.')
    async def deregister_command(interaction):
        '''Command to deregister a player'''
        client.text_channel = int(interaction.channel.id)
        client.write_json_file()
        players_copy = client.players.copy()
        response = ''
        playerFound = False
        for player in players_copy:
            if player.name.strip() == interaction.user.name.strip():
                if player.registered:
                    player.registered = False
                    print(f'{get_log_time()}> Deregistered user {player.name}')
                    response += 'You have been deregistered for Wordle tracking.'
                else:
                    client.players.remove(player)
                    print(f'{get_log_time()}> Deleted data for user {player.name}')
                    response += 'Your saved data has been deleted for Wordle tracking.'
                client.write_json_file()
                playerFound = True
        if not playerFound:
            print(f'{get_log_time()}> Non-existant user {interaction.user.name.strip()} attempted to deregister')
            response += 'You have no saved data for Wordle tracking.'
        await interaction.response.send_message(response)


    @client.tree.command(name='randomletterstart', description='State a random letter to start the Wordle guessing with.')
    async def randomletterstart_command(interaction):
        '''Command to enable random letter starts'''
        client.text_channel = int(interaction.channel.id)
        client.random_letter_starting = not client.random_letter_starting
        client.write_json_file()
        print(f'{get_log_time()}> Random letter starting toggled to {client.random_letter_starting}')
        await interaction.response.send_message(f'Random letter starting has been toggled to {client.random_letter_starting}.')


    @tasks.loop(seconds=1)
    async def midnight_call():
        '''Midnight call loop task that is run every second with a midnight check.'''
        if not client.players:
            return

        hour, minute = get_time()
        if client.scored_today and hour == 0 and minute == 1:
            client.scored_today = False
        if hour != 0 or minute != 0 or client.scored_today:
            return
        client.scored_today = True

        print(f'{get_log_time()}> It is midnight, sending daily scoreboard and then mentioning registered players')
        
        channel = client.get_channel(int(client.text_channel))
        shamed = ''
        for player in client.players:
            if player.registered and not player.completedToday:
                user = discord.utils.get(client.users, name=player.name)
                if user:
                    shamed += f'{user.mention} '
                else:
                    print(f'{get_log_time()}> Failed to mention user {player.name}')
        if shamed != '':
            await channel.send(f'SHAME ON {shamed} FOR NOT DOING THE WORDLE!')
            scoreboard = ''
            for line in client.tally_scores():
                scoreboard += line
            await channel.send(scoreboard)
            for player in client.players:
                await channel.send(f'__{player.name}:__')
                for attachment in player.attachments:
                    await channel.send(file=attachment)
                player.attachments.clear()

        everyone = ''
        for player in client.players:
            player.guesses = 0
            player.completedToday = False
            player.succeededToday = False
            user = discord.utils.get(client.users, name=player.name)
            if user:
                if player.registered:
                    everyone += f'{user.mention} '
            else:
                print(f'{get_log_time()}> Failed to mention user {player.name}')
        await channel.send(f'{everyone}\nIt\'s time to do the Wordle!\nhttps://www.nytimes.com/games/wordle/index.html')
        if client.random_letter_starting:
            letter = chr(random.randint(ord("A"), ord("Z")))
            while letter == 'X':
                letter = chr(random.randint(ord("A"), ord("Z")))
            await channel.send(f'__**Your first word must start with the letter "{letter}!"**__')

    client.run(discord_token)


if __name__ == '__main__':
    main()
