#!/bin/bash
set -euo pipefail

# Colores para la terminal
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}--- Character Engine Linux Installer ---${NC}"

# 1. Dependencias
sudo apt update && sudo apt install -y python3-venv ffmpeg curl libasound2-dev build-essential python3-dev libyaml-dev libsndfile1

# 2. Entorno Python
if [ ! -d "venv" ]; then
    python3 -m venv venv || {
        echo -e "${CYAN}Error creando el entorno virtual. Reinstalando python3-venv y reintentando...${NC}"
        sudo apt install -y python3-venv
        python3 -m venv venv
    }
fi
source venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel packaging

if [ -f "requirements.txt" ]; then
    if ! python3 -m pip install -r requirements.txt; then
        echo -e "${CYAN}La instalación de requirements falló. Instalando paquetes básicos y pyyaml con fallback...${NC}"
        python3 -m pip install requests questionary flask pydantic faster-whisper
        python3 -m pip install --no-use-pep517 pyyaml==6.0
    fi
else
    python3 -m pip install requests questionary flask pydantic faster-whisper
    python3 -m pip install --no-use-pep517 pyyaml==6.0
fi

# 3. Piper TTS Local
if [ ! -d "tools/piper" ]; then
    mkdir -p tools/piper && cd tools/piper
    wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz
    tar -xf piper_amd64.tar.gz && rm piper_amd64.tar.gz
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/carl/low/es_ES-carl-low.onnx
    cd ../..
fi

# 4. Lanzar Wizard si no hay config
if [ ! -f "db/config.json" ]; then
    python3 wizard.py
fi

# 5. Instalar Ollama local si no está presente
if ! command -v ollama >/dev/null 2>&1; then
    echo -e "${CYAN}Instalando Ollama local...${NC}"
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo -e "${GREEN}Ollama ya está instalado.${NC}"
fi

if command -v ollama >/dev/null 2>&1; then
    echo -e "${GREEN}Ollama instalado correctamente.${NC}"
    echo -e "Puedes traer un modelo con: ${CYAN}ollama pull <modelo>${NC}"
else
    echo -e "${CYAN}No se pudo instalar Ollama automáticamente. Visita https://ollama.com para instalarlo manualmente.${NC}"
fi

echo -e "${GREEN}📦 Instalación lista.${NC}"
echo -e "Para cambiar la configuración ejecuta: ${CYAN}python3 wizard.py${NC}"
echo -e "Para iniciar la Web UI ejecuta: ${CYAN}python3 web_server.py${NC}"
