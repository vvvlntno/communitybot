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