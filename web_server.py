from flask import Flask, request, jsonify, render_template_string, send_from_directory
from core.config_manager import load_config, save_config, register_clear_saved_config_on_exit
from core.brain import Brain
from core.audio_engine import AudioEngine
from core.loader import load_character, list_characters
import os
import tempfile

app = Flask(__name__)

# Instanciamos el cerebro y el motor de audio
brain_engine = Brain()
audio_engine = AudioEngine()


def get_active_character():
    config = load_config()
    char_name = config.get('active_personality', '')
    if char_name and os.path.isdir(os.path.join('characters', char_name)):
        return load_character(char_name)

    characters = list_characters()
    if characters:
        return load_character(characters[0])
    return None


@app.route('/ui/<path:filename>')
def ui_static(filename):
    return send_from_directory('ui', filename)


@app.route('/characters/<character>/<path:filename>')
def character_asset(character, filename):
    return send_from_directory(os.path.join('characters', character), filename)


@app.route('/api/vr-character')
def vr_character():
    config = load_config()
    character = get_active_character()

    if not character:
        return jsonify({
            'name': 'Sin personaje',
            'personality': 'Sin personalidad definida',
            'avatar_url': '',
            'emotions': [],
            'vrm_url': config.get('active_vrm')
        })

    vrm = config.get('active_vrm')
    # Normalizar la URL para que sea absoluta desde la raíz del servidor
    if vrm and not (vrm.startswith('/') or vrm.startswith('http')):
        vrm = '/' + vrm

    return jsonify({
        'name': character.name,
        'personality': character.personality,
        'avatar_url': f"/characters/{character.name}/{character.avatar}",
        'emotions': list(character.animations.keys()),
        'vrm_url': vrm
    })


@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory('uploads', filename)


@app.route('/api/upload-vrm', methods=['POST'])
def upload_vrm():
    if 'vrm' not in request.files:
        return jsonify({'status': 'error', 'message': 'No se recibió archivo .vrm'}), 400

    file = request.files['vrm']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'Nombre de archivo inválido'}), 400

    if not file.filename.lower().endswith('.vrm'):
        return jsonify({'status': 'error', 'message': 'Solo se aceptan archivos .vrm'}), 400

    os.makedirs('uploads', exist_ok=True)
    safe_name = file.filename.replace(' ', '_')
    save_path = os.path.join('uploads', safe_name)
    file.save(save_path)

    config = load_config()
    config['active_vrm'] = f"/uploads/{safe_name}"
    save_config(config)

    return jsonify({'status': 'ok', 'vrm_url': config['active_vrm'], 'filename': safe_name})


@app.route('/vr')
def vr():
    return send_from_directory('ui', 'vr.html')


HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Character OS - Terminal</title>
    <style>
        :root { --primary: #00ffcc; --bg: #0a0a0a; --panel: #111; }
        body { background: var(--bg); color: var(--primary); font-family: 'Courier New', monospace; margin: 0; display: flex; height: 100vh; }
        
        /* Sidebar de Configuración */
        .sidebar { width: 300px; background: var(--panel); border-right: 1px solid #333; padding: 20px; display: flex; flex-direction: column; }
        .sidebar h2 { font-size: 1.2rem; border-bottom: 1px solid #333; padding-bottom: 10px; }
        .input-group { margin-bottom: 15px; }
        label { display: block; font-size: 0.8rem; color: #888; margin-bottom: 5px; }
        input, select { width: 100%; background: #000; border: 1px solid #333; color: white; padding: 8px; border-radius: 4px; box-sizing: border-box; }
        
        /* Área de Chat */
        .main-chat { flex-grow: 1; display: flex; flex-direction: column; padding: 20px; position: relative; }
        #chat-window { flex-grow: 1; overflow-y: auto; border: 1px solid #222; padding: 15px; background: #000; border-radius: 5px; margin-bottom: 20px; }
        .msg { margin-bottom: 15px; line-height: 1.4; }
        .msg.user { color: #fff; }
        .msg.bot { color: var(--primary); }
        .emotion-tag { font-size: 0.7rem; background: #222; padding: 2px 5px; border-radius: 3px; margin-right: 5px; }

        /* Input */
        .input-area { display: grid; grid-template-columns: 1fr auto; gap: 12px; }
        .input-area input { width: 100%; padding: 14px; font-size: 1rem; border: 1px solid var(--primary); border-radius: 6px; background: #000; color: white; }
        button { background: var(--primary); color: #000; border: none; padding: 12px 16px; font-weight: bold; cursor: pointer; border-radius: 8px; }
        button:hover { opacity: 0.92; }
        .status-box { background: #111; border: 1px solid #222; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 8px; }
        .status-box div { font-size: 0.93rem; }
        .status-box strong { color: #fff; }
        .status-line { margin-top: 10px; font-size: 0.85rem; color: #8fd7c1; }
        .note { font-size: 0.84rem; color: #aaa; }
        .small-button { margin-top: 12px; background: transparent; border: 1px solid #00ffcc; color: #00ffcc; padding: 10px 14px; border-radius: 8px; font-size: 0.95rem; }
        .small-button:hover { opacity: 0.9; }
        code { background: #111; padding: 2px 6px; border-radius: 4px; color: #a6f5e0; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>⚙️ Configuración rápida</h2>
        <div class="status-box">
            <div><strong>Proveedor:</strong> {{ c.llm.provider or 'No configurado' }}</div>
            <div><strong>Modelo:</strong> {{ c.llm.model or 'No configurado' }}</div>
            <div><strong>Personalidad:</strong> {{ c.active_personality or 'No configurada' }}</div>
            <div><strong>Audio local:</strong> {{ 'ON' if c.audio.tts_local else 'OFF' }}</div>
            <div class="status-line">{{ 'Listo para chatear' if c.llm.provider and c.llm.model else 'Aún falta configuración' }}</div>
        </div>

        <div class="input-group">
            <label>Modelo LLM</label>
            <input type="text" name="model" id="cfg-model" value="{{ c.llm.model }}" placeholder="ej: llama3, gpt-3.5-turbo">
        </div>

        <div class="input-group">
            <label>Personalidad</label>
            <input type="text" name="personality" id="cfg-personality" value="{{ c.active_personality }}" placeholder="ej: Luna, Asistente">
        </div>

        <button type="button" onclick="saveConfig()">Guardar y aplicar</button>
        <button type="button" class="small-button" onclick="copySetupCommand()">Copiar comando de setup</button>
        <button type="button" class="small-button" onclick="window.location.href='/vr'">Abrir vista VR</button>
        <div class="note">Cambia el modelo o la personalidad y pulsa Guardar para actualizar el chat.</div>
        <div class="note">Si no has configurado el motor, ejecuta <code>python3 wizard.py</code> en la terminal.</div>
    </div>

    <div class="main-chat">
        <div id="chat-window">
            <div class="msg bot"><span class="emotion-tag">SYSTEM</span> Bienvenido a Character OS. Escribe tu primera pregunta.</div>
        </div>
        <div class="audio-controls" style="margin-bottom: 15px; display:flex; align-items:center; gap:10px;">
            <button type="button" id="record-button" onclick="toggleRecording()">🎤 Grabar</button>
            <span id="record-status">Listo para grabar</span>
        </div>
        <div id="transcript-area" class="note">Transcripción: <span id="transcript-text">Aquí aparecerá tu voz convertida a texto.</span></div>
        <div class="input-area">
            <input type="text" id="user-input" placeholder="Escribe tu mensaje aquí..." onkeypress="if(event.key==='Enter') sendMsg()">
            <button onclick="sendMsg()">ENVIAR</button>
        </div>
    </div>

    <script>
        let mediaRecorder = null;
        let audioChunks = [];
        let recording = false;

        async function toggleRecording() {
            if (recording) {
                mediaRecorder.stop();
                return;
            }

            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                alert('Tu navegador no soporta grabación de audio. Usa Chrome o Firefox modernos.');
                return;
            }

            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    document.getElementById('record-status').innerText = 'Grabación lista. Transcribiendo...';
                    await sendAudio(audioBlob);
                    stream.getTracks().forEach(track => track.stop());
                };
                mediaRecorder.start();
                recording = true;
                document.getElementById('record-button').innerText = '⏹️ Detener';
                document.getElementById('record-status').innerText = 'Grabando... habla ahora.';
            } catch (err) {
                alert('No se pudo acceder al micrófono: ' + err.message);
            }
        }

        async function sendAudio(blob) {
            const formData = new FormData();
            formData.append('audio', blob, 'input.webm');
            try {
                const response = await fetch('/api/transcribe', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                if (data.status === 'ok') {
                    const transcript = data.transcript || '';
                    document.getElementById('transcript-text').innerText = transcript || 'No se detectó voz.';
                    document.getElementById('user-input').value = transcript;
                    document.getElementById('record-status').innerText = 'Transcripción lista.';
                } else {
                    document.getElementById('transcript-text').innerText = 'Error: ' + (data.message || 'No se pudo transcribir');
                    document.getElementById('record-status').innerText = 'Error en transcripción.';
                }
            } catch (err) {
                document.getElementById('transcript-text').innerText = 'Error en la petición: ' + err.message;
                document.getElementById('record-status').innerText = 'Error en transcripción.';
            } finally {
                recording = false;
                document.getElementById('record-button').innerText = '🎤 Grabar';
            }
        }

        function speakResponse(text) {
            if (!text || !window.speechSynthesis) return;
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'es-ES';
            window.speechSynthesis.speak(utterance);
        }

        async function sendMsg() {
            const input = document.getElementById('user-input');
            const chatWin = document.getElementById('chat-window');
            const text = input.value.trim();
            if (!text) return;

            chatWin.innerHTML += `<div class="msg user"><b>Tú:</b> ${escapeHtml(text)}</div>`;
            input.value = '';
            chatWin.scrollTop = chatWin.scrollHeight;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text})
                });
                const data = await response.json();
                chatWin.innerHTML += `<div class="msg bot"><span class="emotion-tag">${escapeHtml(data.emotion.toUpperCase())}</span><b>${escapeHtml(data.name || 'Bot')}:</b> ${escapeHtml(data.text)}</div>`;
                speakResponse(data.text);
            } catch (e) {
                chatWin.innerHTML += `<div class="msg bot" style="color:#ff6b6b">Error: no se pudo conectar con el motor de IA.</div>`;
            }
            chatWin.scrollTop = chatWin.scrollHeight;
        }

        async function saveConfig() {
            const model = document.getElementById('cfg-model').value.trim();
            const personality = document.getElementById('cfg-personality').value.trim();
            if (!model || !personality) {
                alert('Por favor completa modelo y personalidad antes de guardar.');
                return;
            }
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({model, personality})
            });
            const result = await response.json();
            if (result.status === 'ok') {
                alert('Configuración actualizada correctamente.');
            } else {
                alert('Error al guardar la configuración.');
            }
        }

        function copySetupCommand() {
            const command = 'python3 wizard.py';
            navigator.clipboard.writeText(command).then(() => {
                alert('Comando copiado al portapapeles. Pégalo en la terminal.');
            }).catch(() => {
                alert('No se pudo copiar automáticamente. Usa este comando: ' + command);
            });
        }

        function escapeHtml(text) {
            return text.replace(/[&<>\"]/g, function(match) {
                return ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;'}[match]);
            });
        }

        document.getElementById('user-input').focus();
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    config = load_config()
    return render_template_string(HTML, c=config)

@app.route('/api/chat', methods=['POST'])
def chat_api():
    config = load_config()
    user_text = request.json.get('text')
    
    personality_config = {
        "name": config['active_personality'],
        "instructions": f"Eres {config['active_personality']}, una IA que responde de forma concisa."
    }
    
    response = None
    if config['llm']['provider'] and config['llm']['model']:
        brain_engine.config = config
        brain_engine.llm_settings = config['llm']
        try:
            response = brain_engine.process(personality_config, user_text, [])
        except Exception as e:
            response = {
                "text": f"No se pudo conectar con el modelo: {str(e)}",
                "emotion": "error",
                "name": config['active_personality']
            }

    if response is None:
        response = {
            "text": "Aún no hay un motor de IA configurado. Ejecuta el wizard para conectar Ollama o una API externa y vuelve a intentarlo.",
            "emotion": "warning",
            "name": config['active_personality'] or 'Sistema'
        }

    return jsonify(response)

@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    if 'audio' not in request.files:
        return jsonify({'status': 'error', 'message': 'No se envió audio'}), 400

    audio_file = request.files['audio']
    if not audio_file.filename:
        return jsonify({'status': 'error', 'message': 'Nombre de archivo inválido'}), 400

    suffix = os.path.splitext(audio_file.filename)[1] or '.wav'
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
    config = load_config()
    config['llm']['model'] = data['model']
    config['active_personality'] = data['personality']
    save_config(config)
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    register_clear_saved_config_on_exit()
    app.run(host='0.0.0.0', port=5000)
