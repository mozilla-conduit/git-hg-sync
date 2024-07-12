import configparser
from pathlib import Path

HERE = Path(__file__).parent


def get_config():
    config = configparser.ConfigParser()
    config.read(HERE / "config.ini")
    return config


if __name__ == "__main__":
    get_config()
