import yaml
import os
from typing import List
from .models import Character
from .config_manager import load_config



def load_character(character_name: str) -> Character:
    path = os.path.join("characters", character_name)
    yaml_path = os.path.join(path, "character.yaml")
    
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"Character config not found at {yaml_path}")
        
    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)

    # If there's an active_vrm in global config, prefer it
    try:
        global_conf = load_config()
        active_vrm = global_conf.get('active_vrm')
        if active_vrm:
            # If path is relative, make it relative to repo root
            if not os.path.isabs(active_vrm):
                vrm_path = os.path.normpath(active_vrm)
            else:
                vrm_path = active_vrm
            if os.path.exists(vrm_path):
                config['vrm'] = vrm_path
    except Exception:
        pass

    return Character(**config, base_path=path)

def list_characters() -> List[str]:
    if not os.path.exists("characters"):
        return []
    return [d for d in os.listdir("characters") if os.path.isdir(os.path.join("characters", d))]
