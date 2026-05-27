#!/bin/bash

# AI-TRADE-AI - Quick Start Guide
# Este script te ayuda a empezar rápidamente

echo "🤖 Bienvenido a AI-TRADE-AI"
echo "============================="
echo ""

# Verificar si estamos en el directorio correcto
if [ ! -f "main.py" ]; then
    echo "❌ Error: Ejecuta este script desde la raíz del proyecto"
    exit 1
fi

# 1. Activar venv
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

echo "✅ Activando entorno virtual..."
source venv/bin/activate

# 2. Instalar dependencias
echo "📥 Instalando dependencias..."
pip install -r requirements.txt

# 3. Crear directorios necesarios
mkdir -p db logs

# 4. Verificar setup de audio/piper
if [ ! -f "./tools/piper/piper" ]; then
    echo "⚠️  Piper TTS no encontrado"
    echo "   Para audio local, ejecuta: bash setup_linux.sh"
fi

echo ""
echo "✅ ¡Configuración completada!"
echo ""
echo "Próximos pasos:"
echo "1. python wizard.py          # Configurar IA, voz y personaje"
echo "2. python main.py            # Comenzar a chatear"
echo "3. python web_server.py      # Abrir interfaz web"
