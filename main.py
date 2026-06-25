import os

import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI

import config
import core.prompts as prompts
from core.db import read_data, write_data

load_dotenv()

api_key = os.getenv("MISTRAL_API_KEY")

openai = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")

GUILD_ID: int = int(os.getenv("GUILD_ID"))
BOT_TOKEN: str = os.getenv("BOT_TOKEN")

message_history = [{"role": "system", "content": prompts.SYSTEM_PROMPT}]


class Client(commands.Bot):
    async def on_ready(self) -> None:
        print(f"{self.user} is ready to help!")

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
            model=config.MODEL,
            messages=message_history,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
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
    message_history.append({"role": "system", "content": prompts.DATABASE_PROMPT})
    database_content = read_data()
    message_history.append({"role": "system", "content": str(database_content)})

    response = openai.chat.completions.create(
        model=config.MODEL,
        messages=message_history,
        temperature=config.TEMPERATURE,
        max_tokens=config.MAX_TOKENS,
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
    DRIVE_TOPIC_PROMPT = (
        prompts.DATABASE_PROMPT
        + """
    And return the usernames and given topic the following format format:
    TOPIC;USER_NAME,USER_NAME2,...
    """
    )
    message_history.append({"role": "user", "content": f"{interaction.user}: {topic}"})
    message_history.append({"role": "system", "content": DRIVE_TOPIC_PROMPT})
    database_content = read_data()
    message_history.append({"role": "system", "content": str(database_content)})

    response = openai.chat.completions.create(
        model=config.MODEL,
        messages=message_history,
        temperature=config.TEMPERATURE,
        max_tokens=config.MAX_TOKENS,
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

    message_history.append({"role": "system", "content": prompts.SYSTEM_PROMPT})

    # create channel

    await interaction.response.send_message(
        f"I have created channel {topic} check it out!"
    )
    channel = await guild.create_text_channel(name=topic)
    # await channel.send(bot_reply)

    # write LLM generated message in chat
    TEXT_CHANNEL_PROMPT = """
    Mention people through MENTIONS and invite to to chat about TOPIC"""

    # message_history.append({"role": "system", "content": SYSTEM_PROMPT})


client.run(BOT_TOKEN)
