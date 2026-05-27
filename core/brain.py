import json
import os
import requests
import logging
from core.config_manager import load_config

logger = logging.getLogger(__name__)

# Keywords indicating complex questions
COMPLEX_KEYWORDS = [
    'demostrar', 'demostración', 'probar', 'prueba',
    'código', 'programar', 'algoritmo', 'estructura de datos',
    'matemática', 'ecuación', 'derivada', 'integral',
    'física cuántica', 'relatividad', 'biología molecular',
    'diagrama', 'arquitectura', 'diseño', 'esquema',
    'explicar detalladamente', 'análisis profundo', 'investigación'
]

def _is_question_too_complex(user_input: str) -> bool:
    """Detecta si una pregunta es demasiado complicada para responder de forma simple"""
    user_input_lower = user_input.lower()
    
    # Contar puntos de interrogación y longitud
    question_marks = user_input.count('?')
    words = len(user_input_lower.split())
    
    # Si tiene múltiples preguntas concatenadas
    if question_marks > 3:
        return True
    
    # Si es muy larga (más de 50 palabras)
    if words > 50:
        return True
    
    # Verificar palabras clave de complejidad
    for keyword in COMPLEX_KEYWORDS:
        if keyword in user_input_lower:
            return True
    
    return False


def _is_codespaces():
    return bool(os.environ.get("CODESPACES") or os.environ.get("CODESPACE_NAME"))


def _try_codespaces_ollama_url(url):
    if not _is_codespaces():
        return url
    if url.startswith("http://localhost"):
        return url.replace("http://localhost", "http://127.0.0.1", 1)
    return url


class Brain:
    def __init__(self):
        self.config = load_config()
        self.llm_settings = self.config['llm']

    def process(self, personality_config, user_input, history):
        # Check if question is too complex
        if _is_question_too_complex(user_input):
            logger.info(f"Pregunta detectada como muy compleja: {user_input[:50]}...")
            return {
                "text": "Esa pregunta es muy compleja para que yo pueda responder de forma adecuada. ¿Puedes simplificar o hacer una pregunta más específica?",
                "emotion": "neutral"
            }
        
        provider = self.llm_settings['provider']
        model = self.llm_settings['model']
        url = self.llm_settings['url']
        
        system_prompt = f"{personality_config['instructions']}\nResponde siempre en JSON: {{\"text\": \"...\", \"emotion\": \"...\"}}" 

        if provider == "ollama":
            return self._call_ollama(url, model, system_prompt, history, user_input)
        else:
            return self._call_openai_compatible(url, model, system_prompt, history, user_input)

    def _call_ollama(self, url, model, system, history, user_input):
        payload = {
            "model": model,
            "prompt": f"System: {system}\nContext: {history}\nUser: {user_input}\nAssistant:",
            "format": "json",
            "stream": False
        }

        try:
            r = requests.post(f"{url}/api/generate", json=payload, timeout=60)  # Aumentado a 60 segundos
            r.raise_for_status()
            return json.loads(r.json()['response'])
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ Timeout en Ollama ({url}). El modelo está tardando demasiado.")
            return {
                "text": "El modelo está tardando demasiado en responder. Por favor, intenta de nuevo en unos momentos.",
                "emotion": "neutral"
            }
        except requests.exceptions.RequestException as e:
            logger.warning(f"❌ Ollama error en {url}: {e}")
            alternate_url = _try_codespaces_ollama_url(url)
            if alternate_url != url:
                try:
                    r = requests.post(f"{alternate_url}/api/generate", json=payload, timeout=60)
                    r.raise_for_status()
                    return json.loads(r.json()['response'])
                except requests.exceptions.Timeout:
                    logger.warning(f"⏱️ Timeout en URL alternativa también.")
                    return {
                        "text": "El modelo está tardando demasiado en responder. Por favor, intenta de nuevo en unos momentos.",
                        "emotion": "neutral"
                    }
                except requests.exceptions.RequestException as e2:
                    logger.error(f"❌ Fallido en URL alternativa: {e2}")
                    raise
            logger.error(f"❌ Ollama no disponible en {url}")
            raise

    def _call_openai_compatible(self, url, model, system, history, user_input):
        headers = {"Authorization": f"Bearer {self.llm_settings['api_key']}"}
        messages = [{"role": "system", "content": system}]
        for m in history: 
            messages.append(m)
        messages.append({"role": "user", "content": user_input})
        
        # Deshabilitar pensamiento profundo (deep thinking) para respuesta rápida
        payload = {
            "model": model, 
            "messages": messages, 
            "response_format": {"type": "json_object"},
            "reasoning": "disabled",  # Deshabilita o1/o3 thinking
            "temperature": 0.7,  # Evita modos de reasoning avanzado
            "max_reasoning_tokens": 0  # Algunos modelos usan esto
        }
        try:
            r = requests.post(f"{url}/chat/completions", json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            return json.loads(r.json()['choices'][0]['message']['content'])
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error API OpenAI-compatible: {e}")
            raise
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"❌ Respuesta inválida del servidor: {e}")
            raise
