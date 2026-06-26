import json
import discord
from discord.ext import commands
import config
import core.prompts as prompts
from core.db import read_data, write_data, write_topic_channel, read_topic_channels, log_event
from cogs.interests import generate_persona, generate_welcome_message, send_webhook_message, setup_category_and_driver

def make_profile_embed(user: discord.User, interests: list[str]) -> discord.Embed:
    embed = discord.Embed(
        title=f"🎮 {user.display_name}'s Profile",
        description="Manage your gaming interests below. Select an interest from the dropdown to remove it, or click the clear button.",
        color=discord.Color.blurple()
    )
    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)
    else:
        embed.set_thumbnail(url=user.default_avatar.url)
    
    if interests:
        embed.add_field(
            name="Your Saved Interests",
            value="\n".join(f"• **{i}**" for i in interests),
            inline=False
        )
    else:
        embed.add_field(
            name="Your Saved Interests",
            value="*You haven't added any interests yet!*",
            inline=False
        )
    return embed

class RemoveInterestSelect(discord.ui.Select):
    def __init__(self, user: discord.User, options: list[discord.SelectOption]):
        super().__init__(
            placeholder="Select an interest to remove it...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("This profile control is not for you!", ephemeral=True)
        
        selected_game = self.values[0]
        from core.db import remove_interest
        remove_interest(self.user.name, selected_game)
        
        db = read_data()
        interests = (db.get(self.user.name) or []) if isinstance(db, dict) else []
        embed = make_profile_embed(self.user, interests)
        
        view = ProfileView(self.user)
        await interaction.response.edit_message(embed=embed, view=view)

class ClearAllButton(discord.ui.Button):
    def __init__(self, user: discord.User):
        super().__init__(
            label="Clear All",
            style=discord.ButtonStyle.red,
            emoji="🗑️"
        )
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("This profile control is not for you!", ephemeral=True)
        
        from core.db import clear_interests
        clear_interests(self.user.name)
        
        embed = make_profile_embed(self.user, [])
        view = ProfileView(self.user)
        await interaction.response.edit_message(embed=embed, view=view)

class ProfileView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=300)
        self.user = user
        self.update_components()

    def update_components(self):
        self.clear_items()
        db = read_data()
        interests = (db.get(self.user.name) or []) if isinstance(db, dict) else []
        
        if interests:
            options = [
                discord.SelectOption(label=interest, value=interest, emoji="❌")
                for interest in interests[:25]
            ]
            self.add_item(RemoveInterestSelect(self.user, options))
            self.add_item(ClearAllButton(self.user))

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

        # Retrieve or create category, assign driver role
        category = await setup_category_and_driver(interaction.guild, interaction.user)

        channel_name = self.topic.lower().replace(" ", "-")
        channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
        
        if not channel:
            channel = await interaction.guild.create_text_channel(name=channel_name, category=category)

        # Log NLP-triggered drive-topic event
        log_event(
            event_type="nlp_triggered",
            username=self.user_name,
            channel_name=interaction.channel.name if interaction.channel else "unknown",
            interface="natural_language",
            functionality="drive-topic",
            details={"topic": self.topic.strip().lower(), "channel_name": channel_name}
        )

        # Generate persona
        persona = await generate_persona(self.bot, self.topic)
        username = persona["username"]
        personality = persona["personality"]

        # Save channel mapping
        write_topic_channel(channel.id, self.topic, username, personality)

        # Generate welcome message
        welcome_msg = await generate_welcome_message(self.bot, self.topic, username, personality, channel_name)

        # Send welcome message via Webhook
        await send_webhook_message(channel, username, welcome_msg)

        # Initialize history
        sys_prompt = prompts.AGENT_SYSTEM_PROMPT.format(
            username=username,
            personality=personality,
            topic=self.topic,
            channel_name=channel_name
        )
        self.bot.channel_histories[channel.id] = [
            {"role": "system", "content": sys_prompt},
            {"role": "assistant", "content": welcome_msg}
        ]

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
        # Ignore messages from bots/webhooks to prevent infinite loops
        if message.author.bot or message.webhook_id is not None:
            return

        topic_channels = read_topic_channels()
        channel_id_str = str(message.channel.id)

        # Persona Agent interaction in topic channels
        if channel_id_str in topic_channels:
            persona_info = topic_channels[channel_id_str]
            topic = persona_info["topic"]
            username = persona_info["username"]
            personality = persona_info["personality"]

            # Log user channel message
            log_event(
                event_type="channel_message",
                username=message.author.name,
                channel_name=message.channel.name,
                interface="natural_language",
                functionality="persona_chat",
                details={"message_length": len(message.content), "is_bot": False}
            )

            # Initialize channel history if it does not exist
            if message.channel.id not in self.bot.channel_histories:
                sys_prompt = prompts.AGENT_SYSTEM_PROMPT.format(
                    username=username,
                    personality=personality,
                    topic=topic,
                    channel_name=message.channel.name
                )
                self.bot.channel_histories[message.channel.id] = [
                    {"role": "system", "content": sys_prompt}
                ]

            self.bot.channel_histories[message.channel.id].append(
                {"role": "user", "content": f"{message.author.name}: {message.content}"}
            )

            async with message.channel.typing():
                chat_resp = await self.bot.openai.chat.completions.create(
                    model=config.MODEL,
                    messages=self.bot.channel_histories[message.channel.id],
                    temperature=config.TEMPERATURE,
                    max_tokens=config.MAX_TOKENS,
                )
                reply = chat_resp.choices[0].message.content

            self.bot.channel_histories[message.channel.id].append(
                {"role": "assistant", "content": reply}
            )

            await send_webhook_message(message.channel, username, reply)

            # Log agent channel message
            log_event(
                event_type="channel_message",
                username="",
                channel_name=message.channel.name,
                interface="natural_language",
                functionality="persona_chat",
                details={"message_length": len(reply), "is_bot": True, "agent_username": username}
            )
            return

        # General/Matchmaking flow in non-topic channels
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

            # Detect check/view profile request
            if data.get("view_profile") is True or str(data.get("view_profile")).lower() == "true":
                log_event(
                    event_type="nlp_triggered",
                    username=message.author.name,
                    channel_name=message.channel.name,
                    interface="natural_language",
                    functionality="profile"
                )
                db = read_data()
                interests = (db.get(message.author.name) or []) if isinstance(db, dict) else []
                embed = make_profile_embed(message.author, interests)
                view = ProfileView(message.author)
                await message.reply(embed=embed, view=view)
                return

            db = read_data()
            if not isinstance(db, dict):
                db = {}

            system_instruction = ""
            view = None

            new_topic = data.get("new_interest")
            if new_topic and str(new_topic).lower() not in ["null", "none"]:
                log_event(
                    event_type="nlp_triggered",
                    username=message.author.name,
                    channel_name=message.channel.name,
                    interface="natural_language",
                    functionality="add-interest",
                    details={"game": new_topic.strip().lower()}
                )
                user_interests = [str(i).lower() for i in (db.get(message.author.name) or [])]
                if str(new_topic).lower() not in user_interests:
                    view = AddInterestView(message.author.name, new_topic)
                    system_instruction = f"SYSTEM INSTRUCTION: You are attaching a UI button to let the user add {new_topic} to their profile. Naturally ask them if they want to add it to their profile."

            game_to_play = data.get("wants_to_play")
            if game_to_play and str(game_to_play).lower() not in ["null", "none"]:
                log_event(
                    event_type="nlp_triggered",
                    username=message.author.name,
                    channel_name=message.channel.name,
                    interface="natural_language",
                    functionality="search-interest",
                    details={"game": game_to_play.strip().lower()}
                )
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

            if message.channel.id not in self.bot.channel_histories:
                self.bot.channel_histories[message.channel.id] = [
                    {"role": "system", "content": prompts.SYSTEM_PROMPT}
                ]

            current_context = self.bot.channel_histories[message.channel.id].copy()
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

            self.bot.channel_histories[message.channel.id].append({"role": "user", "content": f"{message.author.name}: {message.content}"})
            self.bot.channel_histories[message.channel.id].append({"role": "assistant", "content": reply})

        await message.reply(reply, view=view)

async def setup(bot):
    await bot.add_cog(Listeners(bot))