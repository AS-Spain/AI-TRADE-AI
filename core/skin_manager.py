import yaml
import os

class SkinManager:
    """Carga aspectos visuales sin tocar la lógica del cerebro"""
    def __init__(self, skin_name):
        self.skin_path = f"skins/{skin_name}"
        self.config = self._load_config()

    def _load_config(self):
        with open(f"{self.skin_path}/skin.yaml", 'r') as f:
            return yaml.safe_load(f)

    def get_animation(self, emotion):
        # Si la emoción no tiene animación propia, usa 'idle'
        anim_file = self.config['animations'].get(emotion, self.config['animations'].get('idle'))
        return os.path.join(self.skin_path, anim_file)
