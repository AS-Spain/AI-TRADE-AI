import os
import questionary
import requests
import shutil
import subprocess
from core.config_manager import load_config, save_config
RECOMMENDED_OLLAMA_MODELS = [
    "llama3",
    "mistral",
    "dolphin",
    "mistral-7b",
    "llama2",
]
DEFAULT_OPENAI_MODEL = "gpt-3.5-turbo"


def is_codespaces():
    return bool(os.environ.get("CODESPACES") or os.environ.get("CODESPACE_NAME"))


def default_ollama_url():
    if is_codespaces():
        return "http://127.0.0.1:11434"
    return "http://localhost:11434"


def normalize_ollama_url(url):
    if not url:
        return url
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url
    return url.rstrip("/")


def test_ollama_server(url):
    try:
        response = requests.get(f"{url}/api/models", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def ensure_ollama_installed():
    return shutil.which("ollama") is not None


def install_ollama():
    print("\nInstalando Ollama local...")
    try:
        subprocess.run("curl -fsSL https://ollama.com/install.sh | sh", shell=True, check=True)
        print("Ollama instalado correctamente.")
        return True
    except subprocess.CalledProcessError:
        print("No se pudo instalar Ollama automáticamente. Por favor instálalo manualmente desde https://ollama.com.")
        return False


def download_ollama_model(model_name):
    print(f"\nDescargando modelo Ollama: {model_name}")
    try:
        subprocess.run(["ollama", "pull", model_name], check=True)
        print(f"Modelo '{model_name}' descargado correctamente.")
        return True
    except subprocess.CalledProcessError:
        print(f"Error descargando el modelo '{model_name}'. Verifica el nombre o la conexión a internet.")
        return False


def list_installed_ollama_models():
    if not ensure_ollama_installed():
        return []
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        return []

    models = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("NAME"):
            continue
        columns = line.split()
        if columns:
            models.append(columns[0])
    return models


def choose_ollama_model(installed_models=None):
    installed_models = installed_models or []
    choices = []

    if installed_models:
        choices.append({"name": "Modelos ya instalados:", "disabled": True})
        for model in installed_models:
            choices.append({"name": model, "value": model})
        choices.append({"name": "Modelos recomendados:", "disabled": True})

    for model in RECOMMENDED_OLLAMA_MODELS:
        if model not in installed_models:
            choices.append({"name": model, "value": model})

    choices.append({"name": "Otro modelo personalizado...", "value": "__custom__"})

    choice = questionary.select("Elige un modelo de Ollama:", choices=choices).ask()
    if choice == "__custom__":
        return questionary.text("Nombre del modelo en Ollama (ej: llama3, mistral, dolphin):").ask()

    return choice
    choice = questionary.select(
        "Elige un modelo de Ollama:",
        choices=[*RECOMMENDED_OLLAMA_MODELS, "Otro modelo personalizado..."]
    ).ask()

    if choice == "Otro modelo personalizado...":
        return questionary.text("Nombre del modelo en Ollama (ej: llama3, mistral, dolphin):").ask()

    return choice


def run_wizard():
    print("\n" + "═" * 60)
    print(" 🧠 CHARACTER OS - SETUP AMIGABLE")
    print(" ═" * 60 + "\n")
    print("Esta configuración te guiará para conectar tu motor de IA y descargar el modelo correcto.")
    print("Si eliges Ollama, el asistente te ayudará a instalarlo y descargar un modelo local.")
    if is_codespaces():
        print("\nNota: estás en GitHub Codespaces. Se usará 127.0.0.1 en lugar de localhost para Ollama.")
    print("\n")

    config = load_config()

    provider = questionary.select(
        "Selecciona tu motor de IA principal:",
        choices=[
            {"name": "Ollama (Servidor Local)", "value": "ollama"},
            {"name": "OpenAI (API Externa)", "value": "openai"},
            {"name": "Custom OpenAI-Compatible API (LM Studio, etc)", "value": "custom"}
        ]
    ).ask()

    model_name = ""
    url = default_ollama_url()
    api_key = ""
    ollama_available = ensure_ollama_installed()
    installed_models = []

    if provider == "ollama":
        if not ollama_available:
            install_now = questionary.confirm(
                "Ollama no está instalado. ¿Quieres instalarlo ahora?", default=True
            ).ask()
            if install_now:
                ollama_available = install_ollama()

        if ollama_available:
            installed_models = list_installed_ollama_models()

        if not ollama_available:
            print("\nNo se pudo instalar Ollama. Puedes continuar, pero el motor local no funcionará hasta que lo instales.")

        model_name = choose_ollama_model(installed_models)
        while True:
            url = normalize_ollama_url(questionary.text("URL de Ollama:", default=url).ask())
            if not url:
                break

            if test_ollama_server(url):
                break

            if is_codespaces() and url.startswith("http://localhost"):
                alternate_url = url.replace("http://localhost", "http://127.0.0.1", 1)
                if test_ollama_server(alternate_url):
                    url = alternate_url
                    print(f"Usando URL de Codespaces: {url}")
                    break

            retry = questionary.confirm(
                "No se detectó Ollama en esa URL. ¿Quieres intentarlo de nuevo?", default=True
            ).ask()
            if not retry:
                print("Continuando sin verificar Ollama. Asegúrate de que el servidor esté activo más tarde.")
                break

    elif provider == "openai":
        model_name = questionary.text(
            f"Modelo de OpenAI (ej: {DEFAULT_OPENAI_MODEL}):",
            default=DEFAULT_OPENAI_MODEL
        ).ask()
        api_key = questionary.password("Introduce tu OpenAI API Key:").ask()
        url = "https://api.openai.com/v1"

    else:
        print("Introduce los datos de tu API compatible con OpenAI.")
        url = questionary.text("URL del endpoint API:").ask()
        model_name = questionary.text("Nombre del modelo configurado:").ask()
        api_key = questionary.password("API Key (si es necesaria):").ask()

    use_local_audio = questionary.confirm(
        "¿Deseas procesar Audio y Voz de forma local?", default=True
    ).ask()

    p_name = questionary.text(
        "Dale un nombre a tu primera personalidad:", default="Asistente"
    ).ask()

    config["llm"]["provider"] = provider
    config["llm"]["model"] = model_name
    config["llm"]["url"] = url
    config["llm"]["api_key"] = api_key
    config["audio"]["stt_local"] = use_local_audio
    config["audio"]["tts_local"] = use_local_audio
    config["active_personality"] = p_name
    config["setup_complete"] = True
    save_config(config)

    if provider == "ollama" and ollama_available and model_name:
        if model_name in installed_models:
            print(f"\nEl modelo '{model_name}' ya está instalado localmente. No es necesario descargarlo.")
        else:
            download_now = questionary.confirm(
                f"¿Quieres descargar el modelo '{model_name}' ahora con ollama?", default=True
            ).ask()
            while download_now:
                if download_ollama_model(model_name):
                    break
                download_now = questionary.confirm(
                    "No se pudo descargar el modelo. ¿Quieres intentarlo de nuevo?", default=False
                ).ask()

    print("\n" + "═" * 60)
    print(" ✅ CONFIGURACIÓN COMPLETADA CON ÉXITO")
    print(f" Motor: {provider}")
    print(f" Modelo: {model_name}")
    print(f" Personalidad: {p_name}")
    print("\nPara abrir la interfaz usa: python3 web_server.py")
    print(" ═" * 60 + "\n")


if __name__ == "__main__":
    run_wizard()
