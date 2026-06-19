import os
from openai import OpenAI
import discord
from discord.ext import commands
from dotenv import load_dotenv
import yaml

load_dotenv()

api_key = os.getenv("MISTRAL_API_KEY")

openai = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")

GUILD_ID: int = int(os.getenv("GUILD_ID"))

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


class Client(commands.Bot):
    async def on_ready(self):
        print(self.user)

        try:
            guild = discord.Object(id=GUILD_ID)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to guild {guild.id}")
        except Exception as e:
            print(f"Error syncing commands: {e}")

    async def on_message(self, message):
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


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

activity = discord.Activity(
    type=discord.ActivityType.watching,
    name="Helping you find friends.",
)

client = Client(
    command_prefix="/", intents=intents, activity=activity, status=discord.Status.online
)


@client.tree.command(
    name="add-interest",
    description="Add new gaming related interests to your profile!",
    guild=discord.Object(id=GUILD_ID),
)
async def hi(interaction: discord.Interaction, game: str):
    write_data(user=interaction.user.name, game=game)
    await interaction.response.send_message(f"Oh {interaction.user} cool you're interested in " + game + "I've marked that down <3")

def read_data():
    with open("database.yaml") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            return exc

def write_data(user: str, game: str):
    data: dict = read_data()
    try:
        if game not in data[user]:
            data[user].append(game)
    except KeyError:
        data.update({user: [game]})
    with open('database.yaml', 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False, sort_keys=False)
    


client.run(BOT_TOKEN)