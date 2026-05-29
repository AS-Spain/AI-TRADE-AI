from flask import Flask, request, jsonify, render_template_string, send_from_directory
from core.config_manager import load_config, save_config
from core.brain import Brain
from core.memory import MemoryManager
import os
import tempfile
import json
import uuid
import base64
import shutil

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

@app.after_request
def add_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
    return response

try:
    from core.audio_engine import AudioEngine
    audio_engine = AudioEngine()
except Exception as _err:
    print('⚠️ AudioEngine no disponible:', _err)
    class AudioEngine:
        def transcribe(self, *a, **k): return "STT no disponible"
    audio_engine = AudioEngine()

from core.loader import load_character, list_characters
brain_engine = Brain()
memory = MemoryManager()

os.makedirs('uploads', exist_ok=True)
os.makedirs('profiles', exist_ok=True)
os.makedirs(os.path.join('uploads', '_chunks'), exist_ok=True)

def get_active_character():
    config = load_config()
    char_name = config.get('active_personality', '')
    if char_name and os.path.isdir(os.path.join('characters', char_name)):
        return load_character(char_name)
    characters = list_characters()
    return load_character(characters[0]) if characters else None

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

PROFILES_DIR = 'profiles'

@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    profiles = []
    try:
        for f in os.listdir(PROFILES_DIR):
            if f.endswith('.json'):
                try:
                    with open(os.path.join(PROFILES_DIR, f), 'r', encoding='utf-8') as fp:
                        profiles.append(json.load(fp))
                except Exception as e:
                    print(f'⚠️ Error leyendo perfil {f}: {e}')
    except Exception as e:
        print(f'⚠️ Error listando profiles: {e}')
    return jsonify(profiles)

@app.route('/api/profiles', methods=['POST'])
def save_profile():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'Sin datos'}), 400
    if not data.get('id'):
        data['id'] = str(uuid.uuid4())
    path = os.path.join(PROFILES_DIR, f"{data['id']}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return jsonify({'status': 'ok', 'profile': data})

@app.route('/api/profiles/<profile_id>', methods=['DELETE'])
def delete_profile(profile_id):
    path = os.path.join(PROFILES_DIR, f"{profile_id}.json")
    if os.path.exists(path):
        os.remove(path)
    return jsonify({'status': 'ok'})

@app.route('/api/vr-character')
def vr_character():
    config = load_config()
    character = get_active_character()

    vrm_url = ''
    active_vrm = config.get('active_vrm', '')

    if active_vrm and active_vrm not in ['/uploads', '/uploads/']:
        clean = active_vrm.lstrip('/')
        if os.path.exists(clean):
            vrm_url = active_vrm

    if not vrm_url and character and hasattr(character, 'vrm') and character.vrm:
        vrm_filename = os.path.basename(character.vrm)
        vrm_path = os.path.join('characters', character.name, vrm_filename)
        if os.path.exists(vrm_path):
            vrm_url = f"/characters/{character.name}/{vrm_filename}"

    if vrm_url and not vrm_url.startswith('http'):
        vrm_url = request.host_url.rstrip('/') + '/' + vrm_url.lstrip('/')

    return jsonify({
        'name': character.name if character else 'Sin personaje',
        'personality': character.personality if character else '',
        'vrm_url': vrm_url or None
    })

@app.route('/api/upload-vrm-chunk', methods=['POST'])
def upload_vrm_chunk():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'Sin datos'}), 400

    filename = data.get('filename', '').replace(' ', '_')
    chunk_index = data.get('chunkIndex', 0)
    total_chunks = data.get('totalChunks', 1)
    chunk_b64 = data.get('data', '')

    if not filename or not chunk_b64:
        return jsonify({'status': 'error', 'message': 'Faltan campos'}), 400

    try:
        chunk_bytes = base64.b64decode(chunk_b64)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error base64: {e}'}), 400

    tmp_dir = os.path.join('uploads', '_chunks', filename)
    os.makedirs(tmp_dir, exist_ok=True)

    chunk_path = os.path.join(tmp_dir, str(chunk_index))
    with open(chunk_path, 'wb') as f:
        f.write(chunk_bytes)

    app.logger.info(f"Chunk {chunk_index+1}/{total_chunks} de {filename} guardado")

    if chunk_index == total_chunks - 1:
        final_path = os.path.join('uploads', filename)
        try:
            with open(final_path, 'wb') as out:
                for i in range(total_chunks):
                    cp = os.path.join(tmp_dir, str(i))
                    with open(cp, 'rb') as cf:
                        out.write(cf.read())
            shutil.rmtree(tmp_dir, ignore_errors=True)
            size = os.path.getsize(final_path)
            app.logger.info(f"VRM reconstruido: {final_path} ({size} bytes)")
            # NO tocar active_vrm global
            return jsonify({'status': 'ok', 'vrm_url': f"/uploads/{filename}", 'filename': filename})
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Error reconstruyendo: {e}'}), 500

    return jsonify({'status': 'chunk_ok', 'chunkIndex': chunk_index})

@app.route('/api/upload-vrm', methods=['POST'])
def upload_vrm():
    if 'vrm' not in request.files:
        return jsonify({'status': 'error', 'message': 'No se recibió archivo'}), 400
    file = request.files['vrm']
    if not file.filename:
        return jsonify({'status': 'error', 'message': 'Nombre inválido'}), 400
    filename = file.filename.replace(' ', '_')
    save_path = os.path.join('uploads', filename)
    file.save(save_path)
    size = os.path.getsize(save_path)
    app.logger.info(f"VRM guardado: {save_path} ({size} bytes)")
    # NO tocar active_vrm global
    return jsonify({'status': 'ok', 'vrm_url': f"/uploads/{filename}", 'filename': filename})

@app.route('/api/chat', methods=['POST'])
def chat_api():
    config = load_config()
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'Sin datos'}), 400

    char_name = data.get('name') or config.get('active_personality', 'IA')
    personality = data.get('personality') or 'Eres una IA amable.'
    text = data.get('text', '')

    if not text:
        return jsonify({'text': 'No recibí texto.', 'name': char_name, 'emotion': 'neutral'})

    contexto = memory.get_context(char_name)
    try:
        memory.save_message(char_name, 'user', text)
        res = brain_engine.process({'name': char_name, 'instructions': personality}, text, contexto)
        memory.save_message(char_name, 'bot', res.get('text', ''))
        res['name'] = char_name
        return jsonify(res)
    except Exception as e:
        app.logger.error(f'Error chat: {e}')
        return jsonify({'text': f'Error: {str(e)}', 'name': char_name, 'emotion': 'neutral'})

@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    if 'audio' not in request.files:
        return jsonify({'status': 'error', 'message': 'No se envió audio'}), 400
    audio_file = request.files['audio']
    suffix = os.path.splitext(audio_file.filename)[1] or '.webm'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        audio_file.save(tmp.name)
        temp_path = tmp.name
    try:
        transcript = audio_engine.transcribe(temp_path)
        return jsonify({'status': 'ok', 'transcript': transcript})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

@app.route('/api/config', methods=['POST'])
def update_config():
    data = request.json
    if not data:
        return jsonify({'status': 'error'}), 400
    config = load_config()
    if 'model' in data:
        config['llm']['model'] = data['model']
    if 'personality' in data:
        config['active_personality'] = data['personality']
    save_config(config)
    return jsonify({'status': 'ok'})

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Character OS - Terminal</title>
    <style>
        :root { --primary: #00ffcc; --bg: #0a0a0a; --panel: #111; }
        body { background: var(--bg); color: var(--primary); font-family: 'Courier New', monospace; margin: 0; display: flex; height: 100vh; }
        .sidebar { width: 300px; background: var(--panel); border-right: 1px solid #333; padding: 20px; display: flex; flex-direction: column; gap: 10px; }
        .main { flex-grow: 1; display: flex; flex-direction: column; padding: 20px; }
        #chat-window { flex-grow: 1; overflow-y: auto; border: 1px solid #222; padding: 15px; background: #000; border-radius: 5px; margin-bottom: 20px; }
        .input-area { display: grid; grid-template-columns: 1fr auto; gap: 12px; }
        input { padding: 14px; font-size: 1rem; border: 1px solid var(--primary); border-radius: 6px; background: #000; color: white; width: 100%; }
        button { background: var(--primary); color: #000; border: none; padding: 12px 16px; font-weight: bold; cursor: pointer; border-radius: 8px; }
        .msg-user { color: #fff; margin: 8px 0; }
        .msg-bot { color: var(--primary); margin: 8px 0; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>⚙️ Character OS</h2>
        <button onclick="window.location.href='/vr'" style="background:#ff0055; color:white;">🥽 ABRIR VR</button>
    </div>
    <div class="main">
        <div id="chat-window"></div>
        <div style="margin-bottom:10px;">
            <button id="record-button" onclick="toggleRecording()" style="background:#ff0055; color:white;">🎤 Grabar Voz</button>
        </div>
        <div class="input-area">
            <input type="text" id="user-input" placeholder="Escribe..." onkeypress="if(event.key==='Enter') sendMsg()">
            <button onclick="sendMsg()">ENVIAR</button>
        </div>
    </div>
    <script>
        let mediaRecorder = null, audioChunks = [], recording = false;
        async function toggleRecording() {
            if (recording) { mediaRecorder.stop(); recording = false; document.getElementById('record-button').innerText = '🎤 Grabar Voz'; return; }
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                mediaRecorder.onstop = async () => {
                    const fd = new FormData();
                    fd.append('audio', new Blob(audioChunks, { type: 'audio/webm' }), 'input.webm');
                    const r = await fetch('/api/transcribe', { method: 'POST', body: fd });
                    const d = await r.json();
                    if (d.status === 'ok') { document.getElementById('user-input').value = d.transcript; sendMsg(); }
                    stream.getTracks().forEach(t => t.stop());
                };
                mediaRecorder.start();
                recording = true;
                document.getElementById('record-button').innerText = '⏹️ Parar';
            } catch (err) { alert('Micrófono: ' + err.message); }
        }
        async function sendMsg() {
            const input = document.getElementById('user-input');
            const text = input.value.trim();
            if (!text) return;
            const win = document.getElementById('chat-window');
            win.innerHTML += `<div class="msg-user"><b>Tú:</b> ${text}</div>`;
            input.value = '';
            win.scrollTop = win.scrollHeight;
            try {
                const r = await fetch('/api/chat', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({text}) });
                const d = await r.json();
                win.innerHTML += `<div class="msg-bot"><b>${d.name || 'Bot'}:</b> ${d.text}</div>`;
            } catch (e) {
                win.innerHTML += `<div class="msg-bot" style="color:#ff6b6b">Error: ${e.message}</div>`;
            }
            win.scrollTop = win.scrollHeight;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    config = load_config()
    return render_template_string(HTML, c=config)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)