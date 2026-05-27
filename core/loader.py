import yaml
import os
from typing import List
from .models import Character

def load_character(character_name: str) -> Character:
    path = os.path.join("characters", character_name)
    yaml_path = os.path.join(path, "character.yaml")
    
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"Character config not found at {yaml_path}")
        
    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)
        
    return Character(**config, base_path=path)

def list_characters() -> List[str]:
    if not os.path.exists("characters"):
        return []
    return [d for d in os.listdir("characters") if os.path.isdir(os.path.join("characters", d))]
