import json
import os
import re
import requests
import logging
from core.config_manager import load_config

logger = logging.getLogger(__name__)

COMPLEX_KEYWORDS = [
    'demostrar', 'demostración', 'probar', 'prueba',
    'código', 'programar', 'algoritmo', 'estructura de datos',
    'matemática', 'ecuación', 'derivada', 'integral',
    'física cuántica', 'relatividad', 'biología molecular',
    'diagrama', 'arquitectura', 'diseño', 'esquema',
    'explicar detalladamente', 'análisis profundo', 'investigación'
]

def _is_question_too_complex(user_input: str) -> bool:
    user_input_lower = user_input.lower()
    if user_input.count('?') > 3:
        return True
    if len(user_input_lower.split()) > 50:
        return True
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

def _parse_response(raw: str) -> dict:
    """Parser defensivo — maneja JSON sucio, texto plano, y respuestas malformadas."""
    if not raw or not raw.strip():
        return {"text": "Sin respuesta del modelo.", "emotion": "neutral"}

    # Intento 1: JSON directo
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            text = data.get("text") or data.get("response") or data.get("content") or str(data)
            emotion = data.get("emotion", "neutral")
            return {"text": text, "emotion": emotion, "name": data.get("name", "")}
    except (json.JSONDecodeError, ValueError):
        pass

    # Intento 2: extraer bloque JSON del texto
    match = re.search(r'\{[^{}]*"text"\s*:\s*"[^"]*"[^{}]*\}', raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return {
                "text": data.get("text", raw),
                "emotion": data.get("emotion", "neutral"),
                "name": data.get("name", "")
            }
        except (json.JSONDecodeError, ValueError):
            pass

    # Intento 3: el modelo devolvió texto plano — usarlo directamente
    clean = raw.strip().strip('"').strip("'")
    return {"text": clean, "emotion": "neutral", "name": ""}


class Brain:
    def __init__(self):
        self.config = load_config()
        self.llm_settings = self.config['llm']

    def process(self, personality_config, user_input, history):
        provider = self.llm_settings['provider']
        model = self.llm_settings['model']
        url = self.llm_settings['url']

        system_prompt = (
            f"{personality_config['instructions']}\n"
            f"IMPORTANTE: Responde SIEMPRE en JSON válido con este formato exacto: "
            f'{{\"text\": \"tu respuesta aquí\", \"emotion\": \"happy|sad|angry|surprised|neutral\"}}'
        )

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

        urls_to_try = [url]
        alt = _try_codespaces_ollama_url(url)
        if alt != url:
            urls_to_try.append(alt)

        last_error = None
        for try_url in urls_to_try:
            try:
                r = requests.post(f"{try_url}/api/generate", json=payload, timeout=60)
                r.raise_for_status()
                raw = r.json().get('response', '')
                result = _parse_response(raw)
                # Inyectar nombre del personaje si falta
                if not result.get('name'):
                    result['name'] = self.config.get('active_personality', '')
                return result

            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ Timeout en Ollama ({try_url})")
                return {
                    "text": "El modelo tarda demasiado. Intenta de nuevo.",
                    "emotion": "neutral",
                    "name": self.config.get('active_personality', '')
                }
            except requests.exceptions.RequestException as e:
                logger.warning(f"❌ Ollama error en {try_url}: {e}")
                last_error = e
                continue

        # Todos los URLs fallaron
        logger.error(f"❌ Ollama no disponible: {last_error}")
        return {
            "text": f"No se pudo conectar con Ollama: {last_error}",
            "emotion": "neutral",
            "name": self.config.get('active_personality', '')
        }

    def _call_openai_compatible(self, url, model, system, history, user_input):
        headers = {"Authorization": f"Bearer {self.llm_settings['api_key']}"}
        messages = [{"role": "system", "content": system}]
        for m in history:
            messages.append(m)
        messages.append({"role": "user", "content": user_input})

        payload = {
            "model": model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.7
        }

        try:
            r = requests.post(f"{url}/chat/completions", json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            raw = r.json()['choices'][0]['message']['content']
            result = _parse_response(raw)
            if not result.get('name'):
                result['name'] = self.config.get('active_personality', '')
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error API OpenAI-compatible: {e}")
            return {
                "text": f"Error conectando con la API: {e}",
                "emotion": "neutral",
                "name": self.config.get('active_personality', '')
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"❌ Respuesta inválida: {e}")
            return {
                "text": "Respuesta inválida del servidor.",
                "emotion": "neutral",
                "name": self.config.get('active_personality', '')
            }