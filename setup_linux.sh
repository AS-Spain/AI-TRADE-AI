#!/bin/bash
set -euo pipefail

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}--- Character Engine Linux Installer ---${NC}"

# 1. Dependencias del sistema
sudo apt update && sudo apt install -y \
    python3-venv ffmpeg curl \
    libasound2-dev build-essential \
    python3-dev libyaml-dev libsndfile1 \
    libespeak-ng1 espeak-ng

# 2. Entorno Python
if [ ! -d "venv" ]; then
    python3 -m venv venv || {
        echo -e "${CYAN}Error creando venv, reintentando...${NC}"
        sudo apt install -y python3-venv
        python3 -m venv venv
    }
fi
source venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel packaging

if [ -f "requirements.txt" ]; then
    if ! python3 -m pip install -r requirements.txt; then
        echo -e "${YELLOW}requirements.txt falló, instalando paquetes base...${NC}"
        python3 -m pip install requests questionary flask pydantic faster-whisper piper-tts
        python3 -m pip install --no-use-pep517 pyyaml==6.0
    fi
else
    python3 -m pip install requests questionary flask pydantic faster-whisper piper-tts
    python3 -m pip install --no-use-pep517 pyyaml==6.0
fi

# 3. Piper TTS — modelos de voz
pip install piper-tts
echo -e "${CYAN}Descargando modelos de voz Piper...${NC}"
mkdir -p models/voices

# Mujer adulta (es_ES)
if [ ! -f "models/voices/es_ES-sharvard-medium.onnx" ]; then
    echo -e "${CYAN}Descargando voz: mujer...${NC}"
    wget -q --show-progress -O models/voices/es_ES-sharvard-medium.onnx \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx"
    wget -q -O models/voices/es_ES-sharvard-medium.onnx.json \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx.json"
fi

# Hombre adulto (es_ES)
if [ ! -f "models/voices/es_ES-davefx-medium.onnx" ]; then
    echo -e "${CYAN}Descargando voz: hombre...${NC}"
    wget -q --show-progress -O models/voices/es_ES-davefx-medium.onnx \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx"
    wget -q -O models/voices/es_ES-davefx-medium.onnx.json \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json"
fi

# Mujer joven — usamos mls_10246 (es) como base para niña
if [ ! -f "models/voices/es-mls_10246-low.onnx" ]; then
    echo -e "${CYAN}Descargando voz: niña (base)...${NC}"
    wget -q --show-progress -O models/voices/es-mls_10246-low.onnx \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/mls_10246/low/es_ES-mls_10246-low.onnx"
    wget -q -O models/voices/es-mls_10246-low.onnx.json \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/mls_10246/low/es_ES-mls_10246-low.onnx.json"
fi

# Hombre joven — usamos mls_9972 (es) como base para niño
if [ ! -f "models/voices/es-mls_9972-low.onnx" ]; then
    echo -e "${CYAN}Descargando voz: niño (base)...${NC}"
    wget -q --show-progress -O models/voices/es-mls_9972-low.onnx \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/mls_9972/low/es_ES-mls_9972-low.onnx"
    wget -q -O models/voices/es-mls_9972-low.onnx.json \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/mls_9972/low/es_ES-mls_9972-low.onnx.json"
fi

echo -e "${GREEN}✅ Modelos de voz descargados en models/voices/${NC}"

# 4. Ollama
if ! command -v ollama >/dev/null 2>&1; then
    echo -e "${CYAN}Instalando Ollama...${NC}"
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo -e "${GREEN}Ollama ya instalado.${NC}"
fi

# 5. Wizard si no hay config
if [ ! -f "db/config.json" ]; then
    python3 wizard.py
fi

echo -e "${GREEN}📦 Instalación lista.${NC}"
echo -e "Iniciar servidor: ${CYAN}python3 web_server.py${NC}"