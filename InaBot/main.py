import discord
import os
from dotenv import load_dotenv

load_dotenv()

#login

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

#missatge de inici
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

#missatges de resposta
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content == '!ping':
        await message.channel.send(f'Pong! 🏓')


#començar el bot


client.run(os.getenv('TOKEN'))