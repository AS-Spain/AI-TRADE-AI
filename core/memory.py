import sqlite3
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self, db_path="db/memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_name TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS character_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_name TEXT,
                    fact TEXT,
                    importance INTEGER
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_char_time ON conversation_history(character_name, timestamp)')
            conn.commit()
            conn.close()
            logger.info(f"✅ Base de datos inicializada: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Error al inicializar BD: {e}")
            raise

    def save_message(self, character_name, role, content):
        """Guarda un mensaje en el historial"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversation_history (character_name, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (character_name, role, content, datetime.now())
            )
            conn.commit()
            conn.close()
            logger.debug(f"💾 Mensaje guardado: {character_name} ({role})")
        except Exception as e:
            logger.error(f"❌ Error al guardar mensaje: {e}")
            raise

    def get_context(self, character_name, limit=10):
        """Obtiene el contexto reciente de conversación"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM conversation_history WHERE character_name = ? ORDER BY timestamp DESC LIMIT ?",
                (character_name, limit)
            )
            rows = cursor.fetchall()
            conn.close()
            # Invertimos para que el orden sea cronológico: [antiguo -> nuevo]
            return [{"role": r, "content": c} for r, c in reversed(rows)]
        except Exception as e:
            logger.error(f"❌ Error al obtener contexto: {e}")
            return []

    def clear_history(self, character_name):
        """Limpia el historial de un personaje"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversation_history WHERE character_name = ?", (character_name,))
            conn.commit()
            conn.close()
            logger.info(f"🧹 Historial limpiado: {character_name}")
        except Exception as e:
            logger.error(f"❌ Error al limpiar historial: {e}")
            raise

    def get_stats(self, character_name):
        """Obtiene estadísticas del personaje"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*), SUM(CASE WHEN role='user' THEN 1 ELSE 0 END) FROM conversation_history WHERE character_name = ?",
                (character_name,)
            )
            total, user_msgs = cursor.fetchone()
            conn.close()
            return {"total_messages": total or 0, "user_messages": user_msgs or 0, "ai_messages": (total or 0) - (user_msgs or 0)}
        except Exception as e:
            logger.error(f"❌ Error al obtener estadísticas: {e}")
            return {}
