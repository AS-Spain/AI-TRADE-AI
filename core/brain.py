import json
import os
import requests
import logging
from core.config_manager import load_config

logger = logging.getLogger(__name__)


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
            r = requests.post(f"{url}/api/generate", json=payload, timeout=30)
            r.raise_for_status()
            return json.loads(r.json()['response'])
        except requests.exceptions.RequestException as e:
            logger.warning(f"❌ Ollama error en {url}: {e}")
            alternate_url = _try_codespaces_ollama_url(url)
            if alternate_url != url:
                try:
                    r = requests.post(f"{alternate_url}/api/generate", json=payload, timeout=30)
                    r.raise_for_status()
                    return json.loads(r.json()['response'])
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
        
        payload = {"model": model, "messages": messages, "response_format": {"type": "json_object"}}
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
