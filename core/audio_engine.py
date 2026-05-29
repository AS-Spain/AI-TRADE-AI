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

    def speak(self, text, language='es'):
        """Usa Piper TTS para generar archivo de voz"""
        if not text or not text.strip():
            logger.warning("⚠️  Intento de reproducir texto vacío")
            return None

        if not os.path.exists(self.piper_path):
            logger.error(f"❌ Piper no encontrado en {self.piper_path}")
            print("❌ Error: Piper no encontrado. Ejecuta setup_linux.sh")
            return None

        if not os.path.exists(self.voice_model):
            logger.warning(f"⚠️  Modelo de voz no encontrado: {self.voice_model}")
            print("⚠️  Modelo de voz no encontrado")
            return None

        # Crear archivo temporal para el audio
        import tempfile
        output_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False, dir='uploads').name
        
        safe_text = text.replace('"', '\\"').replace('$', '\\$')
        command = f'echo "{safe_text}" | {self.piper_path} --model {self.voice_model} --output_file {output_file} 2>/dev/null'
        
        try:
            logger.debug(f"Generando audio: {text[:50]}...")
            result = subprocess.run(command, shell=True, capture_output=True, timeout=30)
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                logger.info(f"✅ Audio generado: {output_file}")
                return output_file
            else:
                logger.error("❌ Piper no generó archivo de audio válido")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Timeout generando audio")
            return None
        except Exception as e:
            logger.error(f"❌ Error en TTS: {e}")
            print(f"❌ Error en audio: {e}")
            return None
