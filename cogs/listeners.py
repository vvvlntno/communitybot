from discord.ext import commands
import config

class Listeners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.bot.user} is ready to help!")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        self.bot.message_history.append({"role": "user", "content": f"{message.author}: {message.content}"})

        response = await self.bot.openai.chat.completions.create(
            model=config.MODEL,
            messages=self.bot.message_history,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
        )

        reply = response.choices[0].message.content
        self.bot.message_history.append({"role": "assistant", "content": reply})
        
        await message.reply(reply)

async def setup(bot):
    await bot.add_cog(Listeners(bot))