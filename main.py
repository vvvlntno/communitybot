import os
from openai import OpenAI
import discord
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("MISTRAL_API_KEY")

openai = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")

MODEL = "mistral-small-latest"
TEMPERATURE = 0.7
MAX_TOKENS = 100
SYSTEM_PROMPT = """
You are a discord bot in an overwatch community discord.
Your role is to answer peoples question about the game.
When responding don't ask questions back and keeps the answers very concise and short!
The user message is given in the following format:
USER_NAME: MESSAGE"""

BOT_TOKEN = os.getenv("BOT_TOKEN")

message_history = [{"role": "system", "content": SYSTEM_PROMPT}]

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(client.user)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')
        return
    
    message_history.append({"role": "user", "content": f"{message.author}: {message.content}"})

    response = openai.chat.completions.create(
        model=MODEL,
        messages=message_history,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )

    reply = response.choices[0].message.content

    message_history.append({"role": "assistant", "content": reply})

    await message.reply(reply)


client.run(BOT_TOKEN)