import discord
from discord import app_commands
from discord.ext import commands

import config
import core.prompts as prompts
from core.db import read_data, write_data

class Interests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_mentions(self, user_names: list[str]) -> list[str]:
        guild = self.bot.get_guild(self.bot.guild_id.id)
        return [m.mention for name in user_names if (m := guild.get_member_named(name.strip()))]

    @app_commands.command(name="search-interest", description="Search new friends with same interest!")
    async def search_interest(self, interaction: discord.Interaction, message: str):
        db_content = read_data()
        self.bot.message_history.extend([
            {"role": "user", "content": f"{interaction.user}: {message}"},
            {"role": "system", "content": prompts.DATABASE_PROMPT},
            {"role": "system", "content": str(db_content)}
        ])

        response = await self.bot.openai.chat.completions.create(
            model=config.MODEL,
            messages=self.bot.message_history,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
        )

        reply = response.choices[0].message.content
        self.bot.message_history.append({"role": "assistant", "content": reply})
        
        if isinstance(db_content, dict):
            guild = self.bot.get_guild(self.bot.guild_id.id)
            for name in db_content.keys():
                if name in reply and (member := guild.get_member_named(name)):
                    reply = reply.replace(name, member.mention)

        # Back to standard send_message
        await interaction.response.send_message(reply)

    @app_commands.command(name="add-interest", description="Add new gaming related interests to your profile!")
    async def add_interest(self, interaction: discord.Interaction, game: str):
        write_data(user=interaction.user.name, game=game)
        await interaction.response.send_message(f"Oh {interaction.user} cool you're interested in {game} I've marked that down <3")

    @app_commands.command(name="drive-topic", description="Add a new topic to the server!")
    async def drive_topic(self, interaction: discord.Interaction, topic: str):
        drive_prompt = prompts.DATABASE_PROMPT + "\nAnd return the usernames and given topic the following format format:\nTOPIC;USER_NAME,USER_NAME2,..."
        
        self.bot.message_history.extend([
            {"role": "user", "content": f"{interaction.user}: {topic}"},
            {"role": "system", "content": drive_prompt},
            {"role": "system", "content": str(read_data())}
        ])

        # Awaiting the async client
        response = await self.bot.openai.chat.completions.create(
            model=config.MODEL,
            messages=self.bot.message_history,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
        )

        reply = response.choices[0].message.content
        parsed_topic, user_names = reply.split(";", 1)
        
        mentions = self.get_mentions(user_names.split(","))
        bot_reply = f"Interested in {parsed_topic}: {' '.join(mentions)} try hitting them up!"

        self.bot.message_history.append({"role": "system", "content": prompts.SYSTEM_PROMPT})

        await interaction.response.send_message(f"I have created channel {parsed_topic} check it out!")
        
        guild = self.bot.get_guild(self.bot.guild_id.id)
        channel = await guild.create_text_channel(name=parsed_topic)
        await channel.send(bot_reply)

async def setup(bot):
    await bot.add_cog(Interests(bot))