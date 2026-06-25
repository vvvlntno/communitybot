import json
import discord
from discord.ext import commands
import config
import core.prompts as prompts
from core.db import read_data, write_data

class AddInterestView(discord.ui.View):
    def __init__(self, user_name: str, topic: str):
        super().__init__(timeout=300)
        self.user_name = user_name
        self.topic = topic

    @discord.ui.button(label="Add to Profile", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.name != self.user_name:
            return await interaction.response.send_message("This prompt isn't for you!", ephemeral=True)
        
        write_data(user=self.user_name, game=self.topic)
        await interaction.message.edit(view=None)
        await interaction.response.send_message(f"Added {self.topic} to your profile!", ephemeral=True)

    @discord.ui.button(label="Ignore", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.name != self.user_name:
            return await interaction.response.send_message("This prompt isn't for you!", ephemeral=True)
        
        await interaction.message.edit(view=None)
        await interaction.response.defer()

class CreateChannelView(discord.ui.View):
    def __init__(self, bot, user_name: str, topic: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_name = user_name
        self.topic = topic

    @discord.ui.button(label="Create Channel", style=discord.ButtonStyle.blurple)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.name != self.user_name:
            return await interaction.response.send_message("This prompt isn't for you!", ephemeral=True)
        
        await interaction.response.defer()
        await interaction.message.edit(view=None)

        channel_name = self.topic.lower().replace(" ", "-")
        channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
        
        if not channel:
            channel = await interaction.guild.create_text_channel(name=channel_name)

        db = read_data()
        mentions = [
            m.mention for u, interests in (db.items() if isinstance(db, dict) else [])
            if interests and self.topic.lower() in (str(i).lower() for i in interests)
            and (m := interaction.guild.get_member_named(u))
        ]

        ping_text = ' '.join(mentions) if mentions else "No specific users to ping yet."
        sys_instruction = f"Write a short, hype welcome message for the brand new {self.topic} channel. You MUST explicitly include these pings in your message: {ping_text}"
        
        resp = await self.bot.openai.chat.completions.create(
            model=config.MODEL,
            messages=[
                {"role": "system", "content": prompts.SYSTEM_PROMPT},
                {"role": "user", "content": sys_instruction}
            ],
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
        )

        await channel.send(resp.choices[0].message.content)
        await interaction.followup.send(f"Done! Check out {channel.mention}", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.name != self.user_name:
            return await interaction.response.send_message("This prompt isn't for you!", ephemeral=True)
        
        await interaction.message.edit(view=None)
        await interaction.response.defer()

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

        async with message.channel.typing():
            
            extract_resp = await self.bot.openai.chat.completions.create(
                model=config.MODEL,
                messages=[
                    {"role": "system", "content": prompts.EXTRACTION_PROMPT},
                    {"role": "user", "content": message.content}
                ],
                temperature=0.0,
                max_tokens=50,
            )

            raw_extract = extract_resp.choices[0].message.content
            clean_json = raw_extract[raw_extract.find('{'):raw_extract.rfind('}')+1]
            try:
                data = json.loads(clean_json) if clean_json else {}
            except json.JSONDecodeError:
                data = {}

            db = read_data()
            if not isinstance(db, dict):
                db = {}

            system_instruction = ""
            view = None

            new_topic = data.get("new_interest")
            if new_topic and str(new_topic).lower() not in ["null", "none"]:
                user_interests = [str(i).lower() for i in (db.get(message.author.name) or [])]
                if str(new_topic).lower() not in user_interests:
                    view = AddInterestView(message.author.name, new_topic)
                    system_instruction = f"SYSTEM INSTRUCTION: You are attaching a UI button to let the user add {new_topic} to their profile. Naturally ask them if they want to add it to their profile."

            game_to_play = data.get("wants_to_play")
            if game_to_play and str(game_to_play).lower() not in ["null", "none"]:
                guild = self.bot.get_guild(self.bot.guild_id.id)
                mentions = [
                    m.mention for u, interests in db.items() 
                    if u != message.author.name 
                    and interests is not None
                    and game_to_play.lower() in (str(i).lower() for i in interests) 
                    and (m := guild.get_member_named(u))
                ]
                
                if mentions:
                    system_instruction = f"SYSTEM INSTRUCTION: The following users play {game_to_play}: {' '.join(mentions)}. You MUST explicitly include these exact pings/mentions in your reply to notify them."
                else:
                    system_instruction = f"SYSTEM INSTRUCTION: The user wants to play {game_to_play}, but nobody in your database plays it yet. Inform them naturally."

            drive_topic = data.get("drive_topic")
            if drive_topic and str(drive_topic).lower() not in ["null", "none"]:
                channel_name = str(drive_topic).lower().replace(" ", "-")
                existing_channel = discord.utils.get(message.guild.text_channels, name=channel_name)
                
                if existing_channel:
                    system_instruction = f"SYSTEM INSTRUCTION: The user wants a space to talk about {drive_topic}, but a channel already exists! Enthusiastically point them to {existing_channel.mention}."
                else:
                    view = CreateChannelView(self.bot, message.author.name, drive_topic)
                    system_instruction = f"SYSTEM INSTRUCTION: You are attaching a UI button to let the user create a dedicated #{channel_name} channel. Naturally ask them if they want you to set it up for them."

            current_context = self.bot.message_history.copy()
            current_context.append({"role": "user", "content": f"{message.author.name}: {message.content}"})
            
            if system_instruction:
                current_context.append({"role": "system", "content": system_instruction})

            chat_resp = await self.bot.openai.chat.completions.create(
                model=config.MODEL,
                messages=current_context,
                temperature=config.TEMPERATURE,
                max_tokens=config.MAX_TOKENS,
            )

            reply = chat_resp.choices[0].message.content

            self.bot.message_history.append({"role": "user", "content": f"{message.author.name}: {message.content}"})
            self.bot.message_history.append({"role": "assistant", "content": reply})

        await message.reply(reply, view=view)

async def setup(bot):
    await bot.add_cog(Listeners(bot))