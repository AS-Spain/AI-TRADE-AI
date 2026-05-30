import os
import subprocess
import tempfile
import logging
import wave
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

VOICE_MODELS = {
    'mujer': {
        'model': 'models/voices/es_ES-sharvard-medium.onnx',
        'config': 'models/voices/es_ES-sharvard-medium.onnx.json',
        'pitch': None
    },
    'hombre': {
        'model': 'models/voices/es_ES-davefx-medium.onnx',
        'config': 'models/voices/es_ES-davefx-medium.onnx.json',
        'pitch': None
    },
    'nina': {
        'model': 'models/voices/es-mls_10246-low.onnx',
        'config': 'models/voices/es-mls_10246-low.onnx.json',
        'pitch': 4
    },
    'nino': {
        'model': 'models/voices/es-mls_9972-low.onnx',
        'config': 'models/voices/es-mls_9972-low.onnx.json',
        'pitch': 3
    }
}

try:
    from piper import PiperVoice
    PIPER_PYTHON = True
except ImportError:
    PIPER_PYTHON = False
    logger.warning("⚠️ piper-tts Python no disponible, usando binario")

PIPER_BINARY = './tools/piper/piper'


class AudioEngine:
    def __init__(self, model_size="tiny"):
        print(f"⌛ Cargando Whisper ({model_size})...")
        try:
            self.stt_model = WhisperModel(model_size, device="cpu", compute_type="int8")
        except Exception as e:
            logger.error(f"❌ Error cargando Whisper: {e}")
            raise
        self._voice_cache = {}

    def _get_piper_voice(self, voice_key):
        if voice_key in self._voice_cache:
            return self._voice_cache[voice_key]
        cfg = VOICE_MODELS.get(voice_key)
        if not cfg:
            return None
        model_path = cfg['model']
        if not os.path.exists(model_path):
            logger.error(f"❌ Modelo no encontrado: {model_path}")
            return None
        try:
            voice = PiperVoice.load(model_path)
            self._voice_cache[voice_key] = voice
            return voice
        except Exception as e:
            logger.error(f"❌ Error cargando voz {voice_key}: {e}")
            return None

    def _apply_pitch(self, wav_path, semitones):
        if not semitones:
            return wav_path
        try:
            r = subprocess.run(['which', 'sox'], capture_output=True)
            if r.returncode != 0:
                return wav_path
            out = wav_path.replace('.wav', '_pitched.wav')
            subprocess.run(['sox', wav_path, out, 'pitch', str(semitones * 100)], capture_output=True, timeout=15)
            if os.path.exists(out) and os.path.getsize(out) > 0:
                os.remove(wav_path)
                return out
        except Exception as e:
            logger.warning(f"⚠️ Error pitch: {e}")
        return wav_path

    def _speak_python(self, text, voice_key):
        voice = self._get_piper_voice(voice_key)
        if not voice:
            return None
        try:
            output_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False, dir='uploads').name
            with wave.open(output_file, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(voice.config.sample_rate)
                voice.synthesize_wav(text, wf)
            size = os.path.getsize(output_file) if os.path.exists(output_file) else 0
            if size <= 44:
                logger.error(f'❌ WAV vacío: {size} bytes')
                return None
            pitch = VOICE_MODELS[voice_key].get('pitch')
            if pitch:
                output_file = self._apply_pitch(output_file, pitch)
            logger.info(f"✅ Audio generado ({voice_key}): {output_file}")
            return output_file
        except Exception as e:
            logger.error(f'❌ Error en speak_python: {e}')
            return None

    def _speak_binary(self, text, voice_key):
        if not os.path.exists(PIPER_BINARY):
            return None
        cfg = VOICE_MODELS.get(voice_key)
        if not cfg or not os.path.exists(cfg['model']):
            return None
        output_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False, dir='uploads').name
        safe_text = text.replace('"', '\\"').replace('$', '\\$').replace('`', '')
        cmd = f'echo "{safe_text}" | {PIPER_BINARY} --model {cfg["model"]} --output_file {output_file} 2>/dev/null'
        try:
            subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
            if os.path.exists(output_file) and os.path.getsize(output_file) > 44:
                pitch = cfg.get('pitch')
                if pitch:
                    output_file = self._apply_pitch(output_file, pitch)
                return output_file
            return None
        except Exception as e:
            logger.error(f"❌ Error en speak_binary: {e}")
            return None

    def speak(self, text, voice_key='mujer'):
        if not text or not text.strip():
            return None
        voice_key = voice_key if voice_key in VOICE_MODELS else 'mujer'
        if PIPER_PYTHON:
            result = self._speak_python(text, voice_key)
            if result:
                return result
            logger.warning("⚠️ speak_python falló, intentando binario...")
        return self._speak_binary(text, voice_key)

    def transcribe(self, audio_file):
        try:
            if not os.path.exists(audio_file):
                raise FileNotFoundError(f"Audio no encontrado: {audio_file}")
            segments, _ = self.stt_model.transcribe(audio_file, beam_size=5)
            return ' '.join(seg.text for seg in segments).strip()
        except Exception as e:
            logger.error(f"❌ Error transcripción: {e}")
            raise

    def list_voices(self):
        return {
            key: {
                'available': os.path.exists(cfg['model']),
                'model': cfg['model'],
                'pitch_shift': cfg.get('pitch')
            }
            for key, cfg in VOICE_MODELS.items()
        }
