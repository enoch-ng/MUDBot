# MUDBot, a Discord bot that assists in playing MUD games through DMs.

import discord
from discord.ext import commands
import asyncio
import zmq

TOKEN = "MjkyMjM3MjM3MzcyODQ2MDgx.C61HMA.tAoMm0TWxe3g_yfcJcqBxM6W52k"
PREFIX = ""
DESC = "MUDBot, a Discord bot that assists in playing MUD games through DMs." 

SERVER_ADDR = "127.0.0.1"
S_PORT = "5555"
R_PORT = "9999"
CHECK_SERVER_MSG_INTERVAL = 0.5

bot = commands.Bot(command_prefix = PREFIX)
context = zmq.Context()
s_socket = context.socket(zmq.REQ)
r_socket = context.socket(zmq.SUB)
never_send = ["connect", "disconnect", "quit"] # Never send these to the game server. Handle them in the bot instead
connected = [] # Holds the IDs of all users who are connected to the game server

async def handle_server_msg():
	msg = r_socket.recv(zmq.NOBLOCK).decode("utf-8")
	# The bot will send the message to all intended recipients. At the moment it will DM it to them regardless of how they choose to interact with the bot. In the future I can change it up so that it sends the message in whatever channel they last used. discord.utils.find or discord.utils.get might help with that, and maybe also the messages attribute of discord.Client
	print("Got message")

async def listen_server_msg():
	await bot.wait_until_ready()
	while not bot.is_closed:
		try:
			await handle_server_msg()
		except zmq.error.Again:
			pass
		await asyncio.sleep(CHECK_SERVER_MSG_INTERVAL)

@bot.event
async def on_ready():
	print(DESC)
	print("Logged into Discord as {0}, ID: {0.id}".format(bot.user))
	print("Connecting to game server")
	s_socket.connect("tcp://%s:%s" % (SERVER_ADDR, S_PORT))
	r_socket.connect("tcp://%s:%s" % (SERVER_ADDR, R_PORT))
	r_socket.setsockopt(zmq.SUBSCRIBE, b"")
	await bot.change_presence(game = discord.Game(name="Type 'connect' or 'help'"))
	print("Waiting for messages")

@bot.event
async def on_message(msg):
	# Author: msg.author, content: msg.content
	if msg.author == bot.user: # We can't have the bot talking to itself!
		return
	if msg.author.id in connected and msg.content not in never_send: # Only process the message if the user is connected to the game server
		print("Message from {0.author}: '{0.content}'".format(msg))
		# Send a multipart message with 2 frames: first contains the user ID, second contains the message
		s_socket.send(msg.author.id.encode("utf-8"), zmq.SNDMORE)
		s_socket.send(msg.content.encode("utf-8")) # Only ASCII characters are supported with send(). This might cause problems with special characters like emojis or accents.
		await bot.send_message(msg.channel, s_socket.recv().decode("utf-8"))
	await bot.process_commands(msg)

@bot.command(pass_context = True)
async def connect(ctx):
	if ctx.message.author.id not in connected:
		await bot.say("Connecting to game server...")
		s_socket.send(ctx.message.author.id.encode("utf-8"), zmq.SNDMORE)
		s_socket.send(b"connect")
		await bot.say(s_socket.recv().decode("utf-8"))
		connected.append(ctx.message.author.id) # This implicitly assumes the connection was successful, which may not be correct
		print("%s connected" % ctx.message.author)
	else:
		print("Command connect failed: already connected.")
		await bot.say("You are already connected.")
	
@bot.command(pass_context = True, aliases = ["quit"])
async def disconnect(ctx):
	if ctx.message.author.id in connected:
		await bot.say("Disconnecting from game server...")
		s_socket.send(ctx.message.author.id.encode("utf-8"), zmq.SNDMORE)
		s_socket.send(b"disconnect")
		s_socket.recv() # "Dummy" recv() call to preserve req-rep pattern
		connected.remove(ctx.message.author.id) # This implicitly assumes the disconnection was successful
		print("%s disconnected" % ctx.message.author)
		await bot.say("Disconnected.")
	else:
		print("Command disconnect failed: not connected.")
		await bot.say("You are not connected to the game server.")
	
@bot.event
async def on_command_error(error, ctx):
	if ctx.message.author.id not in connected and isinstance(error, commands.CommandNotFound):
		await bot.send_message(ctx.message.channel, "'%s' is not a valid MUDBot command. Type `connect` to connect to the game, or `help` to view a complete list of commands." % ctx.message.content.split()[0])

bot.loop.create_task(listen_server_msg())
bot.run(TOKEN)
