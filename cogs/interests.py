import discord
from discord import app_commands
from discord.ext import commands

import config
import core.prompts as prompts
from core.db import read_data, write_data

class Interests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="search-interest", description="Search new friends with same interest!")
    async def search_interest(self, interaction: discord.Interaction, message: str):
        self.bot.message_history.extend([
            {"role": "user", "content": f"{interaction.user}: {message}"},
            {"role": "system", "content": prompts.DATABASE_PROMPT},
            {"role": "system", "content": str(read_data())}
        ])

        response = self.bot.openai.chat.completions.create(
            model=config.MODEL,
            messages=self.bot.message_history,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
        )

        reply = response.choices[0].message.content
        self.bot.message_history.append({"role": "assistant", "content": reply})
        
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

        response = self.bot.openai.chat.completions.create(
            model=config.MODEL,
            messages=self.bot.message_history,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
        )

        reply = response.choices[0].message.content
        
        parsed_topic, user_names = reply.split(";", 1)
        
        guild = self.bot.get_guild(self.bot.guild_id.id)
        mentions = [m.mention for u in user_names.split(",") if (m := guild.get_member_named(u.strip()))]

        self.bot.message_history.append({"role": "system", "content": prompts.SYSTEM_PROMPT})

        await interaction.response.send_message(f"I have created channel {parsed_topic} check it out!")
        await guild.create_text_channel(name=parsed_topic)

async def setup(bot):
    await bot.add_cog(Interests(bot))