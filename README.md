# CommunityBot: Cooperation Systems Evaluation Platform

A Discord-based community support bot and evaluation platform designed to study and quantitatively analyze user interaction paradigms in online community spaces. Developed as part of a Master's degree course in Cooperation Systems, the platform evaluates the adoption of **Natural Language Processing (NLP) triggers** against **traditional Slash Commands** for matchmaking, profiling, and topic-driving activities.

---

## 1. Project Explanation

Online community servers (e.g., Discord) rely on various cooperation tools to help users connect. Traditional tools use rigid slash commands, whereas modern designs integrate LLM-driven agents to detect user intent from natural language chat. 

To evaluate these interaction paradigms, this project transforms a standard matchmaking bot into a **simulated cooperative ecosystem**:
- **Simulated Cooperative Agents**: Instead of searching a database for real users and sending pings, the bot dynamically spawns customized AI gamer personas (using Mistral AI) inside dedicated channels.
- **Anonymized Metrics Logging**: Every command invocation, NLP trigger, and channel conversation message is automatically logged with hashed identifiers.
- **Scientific Dashboard**: A Streamlit dashboard processes the logs to generate statistical metrics comparing interface adoption, user engagement, and timelines.

---

## 2. Architecture Decisions

### 2.1 Webhook-Based Persona Simulation
To ensure the LLM agents look like real, distinct community members (rather than generic bot accounts), the system utilizes **Discord Webhooks**. When a topic channel is created, the bot uses `PERSONA_GENERATION_PROMPT` to choose a game-specific username (e.g. `JettRevivePls` for Valorant). It posts messages using webhooks with a dynamic, keyless AI avatar generated on-the-fly via **Pollinations AI**.

### 2.2 Scoped Conversation Histories
Instead of a single global message history that mixes different conversations, conversation history is strictly isolated per channel in `self.channel_histories`. Registered topic channel IDs and their respective personas are persisted in `topic_channels.json` so that they survive bot restarts.

### 2.3 Anonymized User Logging
To conform to privacy guidelines for academic research, all Discord usernames are anonymized before being logged to disk. The `hash_user` helper uses SHA-256 to generate a consistent, unique 8-character hex code (e.g., `e3b0c442`), ensuring user privacy while preserving the ability to count unique participants ($N$) and track retention.

### 2.4 Streamlit & Plotly Dashboard
To support publication-grade charts without adding frontend/JavaScript dependencies, the evaluation interface is built in **Streamlit** using **Plotly**. The logs are written to a standard JSON Lines (`metrics_log.jsonl`) file, allowing them to be loaded into Pandas dataframes with one line of code:
```python
import pandas as pd
df = pd.read_json("metrics_log.jsonl", lines=True)
```

---

## 3. Discord Bot Explanation

The Discord Bot acts as the primary data collection and matchmaking interface.

### 3.1 Commands & Features
- **`/help`**: Displays an overview of bot commands and capabilities (ephemeral).
- **`/profile`**: Displays the user's interactive Profile Card (Embed). Includes a `discord.ui.Select` dropdown to let the user select and instantly remove saved interests, and a `Clear All` button.
- **`/add-interest [game]`**: Saves a game (normalized to lowercase) to the user's profile in `database.yaml`.
- **`/search-interest [game]`**: Queries the YAML database and returns matching players (real users only).
- **`/drive-topic [topic]`**: Creates a channel named after the topic under the `user-driven-topics` category, assigns the gold `Topic Driver` role to the creator, and spawns the dynamic AI gamer persona.

### 3.2 Natural Language Intent Detection
The bot monitors chat in non-topic channels and queries a strict LLM extraction prompt to detect:
1. **`view_profile`**: If the user asks to see their interests (e.g., *"what am I interested in?"*), the bot replies with the interactive Profile Card.
2. **`new_interest`**: If the user declares a new interest (e.g., *"I'm getting into Valorant"*), the bot prompts them with an `"Add to Profile"` button.
3. **`wants_to_play`**: If the user wants to play (e.g., *"anyone down for Overwatch?"*), the bot automatically pings matching players from the database.
4. **`drive_topic`**: If the user wants a new space (e.g., *"we need a channel for Fortnite"*), the bot offers a `"Create Channel"` button.

---

## 4. Evaluation Dashboard Explanation

The scientific dashboard in `dashboard.py` displays key statistics for Cooperation Systems evaluation:

- **Key Metrics Summary**: Shows the total event sample size ($N$), raw NLP trigger counts, slash command counts, and the overall NLP adoption percentage.
- **Topic Driving Adoption**: A bar chart comparing `/drive-topic` command usage against NLP-triggered channel creation.
- **Player Search Adoption**: A bar chart comparing `/search-interest` command usage against NLP-triggered matchmaking.
- **Topic Channel Activity**: A horizontal stacked bar chart showing user participation (Human messages) vs. agent engagement (replies sent by simulated persona webhooks) in driven channels.
- **Adoption Timeline**: A line chart showing daily invocation trends for NLP vs. Command interfaces over time.
- **Raw Log Inspector**: An interactive table of logs with a button to export the data as a CSV file for external plotting in R, SPSS, or Pandas.

---

## 5. How to Run

### 5.1 Environment Setup
1. Ensure you have Python 3.13+ and [uv](https://github.com/astral-sh/uv) installed.
2. Configure your `.env` file in the root directory:
   ```env
   BOT_TOKEN=your_discord_bot_token
   GUILD_ID=your_discord_guild_id
   MISTRAL_API_KEY=your_mistral_api_key
   ```
3. Install dependencies:
   ```powershell
   uv sync
   ```

### 5.2 Seeding Mock Evaluation Logs
To preview the dashboard immediately with realistic data over the past 7 days:
```powershell
uv run python generate_mock_logs.py
```
*(Alternatively, run the **Generate Mock Evaluation Logs** task in VS Code).*

### 5.3 Running the Discord Bot
Start the Discord bot:
```powershell
uv run python main.py
```

### 5.4 Running the Dashboard
Start the Streamlit web server:
```powershell
uv run streamlit run dashboard.py
```
*(Alternatively, run the **Run Streamlit Dashboard** task in VS Code).*
The dashboard will launch locally and open at `http://localhost:8501`.
