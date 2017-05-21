# MUDBot, a Discord bot that assists in playing MUD games through DMs.

import discord
from discord.ext import commands
import asyncio
import zmq
import zmq.asyncio

TOKEN = "MjkyMjM3MjM3MzcyODQ2MDgx.C61HMA.tAoMm0TWxe3g_yfcJcqBxM6W52k"
PREFIX = ""
DESC = "MUDBot, a Discord bot that assists in playing MUD games through DMs." 
SERVER = "localhost:5555"

bot = commands.Bot(command_prefix = PREFIX)
context = zmq.Context()
socket = context.socket(zmq.REQ) # We use one socket for all connections 
never_send = ["connect", "disconnect", "quit"] # Never send these to the game server. Handle them in the bot instead
connected = [] # Holds the IDs of all users who are connected to the game server

async_context = zmq.asyncio.Context()
async_socket = async_context.socket(zmq.PULL)

@asyncio.coroutine
def recv_and_process(async_sock, sock):
	yield from async_sock.recv()
	sock.send(b"")
	print("Received message!")

@bot.event
async def on_ready():
	print(DESC)
	print("Logged into Discord as {0}, ID: {0.id}".format(bot.user))
	await bot.change_presence(game = discord.Game(name="Type 'connect' or 'help'"))
	print("Connecting to game server")
	socket.connect("tcp://%s" % SERVER)
	async_socket.bind("tcp://%s" % SERVER)
	print("Waiting for messages")

@bot.event
async def on_message(msg):
	# Author: msg.author, content: msg.content
	if msg.author == bot.user: # We can't have the bot talking to itself!
		return
	if msg.author.id in connected and msg.content not in never_send: # Only process the message if the user is connected to the game server
		print("Message from {0.author}: '{0.content}'".format(msg))
		# Send a multipart message with 2 frames: first contains the user ID, second contains the message
		socket.send(msg.author.id.encode("utf-8"), zmq.SNDMORE)
		socket.send(msg.content.encode("utf-8")) # Only ASCII characters are supported with send(). This might cause problems with special characters like emojis or accents.
		await bot.send_message(msg.channel, socket.recv().decode("utf-8"))
	await bot.process_commands(msg)

@bot.command(pass_context = True)
async def connect(ctx):
	if ctx.message.author.id not in connected:
		await bot.say("Connecting to game server...")
		socket.send(ctx.message.author.id.encode("utf-8"), zmq.SNDMORE)
		socket.send(b"connect")
		await bot.say(socket.recv().decode("utf-8"))
		connected.append(ctx.message.author.id) # This implicitly assumes the connection was successful, which may not be correct
		print("%s connected" % ctx.message.author)
	else:
		print("Command connect failed: already connected.")
		await bot.say("You are already connected.")
	
@bot.command(pass_context = True, aliases = ["quit"])
async def disconnect(ctx):
	if ctx.message.author.id in connected:
		await bot.say("Disconnecting from game server...")
		socket.send(ctx.message.author.id.encode("utf-8"), zmq.SNDMORE)
		socket.send(b"disconnect")
		socket.recv() # "Dummy" recv() call to preserve req-rep pattern
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

#bot.run(TOKEN)
loop = asyncio.get_event_loop()
try:
	asyncio.ensure_future(recv_and_process(async_socket, socket));
	loop.run_until_complete(bot.start(TOKEN))
except KeyboardInterrupt:
	loop.run_until_complete(bot.logout())
	# Cancel lingering tasks
finally:
	loop.close()

