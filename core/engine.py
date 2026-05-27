from .loader import load_character
from .llm import LLMEngine
from .models import Character

class Engine:
    def __init__(self, character_name: str):
        self.character: Character = load_character(character_name)
        self.llm = LLMEngine(self.character.personality)
        self.current_emotion = "idle"

    def chat(self, user_input: str):
        # 1. Get response from LLM
        response = self.llm.generate_response(user_input)
        
        # 2. Extract text and emotion
        text = response.get("text")
        emotion = response.get("emotion", "neutral")
        
        # 3. Handle Voice (Mock)
        self._play_voice(text)
        
        # 4. Trigger Animation (Mock)
        animation_file = self.character.animations.get(emotion, self.character.animations.get("idle"))
        self._trigger_animation(emotion, animation_file)
        
        return {
            "character": self.character.name,
            "text": text,
            "emotion": emotion,
            "animation_path": animation_file
        }

    def _play_voice(self, text: str):
        print(f"[VOICE] Playing with {self.character.voice.type} at {self.character.voice.speed}x: {text}")

    def _trigger_animation(self, emotion: str, file_path: str):
        print(f"[ANIMATION] Triggering '{emotion}' using {file_path}")
