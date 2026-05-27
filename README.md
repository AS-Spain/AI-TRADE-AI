# 🤖 AI-TRADE-AI

Una asistente de IA conversacional con voz sintetizada localmente, usando Ollama + Piper + Whisper. Interactúa con personajes animados con emociones y memoria.

## ✨ Características

- **🧠 IA Local**: Ejecuta LLMs como Llama3, Mistral directamente en tu máquina con Ollama
- **🎤 Voz Natural**: Síntesis de voz con Piper (sin conexión a internet)
- **👂 Transcripción**: Faster-Whisper para STT local
- **🎭 Emociones**: Los personajes responden con emociones (feliz, triste, sarcástico, etc)
- **💾 Memoria**: Guarda el contexto de conversaciones para continuidad
- **⚡ Sin dependencias online**: Todo funciona localmente
- **🔧 Personalizable**: Crea tus propios personajes y skins

## 📋 Requisitos

- Python 3.9+
- Ubuntu/Debian (Linux recomendado)
- 4GB RAM mínimo (8GB recomendado para LLMs)

## 🚀 Instalación Rápida

```bash
# 1. Clonar repositorio
git clone https://github.com/AS-Spain/AI-TRADE-AI.git
cd AI-TRADE-AI

# 2. Ejecutar instalador (configura todo automáticamente)
bash setup_linux.sh

# 3. Iniciar wizard de configuración
source venv/bin/activate
python wizard.py
```

## 💬 Uso

```bash
# Activar entorno virtual
source venv/bin/activate

# Opción 1: Conversación interactiva
python main.py

# Opción 2: Web UI
python web_server.py
# Abre http://localhost:5000
```

## 📦 Estructura del Proyecto

```
├── core/              # Motor principal
│   ├── brain.py       # IA/LLM logic
│   ├── audio_engine.py # Voz (Piper + Whisper)
│   ├── memory.py      # Base de datos de contexto
│   └── config_manager.py
├── characters/        # Personajes (Luna, Riko, etc)
├── ui/               # Web UI (HTML)
└── tools/            # Binarios (Piper, Whisper)
```

## ⚙️ Configuración

Edita `db/config.json` o ejecuta `python wizard.py` para:
- Elegir modelo LLM (Llama3, Mistral, etc)
- Configurar voz y idioma
- Seleccionar personaje activo

## 🔗 Links Útiles

- [Ollama](https://ollama.ai) - Ejecuta LLMs localmente
- [Piper TTS](https://github.com/rhasspy/piper) - Síntesis de voz
- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) - Reconocimiento de voz

## 📝 Licencia

MIT License - Usa libremente
