import atexit
import copy
import json
import os

CONFIG_PATH = "db/config.json"

# Ahora no hay modelos predefinidos, solo la estructura
EMPTY_CONFIG = {
    "llm": {
        "provider": None,
        "model": None,
        "url": None,
        "api_key": None
    },
    "audio": {
        "stt_local": True,
        "tts_local": True,
        "voice_model": None
    },
    "active_personality": None,
    "active_skin": None,
    "active_vrm": None,
    "setup_complete": False
}

def _fresh_config():
    return copy.deepcopy(EMPTY_CONFIG)

def clear_saved_config():
    try:
        os.remove(CONFIG_PATH)
    except OSError:
        pass


def register_clear_saved_config_on_exit():
    atexit.register(clear_saved_config)


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return _fresh_config()

    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def save_config(config):
    os.makedirs("db", exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)
