import json
import random

class LLMEngine:
    def __init__(self, personality: str):
        self.personality = personality

    def generate_response(self, user_input: str) -> dict:
        # This is a mock. In a real scenario, you'd call OpenAI/Claude/etc.
        # and prompt it to return JSON.
        
        emotions = ["happy", "neutral", "sad", "angry"]
        selected_emotion = random.choice(emotions)
        
        # Simplified mock logic
        if "hola" in user_input.lower():
            text = "¡Hola! ¿Cómo estás hoy?"
            selected_emotion = "happy"
        elif "triste" in user_input.lower():
            text = "Oh, lamento escuchar eso... ¿Quieres hablar?"
            selected_emotion = "sad"
        else:
            text = f"Respondiendo como alguien {self.personality[:20]}... Dijiste: {user_input}"
        
        return {
            "text": text,
            "emotion": selected_emotion
        }
