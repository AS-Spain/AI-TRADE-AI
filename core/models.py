try:
    from pydantic import BaseModel
except Exception:
    # fallback ligero si pydantic no está disponible (permite arrancar para pruebas UI)
    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)
from typing import Dict, List, Optional

class Animation(BaseModel):
    pass

class VoiceConfig(BaseModel):
    pass

class MemoryConfig(BaseModel):
    pass

class Character(BaseModel):
    # A fallback flexible model: attributes se asignan dinámicamente
    pass
