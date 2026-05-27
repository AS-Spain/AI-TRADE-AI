try:
    from pydantic import BaseModel
except Exception:
    # fallback ligero si pydantic no está disponible (permite arrancar para pruebas UI)
    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)
from typing import Dict, List, Optional, Any

class Animation(BaseModel):
    pass

class VoiceConfig(BaseModel):
    pass

class MemoryConfig(BaseModel):
    pass

class Character(BaseModel):
    """Character model with support for dynamic attributes from YAML"""
    name: Optional[str] = None
    personality: Optional[str] = None
    voice: Optional[Dict[str, Any]] = None
    avatar: Optional[str] = None
    animations: Optional[Dict[str, str]] = None
    memory: Optional[Dict[str, Any]] = None
    vrm: Optional[str] = None
    instructions: Optional[str] = None
    base_path: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow extra fields from YAML
