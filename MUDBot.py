# MUDBot, a Discord bot that assists in playing MUD games through DMs.
# TODO FOR NEXT TIME: Try to get socket stuff working, figure out why it wasn't working the first time (probably by inspecting the example client.py

import discord
from discord.ext import commands
import asyncio
import zmq

TOKEN = "MjkyMjM3MjM3MzcyODQ2MDgx.C61HMA.tAoMm0TWxe3g_yfcJcqBxM6W52k"
PREFIX = ""
DESC = "MUDBot, a Discord bot that assists in playing MUD games through DMs." 

""" Other attributes of commands.Bot I might want to use:
	command_not_found
	command_has_no_subcommands
"""

bot = commands.Bot(command_prefix = PREFIX)
#bot.remove_command("help")
#commands = ["connect", "disconnect", "help"]
context = zmq.Context()
socket = context.socket(zmq.REQ) # In the future, I might want to use one socket for each connection, and keep them all in a list here. Of course, it's perfectly possible for me to do everything with one socket and just include the user ID in each message, but is it the best?
connected = [] # Holds the IDs of all users who are connected to a (the?) server

@bot.event
async def on_ready():
	print(DESC)
	print("Connecting to game server ... ")
	socket.connect("tcp://localhost:5555")
	print("Logged in as {0}, ID: {0.id}".format(bot.user))
	print("-------------------------------")

@bot.event
async def on_message(msg):
	# Author: msg.author, content: msg.content
	if msg.author == bot.user: # We can't have the bot talking to itself!
		return
	if msg.author.id in connected: # We process the message IFF the user is currently connected to the game server
		#await bot.send_message(msg.channel, "Author: {0.author.id}\nMessage: '{0.content}'".format(msg))
		print("Received message from {0.author}: '{0.content}'".format(msg))
		#socket.send(msg.content.encode("utf-8")) # Since I'm sending bytes instead of using send_string(), only ASCII characters are supported. This might cause problems when attempting to send messages with special characters like emojis or accents. (Emojis don't cause it to break entirely, but should still not be allowed.)
		socket.send_string(msg.content)
		await bot.send_message(msg.channel, socket.recv().decode("utf-8"))
	await bot.process_commands(msg)
	
@bot.command(pass_context = True)
async def connect(ctx):
	if ctx.message.author.id not in connected:
		await bot.say("Connecting to game server ... ")
		# Actual connecting stuff here
		connected.append(ctx.message.author.id) # This implicitly assumes the connection was successful, which is not always correct
		print("%s connected" % ctx.message.author)
		await bot.say("Connected.")
	else:
		print("Command connect failed: already connected.")
		await bot.say("You already already connected.")
	""" This should only work if the user is not connected. """
	
@bot.command(pass_context = True, aliases = ["quit"])
async def disconnect(ctx):
	if ctx.message.author.id in connected:
		await bot.say("Disconnecting from game server ... ")
		# Actual disconnecting stuff here ...
		connected.remove(ctx.message.author.id) # This implicitly assumes the disconnection was successful
		print("%s disconnected" % ctx.message.author)
		await bot.say("Disconnected.")
	else:
		print("Command disconnect failed: not connected.")
		await bot.say("You are not connected to the game server.")
	""" This should only work if the user is currently connected. """
	
@bot.event
async def on_command_error(error, ctx):
	if ctx.message.author.id not in connected and isinstance(error, commands.CommandNotFound):
		await bot.send_message(ctx.message.channel, "'%s' is not a valid MUDBot command. Try `connect` to connect to the game, or `help` to view a complete list of commands." % ctx.message.content.split()[0])

bot.run(TOKEN)

