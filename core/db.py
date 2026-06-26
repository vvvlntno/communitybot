import yaml



def read_data():
    with open("database.yaml") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            return exc


def write_data(user: str, game: str):
    data: dict = read_data()
    try:
        if game not in data[user]:
            data[user].append(game)
    except KeyError:
        data.update({user: [game]})
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
