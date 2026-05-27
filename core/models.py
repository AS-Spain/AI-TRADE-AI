from pydantic import BaseModel
from typing import Dict, List, Optional

class Animation(BaseModel):
    name: str
    frames: List[str]
    fps: int
    loop: bool

class VoiceConfig(BaseModel):
    type: str
    speed: float = 1.0

class MemoryConfig(BaseModel):
    enabled: bool = True
    memory_size: int = 100

class Character(BaseModel):
    name: str
    personality: str
    voice: VoiceConfig
    avatar: str
    animations: Dict[str, str]  # Path to json files
    memory: MemoryConfig
    base_path: str
