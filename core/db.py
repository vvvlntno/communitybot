import yaml



def read_data():
    with open("database.yaml") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            return exc


def write_data(user: str, game: str):
    data: dict = read_data()
    game_lower = game.strip().lower()
    try:
        if game_lower not in data[user]:
            data[user].append(game_lower)
    except KeyError:
        data.update({user: [game_lower]})
    with open("database.yaml", "w") as outfile:
        yaml.dump(data, outfile, default_flow_style=False, sort_keys=False)


def read_topic_channels() -> dict:
    import json
    import os
    if not os.path.exists("topic_channels.json"):
        return {}
    with open("topic_channels.json", "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def write_topic_channel(channel_id: int, topic: str, username: str, personality: str):
    import json
    data = read_topic_channels()
    data[str(channel_id)] = {
        "topic": topic,
        "username": username,
        "personality": personality
    }
    with open("topic_channels.json", "w") as f:
        json.dump(data, f, indent=4)


def remove_interest(user: str, game: str):
    data: dict = read_data()
    if isinstance(data, dict) and user in data:
        interests = data[user]
        if isinstance(interests, list):
            data[user] = [i for i in interests if str(i).strip().lower() != game.strip().lower()]
            with open("database.yaml", "w") as outfile:
                yaml.dump(data, outfile, default_flow_style=False, sort_keys=False)


def clear_interests(user: str):
    data: dict = read_data()
    if isinstance(data, dict) and user in data:
        data[user] = []
        with open("database.yaml", "w") as outfile:
            yaml.dump(data, outfile, default_flow_style=False, sort_keys=False)


def hash_user(username: str) -> str:
    import hashlib
    if not username:
        return "system"
    return hashlib.sha256(username.encode("utf-8")).hexdigest()[:8]


def log_event(event_type: str, username: str, channel_name: str, interface: str, functionality: str, details: dict = None):
    import json
    from datetime import datetime, timezone
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user": hash_user(username) if username else "system",
        "channel": channel_name,
        "interface": interface,
        "functionality": functionality,
        "details": details or {}
    }
    with open("metrics_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")
