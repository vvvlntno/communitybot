import os
from openai import OpenAI
import discord
from dotenv import load_dotenv
import yaml

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

DATABASE_PROMPT = """
In the next message will get the database in the following simple yaml format:
````
USER_NAME:
- INTEREST1
- INTEREST2
...

USER_NAME2:
- ...
```
Please search in the database which users are interested in the topic presented by the user.
"""

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
    
    if "interest" in message.content:
        message_history.append({"role": "user", "content": f"{message.author}: {message.content}"})
        message_history.append({"role": "system", "content": DATABASE_PROMPT})
        database_content = read_data()
        message_history.append({"role": "system", "content": str(database_content)})

        response = openai.chat.completions.create(
            model=MODEL,
            messages=message_history,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

        reply = response.choices[0].message.content

        message_history.append({"role": "assistant", "content": reply})
    else:
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

def read_data():
    with open("database.yaml") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            return exc


client.run(BOT_TOKEN)