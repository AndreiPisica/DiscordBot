import discord
import os
from discord import Intents
from discord.ext import commands
from datetime import datetime, timedelta
import repository
import asyncio
import pytz
import json
from dotenv import load_dotenv


intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

CONFIG_FILE = "config.json"
active_games = {}
mute = False
romania_tz = pytz.timezone("Europe/Bucharest")
load_dotenv()

def read_mute_status():
    """Read mute status from the local config file."""
    if not os.path.exists(CONFIG_FILE):
        return False  # Default to unmuted if the file doesn't exist
    
    with open(CONFIG_FILE, "r") as f:
        data = json.load(f)
        return data.get("mute", False)


def write_mute_status(mute):
    """Write mute status to the local config file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump({"mute": mute}, f, indent=4)

@bot.event
async def on_ready():
  global mute
  mute = read_mute_status()
  print(f"✅ Starting background task")
  bot.loop.create_task(weekly_message())  # Start the background task

@bot.command(name="bothelp")
async def help_command(ctx):
    help_message = (
        "**Bot Help**\n\n"
        "**!rankings [duration]**\n"
        "Shows the current player rankings. The duration is optional, and should be provided as a number followed by 'd' for days.\n"
        "For example: `!rankings 3d` will display rankings for the past 3 days. If omitted, it defaults to 7 days.\n\n"
        "**!mute**\n"
        "Will mute the user playing status announcements indefinitely \n\n"
        "**!unmute**\n"
        "Will unmute the user playing status announcements indefinitely \n\n"
        "Use these commands to interact with the bot."
    )
    await ctx.send(help_message)

@bot.command(name="mute")
async def muteBot(ctx):
    global mute
    write_mute_status(True)
    mute = True
    await ctx.send("🔇 Bot is now muted.")

@bot.command(name="unmute")
async def unmuteBot(ctx):
    global mute
    write_mute_status(False)
    mute = False
    await ctx.send("🔊 Bot is now unmuted.")

@bot.command(name="rankings")
async def rankings(ctx, duration: str = "7d"):
    """
    Usage: !rankings 3d   or   !rankings 1d
    If no duration is provided, defaults to 7 days.
    """
    try:
      duration = duration.strip().lower()
      if duration.endswith("d"):
          days = int(duration[:-1])
      else:
          # If the format is not correct, assume it's just a number of days.
          days = int(duration)
    except ValueError:
        await ctx.send("Invalid duration format. Please use a number followed by 'd' (e.g., 3d or 1d).")
        return
    ranking_message = await repository.get_rankings(days)
    await ctx.send(ranking_message)


@bot.event
async def on_presence_update(before, after):
  try:
    global active_games
    global mute
    user_id = after.id
    general_channel = before.guild.system_channel

    if general_channel is None:
      general_channel = before.guild.get_channel(223478400390660096)

    #if before.status != after.status:
      #if after.status == discord.Status.online:
        #await general_channel.send(f'{after.name} is now online')

    # Handle Game Start
    if before.activity != after.activity and after.activity is not None:
      game_name = after.activity.name

      # Prevent duplicate start messages
      if active_games.get(user_id) != game_name:
        active_games[user_id] = game_name  # Mark game as active
        if not mute: await general_channel.send(f'{after.name} is now playing {game_name}')
        repository.start_game_session(user_id, after.name, game_name)

    # Handle Game Stop
    elif before.activity is not None and after.activity is None:
      game_name = before.activity.name

      # Ensure game was previously tracked
      if active_games.get(user_id) == game_name:
        del active_games[user_id]  # Remove from active sessions
        repository.end_game_session(user_id, game_name)
  except Exception as err:
      print(f"Error {err}")


async def wait_until(target_time):
  """Wait until the exact target_time (with 00 milliseconds)"""
  now = datetime.now(romania_tz)
  seconds_until = (target_time - now).total_seconds()

  if seconds_until > 0:
    await asyncio.sleep(seconds_until)


async def weekly_message():
  try:
    await bot.wait_until_ready()
    while True:
      now = datetime.now(romania_tz)
      days_until_sunday = (6 - now.weekday()) % 7  # 6 = Sunday
      next_sunday = now + timedelta(days=days_until_sunday)
      target_time = romania_tz.localize(
          datetime(next_sunday.year, next_sunday.month, next_sunday.day, 20, 0,
                  0))

      print(f"Next Sunday: {target_time}")
      await wait_until(target_time)

      guild = bot.guilds[0]
      print(guild.system_channel)
      general_channel = guild.system_channel or guild.get_channel(
          223478400390660096)  # Replace with your channel ID

      if general_channel:
        await repository.get_top_3_players(general_channel)
        #await general_channel.send()
  except Exception as err:
      print(f"Error {err}")

bot.run(os.getenv('DISCORD_TOKEN'))
