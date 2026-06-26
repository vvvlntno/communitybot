import os
import json
import random
from datetime import datetime, timedelta, timezone

# Helper to hash username as the main code does
def hash_user(username: str) -> str:
    import hashlib
    if not username:
        return "system"
    return hashlib.sha256(username.encode("utf-8")).hexdigest()[:8]

def generate_mock_data():
    log_file = "metrics_log.jsonl"
    if os.path.exists(log_file):
        os.remove(log_file)

    users = ["alex_gamer", "sam_pro", "tracy_support", "jordan_fps", "taylor_builds", "chris_mmo"]
    hashed_users = {u: hash_user(u) for u in users}

    games = ["overwatch", "minecraft", "valorant", "fortnite"]
    
    # Pre-defined agent usernames for dynamic channels
    agent_names = {
        "overwatch": "MercyMain_99",
        "minecraft": "CreepBuster",
        "valorant": "JettRevivePls",
        "fortnite": "BushCamper"
    }

    # Generate logs over the last 7 days
    now = datetime.now(timezone.utc)
    log_entries = []

    for day in range(7, -1, -1):
        day_date = now - timedelta(days=day)
        
        # Determine number of events on this day
        num_events = random.randint(15, 35)
        
        for _ in range(num_events):
            # Pick a random time on this day
            event_time = day_date + timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )
            
            # Weighted choose of functionality
            # 30% search-interest, 30% add-interest, 15% drive-topic, 15% profile, 10% help
            func = random.choices(
                ["search-interest", "add-interest", "drive-topic", "profile", "help"],
                weights=[30, 30, 15, 15, 10]
            )[0]
            
            user = random.choice(users)
            
            # Weighted choose interface: NLP vs Slash Command
            # Suppose NLP is used 60% of the time, Slash 40%
            interface = random.choices(["natural_language", "slash_command"], weights=[60, 40])[0]
            event_type = "nlp_triggered" if interface == "natural_language" else "command_used"
            
            details = {}
            if func == "search-interest":
                details = {"game": random.choice(games)}
            elif func == "add-interest":
                details = {"game": random.choice(games)}
            elif func == "drive-topic":
                game = random.choice(games)
                details = {"topic": game, "channel_name": f"{game}-channel"}
            
            log_entries.append({
                "timestamp": event_time.isoformat(),
                "event_type": event_type,
                "user": hashed_users[user],
                "channel": "general",
                "interface": interface,
                "functionality": func,
                "details": details
            })

            # If it's a drive-topic event, let's simulate a conversation in that topic channel
            if func == "drive-topic":
                topic_game = details["topic"]
                topic_channel = f"{topic_game}-channel"
                agent_user = agent_names.get(topic_game, "GamerBot")
                
                # Simulate a chat of 5-15 messages in this channel
                chat_len = random.randint(5, 15)
                chat_time = event_time
                
                for idx in range(chat_len):
                    chat_time += timedelta(minutes=random.randint(1, 5))
                    
                    is_bot = (idx % 2 == 1) # Alternating user vs bot replies
                    
                    if is_bot:
                        msg_entry = {
                            "timestamp": chat_time.isoformat(),
                            "event_type": "channel_message",
                            "user": "system",
                            "channel": topic_channel,
                            "interface": "natural_language",
                            "functionality": "persona_chat",
                            "details": {
                                "message_length": random.randint(30, 120),
                                "is_bot": True,
                                "agent_username": agent_user
                            }
                        }
                    else:
                        active_user = random.choice(users)
                        msg_entry = {
                            "timestamp": chat_time.isoformat(),
                            "event_type": "channel_message",
                            "user": hashed_users[active_user],
                            "channel": topic_channel,
                            "interface": "natural_language",
                            "functionality": "persona_chat",
                            "details": {
                                "message_length": random.randint(20, 80),
                                "is_bot": False
                            }
                        }
                    log_entries.append(msg_entry)

    # Sort all logs by timestamp
    log_entries.sort(key=lambda x: x["timestamp"])

    with open(log_file, "w", encoding="utf-8") as f:
        for entry in log_entries:
            f.write(json.dumps(entry) + "\n")

    print(f"Generated {len(log_entries)} mock evaluation events in metrics_log.jsonl!")

if __name__ == "__main__":
    generate_mock_data()
