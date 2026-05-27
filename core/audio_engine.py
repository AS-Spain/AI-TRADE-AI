import os
import subprocess
import logging
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class AudioEngine:
    def __init__(self, model_size="tiny"):
        # STT Local con Faster-Whisper
        logger.info(f"⌛ Cargando Whisper ({model_size}) en CPU/GPU...")
        print(f"⌛ Cargando Whisper ({model_size})...")
        try:
            self.stt_model = WhisperModel(model_size, device="cpu", compute_type="int8")
            logger.info("✅ Whisper cargado")
        except Exception as e:
            logger.error(f"❌ Error al cargar Whisper: {e}")
            raise
        
        # Rutas de Piper
        self.piper_path = "./tools/piper/piper"
        self.voice_model = "./tools/piper/es_ES-low.onnx"

    def transcribe(self, audio_file):
        """Usa Faster-Whisper para transcripción local"""
        try:
            if not os.path.exists(audio_file):
                raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_file}")
            
            logger.debug(f"Transcribiendo: {audio_file}")
            segments, info = self.stt_model.transcribe(audio_file, beam_size=5)
            text = " ".join([segment.text for segment in segments])
            result = text.strip()
            logger.info(f"✅ Transcripción: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Error en transcripción: {e}")
            raise

    def speak(self, text):
        """Usa Piper TTS para generar voz instantánea"""
        if not text or not text.strip():
            logger.warning("⚠️  Intento de reproducir texto vacío")
            return

        if not os.path.exists(self.piper_path):
            logger.error(f"❌ Piper no encontrado en {self.piper_path}")
            print("❌ Error: Piper no encontrado. Ejecuta setup_linux.sh")
            return

        if not os.path.exists(self.voice_model):
            logger.warning(f"⚠️  Modelo de voz no encontrado: {self.voice_model}")
            print("⚠️  Modelo de voz no encontrado")
            return

        # Comando Linux: texto -> piper -> aplay (reproductor de audio de Linux)
        # Esto evita crear archivos temporales pesados y reproduce directo al hardware
        safe_text = text.replace('"', '\\"').replace('$', '\\$')
        command = f'echo "{safe_text}" | {self.piper_path} --model {self.voice_model} --output_raw | aplay -r 22050 -f S16_LE -t raw 2>/dev/null'
        
        try:
            logger.debug(f"Reproduciendo audio: {text[:50]}...")
            subprocess.Popen(command, shell=True)
        except Exception as e:
            logger.error(f"❌ Error en TTS: {e}")
            print(f"❌ Error en audio: {e}")
