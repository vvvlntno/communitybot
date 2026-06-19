import os

import discord
import yaml
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("MISTRAL_API_KEY")

openai = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")

GUILD_ID: int = int(os.getenv("GUILD_ID"))

MODEL = "mistral-medium-latest"
TEMPERATURE = 0.7
MAX_TOKENS = 1000
SYSTEM_PROMPT = """
You are a discord bot in an overwatch community discord.
Your role is to answer peoples question about the game.
When responding don't ask questions back and keeps the answers very concise and short!
The user message is given in the following format:
USER_NAME: MESSAGE"""

DATABASE_PROMPT = """
In the next message you will get the database in the following simple yaml format:
```
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

        message_history.append(
            {"role": "user", "content": f"{message.author}: {message.content}"}
        )

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
intents.members = True

client = discord.Client(intents=intents)

activity = discord.Activity(
    type=discord.ActivityType.watching,
    name="Helping you find friends.",
)

client = Client(
    command_prefix="/", intents=intents, activity=activity, status=discord.Status.online
)


@client.tree.command(
    name="search-interest",
    description="Search new friends with same interest!",
    guild=discord.Object(id=GUILD_ID),
)
async def search_interest(interaction: discord.Interaction, message: str):
    message_history.append(
        {"role": "user", "content": f"{interaction.user}: {message}"}
    )
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

    await interaction.response.send_message(reply)


@client.tree.command(
    name="add-interest",
    description="Add new gaming related interests to your profile!",
    guild=discord.Object(id=GUILD_ID),
)
async def add_interest(interaction: discord.Interaction, game: str):
    write_data(user=interaction.user.name, game=game)
    await interaction.response.send_message(
        f"Oh {interaction.user} cool you're interested in "
        + game
        + "I've marked that down <3"
    )


@client.tree.command(
    name="drive-topic",
    description="Add a new topic to the server!",
    guild=discord.Object(id=GUILD_ID),
)
async def drive_topic(interaction: discord.Interaction, topic: str):
    DRIVE_TOPIC_PROMPT = DATABASE_PROMPT + """
    And return the usernames and given topic the following format format:
    TOPIC;USER_NAME,USER_NAME2,...
    """
    message_history.append(
        {"role": "user", "content": f"{interaction.user}: {topic}"}
    )
    message_history.append({"role": "system", "content": DRIVE_TOPIC_PROMPT})
    database_content = read_data()
    message_history.append({"role": "system", "content": str(database_content)})

    response = openai.chat.completions.create(
        model=MODEL,
        messages=message_history,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )

    reply = response.choices[0].message.content
    topic = reply.split(";")[0]
    user_names = reply.split(";")[1].split(",")

    user_mentions = []
    guild = client.get_guild(GUILD_ID)
    for user_name in user_names:
        member = guild.get_member_named(user_name)
        if member:
            user_mentions.append(member.mention)
    
    # build message
    bot_reply = "Interested in " + topic
    for user_mention in user_mentions:
        bot_reply += " " + user_mention
    
    bot_reply += " try hitting them up!"

    message_history.append({"role": "system", "content": SYSTEM_PROMPT})

    # create channel

    #await interaction.response.send_message(bot_reply)
    channel = await guild.create_text_channel(name=topic)
    await channel.send(bot_reply)

    # write LLM generated message in chat
    TEXT_CHANNEL_PROMPT = """
    Mention people through MENTIONS and invite to to chat about TOPIC"""


    # message_history.append({"role": "system", "content": SYSTEM_PROMPT})


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
    with open("database.yaml", "w") as outfile:
        yaml.dump(data, outfile, default_flow_style=False, sort_keys=False)


client.run(BOT_TOKEN)
