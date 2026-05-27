import logging
import sys
from core.brain import Brain
from core.audio_engine import AudioEngine
from core.config_manager import load_config
from core.memory import MemoryManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("🚀 Iniciando AI-TRADE-AI...")
    
    # Cargar configuración
    config = load_config()
    
    # Validar configuración
    if not config.get('setup_complete'):
        print("\n❌ Primero debes configurar el sistema.")
        print("   Ejecuta: python wizard.py")
        sys.exit(1)
    
    if not config['llm']['model']:
        print("\n❌ No hay modelo LLM configurado.")
        print("   Ejecuta: python wizard.py")
        sys.exit(1)
    
    # Configurar Personalidad (IA)
    personality = {
        "name": config.get('active_personality', 'Luna'),
        "model": config['llm']['model'],
        "instructions": "Eres una asistente amable y sarcástica. Responde siempre en JSON."
    }

    logger.info(f"✅ Configuración cargada: {personality['name']}")
    print(f"\n--- Sistema {personality['name']} Online ---")
    print("Escribe 'salir' para terminar o 'help' para ayuda\n")

    # Inicializar motores
    try:
        brain = Brain()
        logger.info("✅ Brain inicializado")
    except Exception as e:
        logger.error(f"❌ Error al inicializar Brain: {e}")
        print("❌ No se puede conectar con el modelo LLM")
        print("   Asegúrate de que Ollama esté ejecutándose: ollama serve")
        sys.exit(1)

    try:
        audio = AudioEngine()
        logger.info("✅ Audio Engine inicializado")
    except Exception as e:
        logger.warning(f"⚠️  Audio no disponible: {e}")
        audio = None

    memory = MemoryManager()
    logger.info("✅ Memory Manager inicializado")

    # Loop principal
    conversation_history = []
    message_count = 0

    while True:
        try:
            user_input = input("👤 Tú: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["salir", "exit", "quit"]:
                print(f"\n👋 {personality['name']}: ¡Hasta luego! ({message_count} mensajes guardados)")
                break
            
            if user_input.lower() == "help":
                print("""
Comandos:
  help    - Mostrar esta ayuda
  clear   - Limpiar historial
  status  - Ver configuración
  salir   - Terminar programa
                """)
                continue
            
            if user_input.lower() == "clear":
                conversation_history = []
                print("🧹 Historial limpiado")
                continue

            if user_input.lower() == "status":
                print(f"  Personalidad: {personality['name']}")
                print(f"  Modelo: {config['llm']['model']}")
                print(f"  Mensajes: {message_count}")
                continue

            # Procesar con IA
            logger.debug(f"Usuario: {user_input}")
            response = brain.process(personality, user_input, conversation_history)
            
            # Guardar en memoria
            memory.save_message(personality['name'], "user", user_input)
            memory.save_message(personality['name'], "assistant", response.get('text', ''))
            
            # Mostrar respuesta
            print(f"🎭 [{response.get('emotion', 'neutro').upper()}] {personality['name']}: {response.get('text', '')}")
            
            # Hablar (si audio está disponible)
            if audio:
                try:
                    audio.speak(response.get('text', ''))
                except Exception as e:
                    logger.warning(f"⚠️  No se pudo reproducir audio: {e}")
            
            # Guardar en historial
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": response.get('text', '')})
            
            # Limitar historial a últimos 20 mensajes
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
            
            message_count += 1
            
        except KeyboardInterrupt:
            print(f"\n\n👋 Terminado por el usuario")
            break
        except Exception as e:
            logger.error(f"❌ Error durante conversación: {e}")
            print(f"❌ Error: {e}")
            print("   Intenta de nuevo o escribe 'salir' para terminar")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"❌ Error crítico: {e}")
        sys.exit(1)
