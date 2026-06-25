import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import AsyncOpenAI

import core.prompts as prompts

load_dotenv()

class Client(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(
            command_prefix="/",
            intents=intents,
            activity=discord.Activity(type=discord.ActivityType.watching, name="Helping you find friends.")
        )
        self.openai = AsyncOpenAI(api_key=os.getenv("MISTRAL_API_KEY"), base_url="https://api.mistral.ai/v1")
        
        self.message_history = [{"role": "system", "content": prompts.SYSTEM_PROMPT}]
        self.guild_id = discord.Object(id=int(os.getenv("GUILD_ID")))

    async def setup_hook(self):
        await self.load_extension("cogs.listeners")
        await self.load_extension("cogs.interests")
        
        self.tree.copy_global_to(guild=self.guild_id)
        synced = await self.tree.sync(guild=self.guild_id)
        print(f"Synced {len(synced)} commands to guild {self.guild_id.id}")

if __name__ == "__main__":
    Client().run(os.getenv("BOT_TOKEN"))