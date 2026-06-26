import json
import discord
from discord import app_commands
from discord.ext import commands

import config
import core.prompts as prompts
from core.db import read_data, write_data, write_topic_channel

async def generate_persona(bot, topic: str) -> dict:
    resp = await bot.openai.chat.completions.create(
        model=config.MODEL,
        messages=[
            {"role": "system", "content": prompts.PERSONA_GENERATION_PROMPT},
            {"role": "user", "content": f"Topic: {topic}"}
        ],
        temperature=0.7,
        max_tokens=150,
    )
    raw = resp.choices[0].message.content.strip()
    clean_json = raw[raw.find('{'):raw.rfind('}')+1]
    try:
        data = json.loads(clean_json)
        return {
            "username": data.get("username", f"{topic.capitalize()}Gamer"),
            "personality": data.get("personality", f"A friendly gamer who loves {topic}")
        }
    except Exception:
        return {
            "username": f"{topic.capitalize()}Gamer",
            "personality": f"A friendly gamer who loves {topic}"
        }

async def generate_welcome_message(bot, topic: str, username: str, personality: str, channel_name: str) -> str:
    system_prompt = prompts.AGENT_SYSTEM_PROMPT.format(
        username=username,
        personality=personality,
        topic=topic,
        channel_name=channel_name
    )
    resp = await bot.openai.chat.completions.create(
        model=config.MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Write a short, hype welcome message introducing yourself as a member of this new channel!"}
        ],
        temperature=0.7,
        max_tokens=200,
    )
    return resp.choices[0].message.content

async def send_webhook_message(channel, username: str, content: str):
    webhooks = await channel.webhooks()
    webhook = next((w for w in webhooks if w.name == "Community Agent"), None)
    if not webhook:
        webhook = await channel.create_webhook(name="Community Agent")
    await webhook.send(
        content=content,
        username=username
    )

class Interests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_mentions(self, user_names: list[str]) -> list[str]:
        guild = self.bot.get_guild(self.bot.guild_id.id)
        return [m.mention for name in user_names if (m := guild.get_member_named(name.strip()))]

    @app_commands.command(name="search-interest", description="Search new friends with same interest!")
    async def search_interest(self, interaction: discord.Interaction, message: str):
        db_content = read_data()
        messages = [
            {"role": "system", "content": prompts.SYSTEM_PROMPT},
            {"role": "user", "content": f"{interaction.user}: {message}"},
            {"role": "system", "content": prompts.DATABASE_PROMPT},
            {"role": "system", "content": str(db_content)}
        ]

        response = await self.bot.openai.chat.completions.create(
            model=config.MODEL,
            messages=messages,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
        )

        reply = response.choices[0].message.content
        
        if isinstance(db_content, dict):
            guild = self.bot.get_guild(self.bot.guild_id.id)
            for name in db_content.keys():
                if name in reply and (member := guild.get_member_named(name)):
                    reply = reply.replace(name, member.mention)

        await interaction.response.send_message(reply)

    @app_commands.command(name="add-interest", description="Add new gaming related interests to your profile!")
    async def add_interest(self, interaction: discord.Interaction, game: str):
        write_data(user=interaction.user.name, game=game)
        await interaction.response.send_message(f"Oh {interaction.user} cool you're interested in {game} I've marked that down <3")

    @app_commands.command(name="drive-topic", description="Add a new topic to the server!")
    async def drive_topic(self, interaction: discord.Interaction, topic: str):
        await interaction.response.defer()

        # Generate persona
        persona = await generate_persona(self.bot, topic)
        username = persona["username"]
        personality = persona["personality"]

        # Create channel
        guild = interaction.guild
        channel_name = topic.lower().replace(" ", "-")
        channel = await guild.create_text_channel(name=channel_name)

        # Save channel mapping
        write_topic_channel(channel.id, topic, username, personality)

        # Generate welcome message
        welcome_msg = await generate_welcome_message(self.bot, topic, username, personality, channel_name)

        # Send welcome message via Webhook
        await send_webhook_message(channel, username, welcome_msg)

        # Initialize history
        sys_prompt = prompts.AGENT_SYSTEM_PROMPT.format(
            username=username,
            personality=personality,
            topic=topic,
            channel_name=channel_name
        )
        self.bot.channel_histories[channel.id] = [
            {"role": "system", "content": sys_prompt},
            {"role": "assistant", "content": welcome_msg}
        ]

        await interaction.followup.send(f"I have created channel {channel.mention} check it out!")

async def setup(bot):
    await bot.add_cog(Interests(bot))