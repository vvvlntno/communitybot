import json
import asyncio
from discord.ext import commands
import config
import core.prompts as prompts
from core.db import read_data, write_data

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

        self.bot.message_history.append({"role": "user", "content": f"{message.author.name}: {message.content}"})

        chat_task = self.bot.openai.chat.completions.create(
            model=config.MODEL,
            messages=self.bot.message_history,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
        )

        extract_task = self.bot.openai.chat.completions.create(
            model=config.MODEL,
            messages=[
                {"role": "system", "content": prompts.EXTRACTION_PROMPT},
                {"role": "user", "content": message.content}
            ],
            temperature=0.0,
            max_tokens=50,
        )

        chat_resp, extract_resp = await asyncio.gather(chat_task, extract_task)

        reply = chat_resp.choices[0].message.content
        self.bot.message_history.append({"role": "assistant", "content": reply})

        raw_extract = extract_resp.choices[0].message.content
        clean_json = raw_extract[raw_extract.find('{'):raw_extract.rfind('}')+1]
        try:
            data = json.loads(clean_json) if clean_json else {}
        except json.JSONDecodeError:
            data = {}

        db = read_data()
        if not isinstance(db, dict):
            db = {}

        # 1. Handle auto-adding interests
        new_topic = data.get("new_interest")
        if new_topic and str(new_topic).lower() not in ["null", "none"]:
            user_interests = [i.lower() for i in db.get(message.author.name, [])]
            if new_topic.lower() not in user_interests:
                write_data(user=message.author.name, game=new_topic)
                reply += f"\n\n*(I noticed you're into {new_topic}, so I added it to your profile!)*"

        # 2. Handle matchmaking pings
        game_to_play = data.get("wants_to_play")
        if game_to_play and str(game_to_play).lower() not in ["null", "none"]:
            guild = self.bot.get_guild(self.bot.guild_id.id)
            
            mentions = [
                m.mention for u, interests in db.items() 
                if u != message.author.name 
                and game_to_play.lower() in (str(i).lower() for i in interests) 
                and (m := guild.get_member_named(u))
            ]
            
            if mentions:
                reply += f"\n\nHey {' '.join(mentions)}, {message.author.mention} is looking to play {game_to_play}!"
            else:
                # Visibility so you know the LLM extraction actually worked!
                reply += f"\n\n*(I see you're looking for an {game_to_play} group, but I couldn't find anyone else in my database who plays it yet!)*"

        await message.reply(reply)

async def setup(bot):
    await bot.add_cog(Listeners(bot))