import requests
import json

class LLMProvider:
    def __init__(self, config):
        self.config = config # Contiene tipo (ollama/api), url, modelo

    def generate(self, system_prompt, history, user_input):
        if self.config['type'] == 'ollama':
            return self._call_ollama(system_prompt, history, user_input)
        else:
            return self._call_generic_api(system_prompt, history, user_input)

    def _call_ollama(self, system_prompt, history, user_input):
        url = f"{self.config['base_url']}/api/generate"
        
        # Construimos el prompt con formato de chat
        full_context = f"System: {system_prompt}\n"
        for msg in history:
            full_context += f"{msg['role']}: {msg['content']}\n"
        full_context += f"User: {user_input}\nAssistant:"

        payload = {
            "model": self.config['model'],
            "prompt": full_context,
            "stream": False,
            "format": "json" # Ollama soporta modo JSON
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            data = response.json()
            # Esperamos que el LLM devuelva {"text": "...", "emotion": "..."}
            return json.loads(data['response'])
        except Exception as e:
            return {"text": f"Error de conexión local: {str(e)}", "emotion": "neutral"}

    def _call_generic_api(self, system_prompt, history, user_input):
        # Implementación simplificada para OpenAI/Claude
        return {"text": "Respuesta desde API (no implementada)", "emotion": "happy"}
