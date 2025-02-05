import discord
import os
from discord import Intents
from datetime import datetime, timedelta
import repository
import asyncio
import pytz
from dotenv import load_dotenv

client = discord.Client(intents=Intents.all())
active_games = {}
romania_tz = pytz.timezone("Europe/Bucharest")
load_dotenv()

@client.event
async def on_ready():
  print(f"✅ Starting background task")
  client.loop.create_task(weekly_message())  # Start the background task


@client.event
async def on_presence_update(before, after):
  global active_games
  user_id = after.id
  general_channel = before.guild.system_channel

  if general_channel is None:
    general_channel = before.guild.get_channel(1335311911704723539)

  #if before.status != after.status:
    #if after.status == discord.Status.online:
      #await general_channel.send(f'{after.name} is now online')

  # Handle Game Start
  if before.activity != after.activity and after.activity is not None:
    game_name = after.activity.name

    # Prevent duplicate start messages
    if active_games.get(user_id) != game_name:
      active_games[user_id] = game_name  # Mark game as active
      await general_channel.send(f'{after.name} is now playing {game_name}')
      repository.start_game_session(user_id, after.name, game_name)

  # Handle Game Stop
  elif before.activity is not None and after.activity is None:
    game_name = before.activity.name

    # Ensure game was previously tracked
    if active_games.get(user_id) == game_name:
      del active_games[user_id]  # Remove from active sessions
      repository.end_game_session(user_id, game_name)


async def wait_until(target_time):
  """Wait until the exact target_time (with 00 milliseconds)"""
  now = datetime.now(romania_tz)
  seconds_until = (target_time - now).total_seconds()

  if seconds_until > 0:
    await asyncio.sleep(seconds_until)


async def weekly_message():

  await client.wait_until_ready()

  while True:
    now = datetime.now(romania_tz)
    days_until_sunday = (6 - now.weekday()) % 7  # 6 = Sunday
    next_sunday = now + timedelta(days=days_until_sunday)
    target_time = romania_tz.localize(
        datetime(next_sunday.year, next_sunday.month, next_sunday.day, 20, 0,
                 0))

    print(f"Next Sunday: {target_time}")
    await wait_until(target_time)

    guild = client.guilds[0]
    print(guild.system_channel)
    general_channel = guild.system_channel or guild.get_channel(
        1335311911704723539)  # Replace with your channel ID

    if general_channel:
      await repository.get_top_3_players(general_channel)
      #await general_channel.send()


client.run(os.getenv('DISCORD_TOKEN'))
