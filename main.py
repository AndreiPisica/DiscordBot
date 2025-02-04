import discord
import os
from discord import Intents
import repository

client = discord.Client(intents=Intents.all())
active_games = {}

@client.event
async def on_voice_state_update(member, before, after):
  general_channel = member.guild.system_channel
  if general_channel is None:
    general_channel = member.guild.get_channel('general')
  if after.channel is not None:
    await general_channel.send(f'{member.name} has joined {after.channel.name}'
                               )


@client.event
async def on_presence_update(before, after):
  global active_games
  user_id = after.id
  general_channel = before.guild.system_channel
  
  if general_channel is None:
    general_channel = before.guild.get_channel(1335311911704723539)
    
  if before.status != after.status:
    if after.status == discord.Status.online:
      await general_channel.send(f'{after.name} is now online')
     
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


client.run(os.getenv('TOKEN'))
