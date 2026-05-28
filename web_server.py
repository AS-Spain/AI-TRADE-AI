from flask import Flask, request, jsonify, render_template_string, send_from_directory
from core.config_manager import load_config, save_config, register_clear_saved_config_on_exit
from core.brain import Brain
import os
import tempfile

# --- MOTORES DE AUDIO ---
try:
    from core.audio_engine import AudioEngine
except Exception as _err:
    _audio_load_error = str(_err)
    class AudioEngine:
        def __init__(self, *args, **kwargs):
            print('⚠️ AudioEngine no disponible:', _audio_load_error)
        def transcribe(self, *a, **k):
            return "STT no disponible"
        def speak(self, *a, **k):
            pass

from core.loader import load_character, list_characters

app = Flask(__name__)

# Permitir archivos grandes (VRM)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 

@app.after_request
def add_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
    return response

brain_engine = Brain()
audio_engine = AudioEngine()

def get_active_character():
    config = load_config()
    char_name = config.get('active_personality', '')
    if char_name and os.path.isdir(os.path.join('characters', char_name)):
        return load_character(char_name)
    characters = list_characters()
    return load_character(characters[0]) if characters else None

# --- RUTAS DE ARCHIVOS ---
@app.route('/ui/<path:filename>')
def ui_static(filename):
    return send_from_directory('ui', filename)

@app.route('/characters/<character>/<path:filename>')
def character_asset(character, filename):
    return send_from_directory(os.path.join('characters', character), filename)

@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory('uploads', filename)

@app.route('/vr')
def vr():
    return send_from_directory('ui', 'vr.html')

# --- API VRM ---
@app.route('/api/vr-character')
def vr_character():
    config = load_config()
    character = get_active_character()
    vrm_url = None
    if character and hasattr(character, 'vrm') and character.vrm:
        vrm_filename = os.path.basename(character.vrm)
        vrm_url = f"/characters/{character.name}/{vrm_filename}"
    else:
        vrm_url = config.get('active_vrm')
    return jsonify({
        'name': character.name if character else 'Luna',
        'personality': character.personality if character else '',
        'vrm_url': vrm_url
    })

# --- APIS DE CHAT Y VOZ ---
@app.route('/api/chat', methods=['POST'])
def chat_api():
    config = load_config()
    user_text = request.json.get('text')
    character = get_active_character()
    personality_config = {
        "name": character.name if character else config['active_personality'],
        "instructions": character.personality if character else "Eres una IA amable."
    }
    brain_engine.config = config
    brain_engine.llm_settings = config.get('llm', {})
    try:
        response = brain_engine.process(personality_config, user_text, [])
    except Exception as e:
        response = {"text": f"Error: {str(e)}", "emotion": "sad", "name": "System"}
    return jsonify(response)

@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    if 'audio' not in request.files: return jsonify({'status': 'error'}), 400
    audio_file = request.files['audio']
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
        audio_file.save(tmp.name)
        temp_path = tmp.name
    try:
        transcript = audio_engine.transcribe(temp_path)
        return jsonify({'status': 'ok', 'transcript': transcript})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

@app.route('/api/config', methods=['POST'])
def update_config():
    data = request.json
    config = load_config()
    config['llm']['model'] = data['model']
    config['active_personality'] = data['personality']
    save_config(config)
    return jsonify({"status": "ok"})

# --- INTERFAZ HTML (ESTO ES LO QUE VE EL NAVEGADOR) ---
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>AI-TRADE-AI Terminal</title>
    <style>
        :root { --primary: #00ffcc; --bg: #0a0a0a; --panel: #111; }
        body { background: var(--bg); color: var(--primary); font-family: 'Courier New', monospace; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        .sidebar { width: 300px; background: var(--panel); border-right: 1px solid #333; padding: 20px; display: flex; flex-direction: column; }
        .main-chat { flex-grow: 1; display: flex; flex-direction: column; padding: 20px; }
        #chat-window { flex-grow: 1; overflow-y: auto; border: 1px solid #222; padding: 15px; background: #000; border-radius: 5px; margin-bottom: 20px; }
        .msg { margin-bottom: 15px; line-height: 1.4; }
        .msg.user { color: #fff; }
        .msg.bot { color: var(--primary); }
        .input-area { display: flex; gap: 10px; }
        input { flex-grow: 1; background: #000; border: 1px solid var(--primary); color: white; padding: 12px; border-radius: 5px; }
        button { background: var(--primary); color: #000; border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; border-radius: 5px; }
        .small-button { margin-top: 10px; background: transparent; border: 1px solid var(--primary); color: var(--primary); padding: 8px; cursor: pointer; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>⚙️ Configuración</h2>
        <p style="font-size:0.8rem; color:#888;">Modelo: {{ c.llm.model }}</p>
        <p style="font-size:0.8rem; color:#888;">Personaje: {{ c.active_personality }}</p>
        <button class="small-button" onclick="window.location.href='/vr'">🥽 ABRIR VISTA VR</button>
    </div>
    <div class="main-chat">
        <div id="chat-window">
            <div class="msg bot">Terminal cargada. Lista para chatear.</div>
        </div>
        <div class="audio-controls" style="margin-bottom:10px;">
            <button id="record-btn" onclick="toggleRecording()">🎤 Grabar Voz</button>
        </div>
        <div class="input-area">
            <input type="text" id="user-input" placeholder="Escribe tu mensaje..." onkeypress="if(event.key==='Enter') sendMsg()">
            <button onclick="sendMsg()">ENVIAR</button>
        </div>
    </div>
    <script>
        let mediaRecorder, audioChunks = [], recording = false;

        async function toggleRecording() {
            if (recording) { mediaRecorder.stop(); return; }
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
            mediaRecorder.onstop = async () => {
                const blob = new Blob(audioChunks, { type: 'audio/webm' });
                const fd = new FormData();
                fd.append('audio', blob, 'input.webm');
                const r = await fetch('/api/transcribe', { method: 'POST', body: fd });
                const d = await r.json();
                if (d.status === 'ok') document.getElementById('user-input').value = d.transcript;
                recording = false;
                document.getElementById('record-btn').innerText = '🎤 Grabar Voz';
            };
            mediaRecorder.start();
            recording = true;
            document.getElementById('record-btn').innerText = '⏹️ Detener';
        }

        async function sendMsg() {
            const input = document.getElementById('user-input');
            const text = input.value.trim();
            if(!text) return;
            const chatWin = document.getElementById('chat-window');
            chatWin.innerHTML += `<div class="msg user"><b>Tú:</b> ${text}</div>`;
            input.value = '';
            const r = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text})
            });
            const d = await r.json();
            chatWin.innerHTML += `<div class="msg bot"><b>${d.name}:</b> ${d.text}</div>`;
            chatWin.scrollTop = chatWin.scrollHeight;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    config = load_config()
    # ESTO es lo que hace que se vea el HTML y no el código Python
    return render_template_string(HTML, c=config)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)