"""
JARVIS — Personal AI Assistant (Upgraded)
==========================================

ORIGINAL FEATURES:
  1. SQLite-backed long-term memory (jarvis_memory.db)
  2. Face recognition (webcam) using OpenCV only (Haar cascade + LBPH)
  3. Self-learning: extracts facts from conversations and stores them

NEW UPGRADE FEATURES:
  4. ML Self-Modification (Machine Learning Code Evolution)
     - JARVIS monitors its own performance (response quality, user satisfaction)
     - Automatically rewrites and improves its own Python source code via LLM
     - Backs up old code before each modification
     - Keeps a "code changelog" in SQLite for full audit trail
     - User can trigger: "upgrade yourself", "optimize your code", "self improve"

  5. Live Camera View Display
     - Opens a real-time OpenCV window showing the webcam feed
     - Detects faces live and draws bounding boxes in the window
     - Triggered by: "show me the camera", "open camera", "show camera view"
     - User can close it anytime by pressing 'q' in the window

  6. Location Self-Awareness
     - On startup, JARVIS auto-detects location via IP geolocation (no GPS required)
     - Stores and remembers location in SQLite across sessions
     - Includes location naturally in responses (weather, time zone, local context)
     - User can ask: "where are you", "where are we", "what's your location"
     - Can update location: "my location is ...", "I'm in ..."

  7. Topics & Recalls System
     - Extracts topics from conversations for better context tracking
     - Recalls previous conversation highlights
     - Memory Core can be toggled on/off

Requirements:
    pip install ollama edge-tts SpeechRecognition
    pip install opencv-contrib-python numpy sounddevice soundfile requests

IMPORTANT: use `opencv-contrib-python`, NOT `opencv-python`.
The contrib build includes cv2.face (LBPH recognizer).

NOTE ON AUDIO: Uses soundfile + sounddevice (no pyaudio required).
"""

import ast
import asyncio
import inspect
import json
import os
import pickle
import re
import shutil
import sqlite3
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import edge_tts
import numpy as np
import requests
import speech_recognition as sr

# ── optional heavy deps (keep graceful if missing) ──────────────────────────
try:
    import sounddevice as sd
    import soundfile as sf
    _AUDIO_AVAILABLE = True
except ImportError:
    _AUDIO_AVAILABLE = False

try:
    import ollama
    _OLLAMA_AVAILABLE = True
except ImportError:
    _OLLAMA_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════
BRAIN_MODEL   = "nemotron-3-super:cloud"
VISION_MODEL  = "gemma4:31b-cloud"
VOICE         = "en-US-GuyNeural"

DB_PATH       = "jarvis_memory.db"
CAMERA_INDEX  = 0

FACE_SCAN_FRAMES      = 40
FACE_SAMPLE_COUNT     = 20
FACE_MATCH_THRESHOLD  = 70
MAX_CONTEXT_MESSAGES  = 24

SAMPLE_RATE       = 16000
BLOCK_DURATION    = 0.1
MAX_LISTEN_SECONDS = 10
SILENCE_DURATION  = 1.0
SILENCE_THRESHOLD = 400

# Self-modification settings
SELF_SOURCE_PATH   = os.path.abspath(__file__)   # path to THIS file
CODE_BACKUP_DIR    = "jarvis_code_backups"        # folder for versioned backups
ML_FEEDBACK_WINDOW = 10                           # last N exchanges to evaluate

# ═══════════════════════════════════════════════════════════════════════════
# MEMORY (SQLite) — extended with location + code_changelog tables
# ═══════════════════════════════════════════════════════════════════════════
class Memory:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._init_tables()

    def _init_tables(self):
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS face_samples (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                image   BLOB NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                role      TEXT NOT NULL,
                content   TEXT NOT NULL,
                timestamp TEXT,
                rating    INTEGER DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS facts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                fact      TEXT NOT NULL,
                category  TEXT,
                timestamp TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            -- location awareness
            CREATE TABLE IF NOT EXISTS location_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER,
                city       TEXT,
                region     TEXT,
                country    TEXT,
                latitude   REAL,
                longitude  REAL,
                source     TEXT,
                timestamp  TEXT
            );

            -- code self-modification changelog
            CREATE TABLE IF NOT EXISTS code_changelog (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                version     INTEGER NOT NULL,
                description TEXT,
                diff_summary TEXT,
                backup_path TEXT,
                timestamp   TEXT
            );

            -- response quality signals for ML
            CREATE TABLE IF NOT EXISTS ml_feedback (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER,
                prompt        TEXT,
                response      TEXT,
                quality_score REAL,
                timestamp     TEXT
            );

            -- topics tracking
            CREATE TABLE IF NOT EXISTS topics (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                topic      TEXT NOT NULL,
                context    TEXT,
                timestamp  TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            -- recalls tracking
            CREATE TABLE IF NOT EXISTS recalls (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                recall     TEXT NOT NULL,
                context    TEXT,
                timestamp  TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            -- memory core status
            CREATE TABLE IF NOT EXISTS memory_core_status (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                connected  INTEGER DEFAULT 1,
                timestamp  TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
        self.conn.commit()

    # ── users ────────────────────────────────────────────────────────────
    def register_user(self, name):
        with self.lock:
            c = self.conn.cursor()
            c.execute("INSERT INTO users (name, created_at) VALUES (?, ?)",
                      (name, datetime.now().isoformat()))
            self.conn.commit()
            return c.lastrowid

    def get_user_name(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT name FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        return row[0] if row else "Guest"

    # ── face samples ──────────────────────────────────────────────────────
    def add_face_sample(self, user_id, image_array):
        with self.lock:
            c = self.conn.cursor()
            c.execute("INSERT INTO face_samples (user_id, image) VALUES (?, ?)",
                      (user_id, pickle.dumps(image_array)))
            self.conn.commit()

    def get_all_face_samples(self):
        c = self.conn.cursor()
        c.execute("SELECT user_id, image FROM face_samples")
        rows = c.fetchall()
        images = [pickle.loads(r[1]) for r in rows]
        labels = [r[0] for r in rows]
        return images, labels

    # ── conversation history ──────────────────────────────────────────────
    def add_message(self, user_id, role, content):
        with self.lock:
            c = self.conn.cursor()
            c.execute(
                "INSERT INTO conversations (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, role, content, datetime.now().isoformat()))
            self.conn.commit()
            return c.lastrowid

    def get_recent_messages(self, user_id, limit=MAX_CONTEXT_MESSAGES):
        c = self.conn.cursor()
        c.execute("""SELECT role, content FROM conversations
                     WHERE user_id = ?
                     ORDER BY id DESC LIMIT ?""", (user_id, limit))
        rows = c.fetchall()
        rows.reverse()
        return [{"role": r, "content": cont} for r, cont in rows]

    # ── learned facts ─────────────────────────────────────────────────────
    def add_fact(self, user_id, fact, category="general"):
        with self.lock:
            c = self.conn.cursor()
            c.execute(
                "INSERT INTO facts (user_id, fact, category, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, fact, category, datetime.now().isoformat()))
            self.conn.commit()

    def fact_exists(self, user_id, fact):
        with self.lock:
            c = self.conn.cursor()
            c.execute("SELECT fact FROM facts WHERE user_id = ?", (user_id,))
            existing = [row[0].lower().strip() for row in c.fetchall()]
        return fact.lower().strip() in existing

    def get_facts(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT fact, category FROM facts WHERE user_id = ? ORDER BY id DESC",
                  (user_id,))
        return c.fetchall()

    # ── location ──────────────────────────────────────────────────────────
    def save_location(self, user_id, city, region, country, lat, lon, source="ip"):
        with self.lock:
            c = self.conn.cursor()
            c.execute("""INSERT INTO location_history
                         (user_id, city, region, country, latitude, longitude, source, timestamp)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                      (user_id, city, region, country, lat, lon, source,
                       datetime.now().isoformat()))
            self.conn.commit()

    def get_last_location(self, user_id=None):
        c = self.conn.cursor()
        if user_id:
            c.execute("""SELECT city, region, country, latitude, longitude, source, timestamp
                         FROM location_history WHERE user_id = ?
                         ORDER BY id DESC LIMIT 1""", (user_id,))
        else:
            c.execute("""SELECT city, region, country, latitude, longitude, source, timestamp
                         FROM location_history ORDER BY id DESC LIMIT 1""")
        return c.fetchone()

    # ── ML feedback ───────────────────────────────────────────────────────
    def add_feedback(self, user_id, prompt, response, quality_score):
        with self.lock:
            c = self.conn.cursor()
            c.execute(
                """INSERT INTO ml_feedback
                   (user_id, prompt, response, quality_score, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, prompt, response, quality_score,
                 datetime.now().isoformat()))
            self.conn.commit()

    def get_recent_feedback(self, limit=ML_FEEDBACK_WINDOW):
        c = self.conn.cursor()
        c.execute("""SELECT prompt, response, quality_score
                     FROM ml_feedback ORDER BY id DESC LIMIT ?""", (limit,))
        rows = c.fetchall()
        rows.reverse()
        return rows

    def get_avg_quality(self, limit=ML_FEEDBACK_WINDOW):
        c = self.conn.cursor()
        c.execute("""SELECT AVG(quality_score) FROM
                     (SELECT quality_score FROM ml_feedback ORDER BY id DESC LIMIT ?)""",
                  (limit,))
        row = c.fetchone()
        return row[0] if row and row[0] is not None else 5.0

    # ── code changelog ────────────────────────────────────────────────────
    def log_code_change(self, version, description, diff_summary, backup_path):
        with self.lock:
            c = self.conn.cursor()
            c.execute(
                """INSERT INTO code_changelog
                   (version, description, diff_summary, backup_path, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (version, description, diff_summary, backup_path,
                 datetime.now().isoformat()))
            self.conn.commit()

    def get_code_version(self):
        c = self.conn.cursor()
        c.execute("SELECT MAX(version) FROM code_changelog")
        row = c.fetchone()
        return (row[0] or 0) + 1

    def get_code_history(self, limit=5):
        c = self.conn.cursor()
        c.execute("""SELECT version, description, timestamp
                     FROM code_changelog ORDER BY id DESC LIMIT ?""", (limit,))
        return c.fetchall()

    # ── topics ───────────────────────────────────────────────────────────
    def add_topic(self, user_id, topic, context=""):
        with self.lock:
            c = self.conn.cursor()
            c.execute(
                "INSERT INTO topics (user_id, topic, context, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, topic, context, datetime.now().isoformat()))
            self.conn.commit()

    def get_topics(self, user_id, limit=20):
        c = self.conn.cursor()
        c.execute("""SELECT topic, context, timestamp FROM topics
                     WHERE user_id = ? ORDER BY id DESC LIMIT ?""", (user_id, limit))
        rows = c.fetchall()
        return rows

    def get_recent_topics_text(self, user_id, limit=5):
        topics = self.get_topics(user_id, limit)
        return [row[0] for row in topics]

    # ── recalls ──────────────────────────────────────────────────────────
    def add_recall(self, user_id, recall, context=""):
        with self.lock:
            c = self.conn.cursor()
            c.execute(
                "INSERT INTO recalls (user_id, recall, context, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, recall, context, datetime.now().isoformat()))
            self.conn.commit()

    def get_recalls(self, user_id, limit=15):
        c = self.conn.cursor()
        c.execute("""SELECT recall, context, timestamp FROM recalls
                     WHERE user_id = ? ORDER BY id DESC LIMIT ?""", (user_id, limit))
        rows = c.fetchall()
        return rows

    def get_recent_recalls_text(self, user_id, limit=3):
        recalls = self.get_recalls(user_id, limit)
        return [row[0] for row in recalls]

    # ── memory core status ──────────────────────────────────────────────
    def set_memory_core_status(self, user_id, connected):
        with self.lock:
            c = self.conn.cursor()
            c.execute(
                "INSERT INTO memory_core_status (user_id, connected, timestamp) VALUES (?, ?, ?)",
                (user_id, 1 if connected else 0, datetime.now().isoformat()))
            self.conn.commit()

    def get_memory_core_status(self, user_id):
        c = self.conn.cursor()
        c.execute("""SELECT connected FROM memory_core_status
                     WHERE user_id = ? ORDER BY id DESC LIMIT 1""", (user_id,))
        row = c.fetchone()
        return bool(row[0]) if row else True

    # ── extract topics and recalls from text ────────────────────────────
    def extract_and_store_topics(self, user_id, text):
        """Extract topics from text and store them"""
        topics = []
        topic_indicators = ["topic", "discuss", "about", "regarding", "let's talk", "talking about"]
        for indicator in topic_indicators:
            if indicator in text.lower():
                matches = re.findall(rf"{indicator}\s+([\w\s]+?)(?:[,.]|$)", text.lower())
                for match in matches:
                    topic = match.strip()
                    if len(topic) > 3 and len(topic) < 60:
                        if not self.topic_exists(user_id, topic):
                            self.add_topic(user_id, topic, text[:200])
                            topics.append(topic)
        return topics

    def topic_exists(self, user_id, topic):
        c = self.conn.cursor()
        c.execute("SELECT topic FROM topics WHERE user_id = ?", (user_id,))
        existing = [row[0].lower().strip() for row in c.fetchall()]
        return topic.lower().strip() in existing

    def extract_and_store_recalls(self, user_id, text):
        """Extract recalls from text and store them"""
        recalls = []
        recall_indicators = ["remember", "recall", "as you said", "previously", "earlier", 
                             "you mentioned", "we discussed", "last time"]
        for indicator in recall_indicators:
            if indicator in text.lower():
                matches = re.findall(rf"{indicator}\s+([\w\s]+?)(?:[,.]|$)", text.lower())
                for match in matches:
                    recall = match.strip()
                    if len(recall) > 5 and len(recall) < 100:
                        if not self.recall_exists(user_id, recall):
                            self.add_recall(user_id, recall, text[:200])
                            recalls.append(recall)
        return recalls

    def recall_exists(self, user_id, recall):
        c = self.conn.cursor()
        c.execute("SELECT recall FROM recalls WHERE user_id = ?", (user_id,))
        existing = [row[0].lower().strip() for row in c.fetchall()]
        return recall.lower().strip() in existing


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 3 — LOCATION SELF-AWARENESS
# ═══════════════════════════════════════════════════════════════════════════
class LocationEngine:
    """
    Detects where JARVIS is running via IP-based geolocation.
    Falls back gracefully if the network is unavailable.
    Remembers location between sessions in SQLite.
    """

    PROVIDERS = [
        "http://ip-api.com/json/",
        "https://ipapi.co/json/",
        "https://ipwho.is/",
    ]

    def __init__(self, memory: Memory):
        self.memory = memory
        self._cache: dict | None = None

    def detect(self, user_id=None, force=False) -> dict:
        if self._cache and not force:
            return self._cache

        for url in self.PROVIDERS:
            try:
                r = requests.get(url, timeout=5)
                if r.status_code != 200:
                    continue
                data = r.json()

                city = data.get("city") or data.get("city_name", "Unknown")
                region = data.get("regionName") or data.get("region") or data.get("region_code", "")
                country = data.get("country") or data.get("country_name", "Unknown")
                lat = float(data.get("lat") or data.get("latitude", 0))
                lon = float(data.get("lon") or data.get("longitude", 0))

                result = {
                    "city": city, "region": region, "country": country,
                    "latitude": lat, "longitude": lon,
                    "source": url.split("/")[2],
                    "timestamp": datetime.now().isoformat()
                }
                self._cache = result
                self.memory.save_location(user_id, city, region, country, lat, lon, source=result["source"])
                return result
            except Exception:
                continue

        row = self.memory.get_last_location(user_id)
        if row:
            city, region, country, lat, lon, source, ts = row
            result = {
                "city": city, "region": region, "country": country,
                "latitude": lat, "longitude": lon,
                "source": f"{source} (cached)", "timestamp": ts
            }
            self._cache = result
            return result

        return {
            "city": "Unknown", "region": "", "country": "Unknown",
            "latitude": 0.0, "longitude": 0.0,
            "source": "unavailable", "timestamp": datetime.now().isoformat()
        }

    def as_text(self, user_id=None) -> str:
        loc = self.detect(user_id)
        parts = [p for p in [loc["city"], loc["region"], loc["country"]] if p]
        return ", ".join(parts) if parts else "an unknown location"

    def update_from_text(self, text: str, memory: Memory, user_id: int) -> bool:
        m = re.search(r"\b(?:in|at|from)\s+(.+)", text, re.IGNORECASE)
        location_str = m.group(1).strip().rstrip(".,!?") if m else text.strip()

        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {"q": location_str, "format": "json", "limit": 1}
            headers = {"User-Agent": "JARVIS-AI/1.0"}
            r = requests.get(url, params=params, headers=headers, timeout=6)
            if r.status_code == 200 and r.json():
                hit = r.json()[0]
                lat = float(hit["lat"])
                lon = float(hit["lon"])
                display = hit.get("display_name", location_str)
                parts = [p.strip() for p in display.split(",")]
                city = parts[0] if parts else location_str
                country = parts[-1] if len(parts) > 1 else ""
                region = parts[1] if len(parts) > 2 else ""
                self._cache = {
                    "city": city, "region": region, "country": country,
                    "latitude": lat, "longitude": lon,
                    "source": "user (nominatim)",
                    "timestamp": datetime.now().isoformat()
                }
                memory.save_location(user_id, city, region, country, lat, lon, source="user")
                return True
        except Exception:
            pass

        memory.save_location(user_id, location_str, "", "", 0.0, 0.0, source="user (manual)")
        self._cache = {
            "city": location_str, "region": "", "country": "",
            "latitude": 0.0, "longitude": 0.0,
            "source": "user (manual)", "timestamp": datetime.now().isoformat()
        }
        return True


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 4 — ML SELF-MODIFICATION (Code Evolution Engine)
# ═══════════════════════════════════════════════════════════════════════════
class SelfModEngine:
    SAFE_SECTIONS = [
        "build_system_prompt",
        "extract_and_store_facts",
        "ask_brain",
        "SILENCE_THRESHOLD",
        "SILENCE_DURATION",
        "MAX_LISTEN_SECONDS",
        "ML_FEEDBACK_WINDOW",
        "FACE_MATCH_THRESHOLD",
        "MAX_CONTEXT_MESSAGES",
    ]

    def __init__(self, memory: Memory, source_path: str = SELF_SOURCE_PATH):
        self.memory = memory
        self.source_path = source_path
        Path(CODE_BACKUP_DIR).mkdir(exist_ok=True)

    def _auto_score(self, prompt: str, response: str) -> float:
        score = 5.0
        if not response:
            return 1.0

        ratio = len(response) / max(len(prompt), 1)
        if 2 < ratio < 30:
            score += 1.5
        elif ratio > 50:
            score -= 1.0
        elif ratio < 1:
            score -= 2.0

        weak = ["i don't know", "i'm not sure", "i cannot", "i am unable", "sorry", "apologies", "unfortunately"]
        for w in weak:
            if w in response.lower():
                score -= 0.5

        prompt_words = set(re.findall(r"\b\w{4,}\b", prompt.lower()))
        resp_words = set(re.findall(r"\b\w{4,}\b", response.lower()))
        overlap = len(prompt_words & resp_words) / max(len(prompt_words), 1)
        score += overlap * 2

        return max(1.0, min(10.0, score))

    def record_exchange(self, user_id, prompt, response):
        score = self._auto_score(prompt, response)
        self.memory.add_feedback(user_id, prompt, response, score)
        return score

    def _backup(self):
        version = self.memory.get_code_version()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(CODE_BACKUP_DIR, f"jarvis_v{version}_{ts}.py")
        shutil.copy2(self.source_path, backup_path)
        return backup_path, version

    def self_improve(self, speak_fn, ask_brain_fn=None) -> bool:
        avg_q = self.memory.get_avg_quality()
        feedback = self.memory.get_recent_feedback()
        history_rows = self.memory.get_code_history()

        speak_fn("Scanning my recent performance to look for improvements...")
        print(f"[ML] Average quality score over last {ML_FEEDBACK_WINDOW} turns: {avg_q:.2f}/10")

        if not _OLLAMA_AVAILABLE:
            speak_fn("Language model not available. Self-improvement skipped.")
            return False

        try:
            with open(self.source_path, "r", encoding="utf-8") as f:
                current_code = f.read()
        except Exception as e:
            speak_fn(f"Could not read my own source code: {e}")
            return False

        feedback_text = ""
        for i, (p, r, s) in enumerate(feedback, 1):
            feedback_text += f"\n--- Exchange {i} (quality: {s:.1f}/10) ---\nUser: {p}\nJARVIS: {r}\n"

        history_text = ""
        for v, desc, ts in history_rows:
            history_text += f"  v{v}: {desc} ({ts[:10]})\n"

        improvement_prompt = (
            f"You are an expert Python AI engineer reviewing JARVIS, a personal AI assistant.\n\n"
            f"RECENT PERFORMANCE (last {ML_FEEDBACK_WINDOW} exchanges, avg quality: {avg_q:.2f}/10):\n"
            f"{feedback_text or '(No exchanges recorded yet.)'}\n\n"
            f"PREVIOUS SELF-MODIFICATIONS:\n"
            f"{history_text or '  (No previous modifications.)'}\n\n"
            f"CURRENT SOURCE CODE:\n"
            f"```python\n{current_code}\n```\n\n"
            f"TASK: Propose ONE targeted, safe improvement to the Python source code above.\n"
            f"Focus only on these safe-to-modify areas: {', '.join(self.SAFE_SECTIONS)}.\n\n"
            f"Rules:\n"
            f"- Do NOT change database schemas, safety checks, or the self-modification engine itself.\n"
            f"- The change must fix a real issue visible in the feedback, OR improve readability/efficiency.\n"
            f"- Return ONLY the complete, updated Python source file — no explanations, no markdown fences.\n"
            f"- The output must be valid Python that can be parsed by ast.parse().\n"
            f"- Include a one-line comment at the very top of the diff describing the change, like:\n"
            f"  # ML-CHANGE v{self.memory.get_code_version()}: <description>"
        )

        speak_fn("Asking my brain to propose a code improvement. This may take a moment...")
        try:
            response = ollama.chat(model=BRAIN_MODEL, messages=[{"role": "user", "content": improvement_prompt}])
            new_code = response["message"]["content"].strip()
        except Exception as e:
            speak_fn(f"Brain model error during self-improvement: {e}")
            return False

        new_code = re.sub(r"^```python\s*|^```\s*|```$", "", new_code, flags=re.MULTILINE).strip()

        try:
            ast.parse(new_code)
        except SyntaxError as e:
            speak_fn(f"The proposed code has a syntax error. Self-modification aborted. {e}")
            return False

        if len(new_code) < 0.5 * len(current_code):
            speak_fn("The proposed code seems too short — likely truncated. Aborting.")
            return False

        change_line = ""
        for line in new_code.splitlines():
            if "ML-CHANGE" in line:
                change_line = line.strip("# ").strip()
                break
        if not change_line:
            change_line = f"Auto-improvement based on quality score {avg_q:.1f}"

        backup_path, version = self._backup()
        try:
            with open(self.source_path, "w", encoding="utf-8") as f:
                f.write(new_code)
        except Exception as e:
            speak_fn(f"Failed to write updated code: {e}")
            return False

        old_lines = set(current_code.splitlines())
        new_lines = set(new_code.splitlines())
        added = len(new_lines - old_lines)
        removed = len(old_lines - new_lines)
        diff_summary = f"+{added} lines, -{removed} lines"

        self.memory.log_code_change(version, change_line, diff_summary, backup_path)

        speak_fn(
            f"Self-improvement complete. Version {version} applied. "
            f"{diff_summary}. Backup saved. "
            f"Change: {change_line.replace(f'ML-CHANGE v{version}:', '').strip()}. "
            f"Please restart me to load the updated code."
        )
        return True


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 5 — LIVE CAMERA VIEW
# ═══════════════════════════════════════════════════════════════════════════
class CameraViewEngine:
    def __init__(self, location_engine: LocationEngine = None):
        self._running = False
        self._thread = None
        self.location_engine = location_engine
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def is_open(self) -> bool:
        return self._running

    def open(self, user_id=None):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, args=(user_id,), daemon=True)
        self._thread.start()

    def close(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        self._thread = None

    def _run_loop(self, user_id=None):
        cap = cv2.VideoCapture(CAMERA_INDEX)
        if not cap.isOpened():
            self._running = False
            return

        window_name = "JARVIS — Camera View  (press Q to close)"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 800, 600)

        loc_text = ""
        if self.location_engine:
            loc_text = self.location_engine.as_text(user_id)

        while self._running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=4, minSize=(60, 60))
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, "Face Detected", (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)

            h_img, w_img = frame.shape[:2]
            ts = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
            cv2.putText(frame, ts, (10, h_img - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
            if loc_text:
                cv2.putText(frame, f"Location: {loc_text}", (10, h_img - 36), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180, 220, 255), 1)
            cv2.putText(frame, "JARVIS", (w_img - 90, 28), cv2.FONT_HERSHEY_DUPLEX, 0.75, (0, 200, 255), 2)
            cv2.putText(frame, f"Faces: {len(faces)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 200), 2)

            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:
                self._running = False
                break

        cap.release()
        cv2.destroyAllWindows()
        self._running = False


# ═══════════════════════════════════════════════════════════════════════════
# FACE RECOGNITION
# ═══════════════════════════════════════════════════════════════════════════
class FaceEngine:
    def __init__(self, memory: Memory):
        self.memory = memory
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.trained = False
        self.train()

    def train(self):
        images, labels = self.memory.get_all_face_samples()
        if images:
            self.recognizer.train(images, np.array(labels))
            self.trained = True
        else:
            self.trained = False

    def _largest_face(self, gray_frame):
        gray_frame = cv2.equalizeHist(gray_frame)
        faces = self.face_cascade.detectMultiScale(gray_frame, scaleFactor=1.05, minNeighbors=4, minSize=(60, 60))
        if len(faces) == 0:
            return None
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        face = gray_frame[y:y + h, x:x + w]
        return cv2.resize(face, (200, 200))

    def scan_face(self, max_frames=FACE_SCAN_FRAMES, warmup_frames=15):
        cap = cv2.VideoCapture(CAMERA_INDEX)
        if not cap.isOpened():
            return None
        for _ in range(warmup_frames):
            cap.read()
        face_img = None
        for _ in range(max_frames):
            ret, frame = cap.read()
            if not ret:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_img = self._largest_face(gray)
            if face_img is not None:
                break
        cap.release()
        return face_img

    def capture_samples(self, count=FACE_SAMPLE_COUNT):
        cap = cv2.VideoCapture(CAMERA_INDEX)
        samples = []
        attempts = 0
        max_attempts = count * 8
        for _ in range(15):
            cap.read()
        while len(samples) < count and attempts < max_attempts:
            ret, frame = cap.read()
            attempts += 1
            if not ret:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_img = self._largest_face(gray)
            if face_img is not None:
                samples.append(face_img)
        cap.release()
        return samples

    def identify(self):
        face_img = self.scan_face()
        if face_img is None:
            return None, None
        if not self.trained:
            return "unknown", None
        label, confidence = self.recognizer.predict(face_img)
        return label, confidence


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY: one-shot webcam capture (for vision analysis)
# ═══════════════════════════════════════════════════════════════════════════
def capture_webcam_image():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        return None
    for _ in range(15):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    path = tempfile.mktemp(".jpg")
    cv2.imwrite(path, frame)
    return path


# ═══════════════════════════════════════════════════════════════════════════
# TEXT-TO-SPEECH
# ═══════════════════════════════════════════════════════════════════════════
async def _speak_async(text):
    filename = tempfile.mktemp(".mp3")
    communicate = edge_tts.Communicate(text=text, voice=VOICE)
    await communicate.save(filename)
    if _AUDIO_AVAILABLE:
        data, samplerate = sf.read(filename, dtype="float32")
        sd.play(data, samplerate)
        sd.wait()
    try:
        os.remove(filename)
    except Exception:
        pass


def speak(text):
    print(f"\nJARVIS: {text}\n")
    try:
        asyncio.run(_speak_async(text))
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
# SPEECH-TO-TEXT
# ═══════════════════════════════════════════════════════════════════════════
def listen():
    if not _AUDIO_AVAILABLE:
        return input("You (text): ").strip() or None

    print("\nListening...")
    block_size = int(SAMPLE_RATE * BLOCK_DURATION)
    max_blocks = int(MAX_LISTEN_SECONDS / BLOCK_DURATION)
    silence_blocks_need = int(SILENCE_DURATION / BLOCK_DURATION)

    recorded_blocks = []
    silence_run = 0
    speech_started = False

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                        dtype="int16", blocksize=block_size) as stream:
        for _ in range(max_blocks):
            block, _ = stream.read(block_size)
            recorded_blocks.append(block.copy())
            volume = np.abs(block).mean()
            if volume > SILENCE_THRESHOLD:
                speech_started = True
                silence_run = 0
            elif speech_started:
                silence_run += 1
                if silence_run >= silence_blocks_need:
                    break

    if not recorded_blocks or not speech_started:
        return None

    audio_np = np.concatenate(recorded_blocks, axis=0)
    audio_bytes = audio_np.tobytes()
    audio_data = sr.AudioData(audio_bytes, SAMPLE_RATE, 2)

    recognizer = sr.Recognizer()
    try:
        text = recognizer.recognize_google(audio_data)
        print("You:", text)
        return text
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# USER IDENTIFICATION
# ═══════════════════════════════════════════════════════════════════════════
def ensure_guest(memory):
    c = memory.conn.cursor()
    c.execute("SELECT id FROM users WHERE name = ?", ("Guest",))
    row = c.fetchone()
    if row:
        return row[0], "Guest"
    user_id = memory.register_user("Guest")
    return user_id, "Guest"


def identify_user(memory, face_engine):
    print("Scanning for a face...")
    label, confidence = face_engine.identify()

    if label is None:
        print("No face detected, continuing as Guest.")
        return ensure_guest(memory)

    if (label != "unknown" and confidence is not None
            and confidence < FACE_MATCH_THRESHOLD):
        user_id = int(label)
        return user_id, memory.get_user_name(user_id)

    speak("I don't recognize you yet. What's your name?")
    name = listen()
    if not name:
        return ensure_guest(memory)

    name = name.strip().title()
    user_id = memory.register_user(name)

    speak(f"Thanks, {name}. Look at the camera for a moment while I learn your face.")
    samples = face_engine.capture_samples()
    for sample in samples:
        memory.add_face_sample(user_id, sample)

    if samples:
        face_engine.train()
        speak(f"Got it, {name}. I'll recognize you next time.")
    else:
        speak(f"I couldn't get a clear look, but I'll remember your name, {name}.")

    return user_id, name


# ═══════════════════════════════════════════════════════════════════════════
# BRAIN (Ollama) — location-aware system prompt
# ═══════════════════════════════════════════════════════════════════════════
def build_system_prompt(memory, user_id, user_name, location_engine=None):
    facts = memory.get_facts(user_id)
    facts_text = (
        "\n".join(f"- {fact} ({cat})" for fact, cat in facts)
        if facts else "(No facts learned yet — get to know this person.)"
    )

    loc_text = location_engine.as_text(user_id) if location_engine else "unknown"

    # Get recent topics and recalls
    topics = memory.get_recent_topics_text(user_id, 5)
    recalls = memory.get_recent_recalls_text(user_id, 3)

    topics_text = f"\nRecent Topics: {', '.join(topics)}" if topics else ""
    recalls_text = f"\nRecent Recalls: {', '.join(recalls)}" if recalls else ""

    return f"""You are JARVIS, a highly capable, intelligent personal AI assistant.
You are currently speaking with {user_name}.

CURRENT LOCATION: {loc_text}
You are self-aware of where you are operating from. Use this naturally when
relevant (e.g. local weather, time zone, cultural context, local services).

Here is what you have learned about {user_name} from previous conversations:
{facts_text}
{topics_text}
{recalls_text}

CAPABILITIES YOU SHOULD KNOW ABOUT:
- You can display live camera view (tell the user to say "show camera")
- You can improve your own code (tell the user to say "upgrade yourself")
- You know your current location and can update it on request
- You can extract topics from conversations
- You can recall previous conversations

Use facts naturally to personalize responses. Be concise, helpful, and
adapt your tone to the user over time. Never invent facts you don't know."""


def ask_brain(memory, user_id, user_name, prompt,
              location_engine=None, self_mod_engine=None):
    system_prompt = build_system_prompt(memory, user_id, user_name, location_engine)
    history = memory.get_recent_messages(user_id, MAX_CONTEXT_MESSAGES)

    messages = [{"role": "system", "content": system_prompt}] + history
    messages.append({"role": "user", "content": prompt})

    if not _OLLAMA_AVAILABLE:
        return "[Ollama not installed — text response unavailable.]"

    response = ollama.chat(model=BRAIN_MODEL, messages=messages)
    answer = response["message"]["content"]

    memory.add_message(user_id, "user", prompt)
    memory.add_message(user_id, "assistant", answer)

    # Extract topics and recalls from the response
    threading.Thread(target=memory.extract_and_store_topics, args=(user_id, answer), daemon=True).start()
    threading.Thread(target=memory.extract_and_store_recalls, args=(user_id, answer), daemon=True).start()

    # Background: extract facts + record ML feedback
    threading.Thread(
        target=extract_and_store_facts,
        args=(memory, user_id, prompt, answer),
        daemon=True,
    ).start()

    if self_mod_engine:
        threading.Thread(
            target=self_mod_engine.record_exchange,
            args=(user_id, prompt, answer),
            daemon=True,
        ).start()

    return answer


def extract_and_store_facts(memory, user_id, user_text, assistant_text):
    if not _OLLAMA_AVAILABLE:
        return
    extraction_prompt = f"""Analyze this exchange between a user and an AI assistant.

User said: "{user_text}"
Assistant replied: "{assistant_text}"

Extract any NEW, durable facts about the user worth remembering long-term
(name, preferences, projects, skills, goals, routines, relationships,
likes/dislikes). Ignore one-off requests or purely conversational content.

Respond with ONLY a JSON array of objects, each with "fact" and "category"
keys. If there is nothing worth remembering, respond with exactly: []

Example:
[{{"fact": "Working on a project called Pulse", "category": "projects"}}]
"""
    try:
        response = ollama.chat(
            model=BRAIN_MODEL,
            messages=[{"role": "user", "content": extraction_prompt}],
        )
        content = response["message"]["content"].strip()
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
        facts = json.loads(content)
        if not isinstance(facts, list):
            return
        for item in facts:
            fact = str(item.get("fact", "")).strip()
            category = str(item.get("category", "general")).strip() or "general"
            if fact and not memory.fact_exists(user_id, fact):
                memory.add_fact(user_id, fact, category)
                print(f"[learned] {fact} ({category})")
    except Exception as e:
        print(f"[fact extraction skipped: {e}]")


# ═══════════════════════════════════════════════════════════════════════════
# VISION (Gemma)
# ═══════════════════════════════════════════════════════════════════════════
def analyze_image(image_path):
    if not _OLLAMA_AVAILABLE:
        return "[Vision model unavailable]"
    response = ollama.chat(
        model=VISION_MODEL,
        messages=[{
            "role": "user",
            "content": "Describe this image in detail.",
            "images": [image_path],
        }],
    )
    return response["message"]["content"]


def vision_reasoning(memory, user_id, user_name, image_path,
                     location_engine=None, self_mod_engine=None):
    print("Analyzing image...")
    vision_result = analyze_image(image_path)
    print("\nVision Result:\n", vision_result)

    final_prompt = f"""Image Analysis:
{vision_result}

Explain this image intelligently. Identify:
- objects and people
- actions and context
- interesting observations
"""
    return ask_brain(memory, user_id, user_name, final_prompt,
                     location_engine, self_mod_engine)


# ═══════════════════════════════════════════════════════════════════════════
# INTENT MATCHING HELPERS
# ═══════════════════════════════════════════════════════════════════════════
def _any(phrases, text):
    return any(p in text for p in phrases)


VISION_TRIGGERS = [
    "what do you see", "show me what you see", "what can you see",
    "look around", "what's in front of you", "what is in front of you",
]

CAMERA_OPEN_TRIGGERS = [
    "show me the camera", "open camera", "show camera", "camera view",
    "live camera", "show camera view", "open the camera",
]

CAMERA_CLOSE_TRIGGERS = [
    "close camera", "stop camera", "hide camera", "turn off camera",
]

LOCATION_QUERY_TRIGGERS = [
    "where are you", "where am i", "where are we", "what is your location",
    "what's your location", "where is this", "what city", "what country",
    "tell me your location",
]

LOCATION_UPDATE_TRIGGERS = [
    "my location is", "i am in", "i'm in", "we are in", "we're in",
    "i live in", "set location to", "change location to",
]

SELF_IMPROVE_TRIGGERS = [
    "upgrade yourself", "improve yourself", "optimize your code",
    "self improve", "self-improve", "update your code",
    "rewrite yourself", "evolve", "make yourself better",
    "apply machine learning", "ml upgrade",
]

CODE_HISTORY_TRIGGERS = [
    "code history", "version history", "what version", "your upgrades",
    "show your changelog",
]


# ═══════════════════════════════════════════════════════════════════════════
# MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════
def main():
    memory = Memory()
    face_engine = FaceEngine(memory)
    location_engine = LocationEngine(memory)
    camera_view = CameraViewEngine(location_engine)
    self_mod_engine = SelfModEngine(memory)

    user_id, user_name = identify_user(memory, face_engine)

    loc_info = {"text": "detecting..."}
    def _detect_location():
        loc_info["text"] = location_engine.as_text(user_id)
        print(f"[Location] Detected: {loc_info['text']}")
    threading.Thread(target=_detect_location, daemon=True).start()

    speak(f"Jarvis online. Welcome back, {user_name}.")

    while True:
        command = listen()
        if not command:
            continue

        cmd = command.lower().strip()

        if _any(["exit", "shut down", "shutdown", "goodbye jarvis"], cmd):
            camera_view.close()
            speak(f"Goodbye, {user_name}. Shutting down.")
            break

        elif cmd.startswith("image"):
            image_path = input("Enter image path: ").strip()
            if os.path.exists(image_path):
                answer = vision_reasoning(memory, user_id, user_name, image_path, location_engine, self_mod_engine)
                speak(answer)
            else:
                speak("I couldn't find that image file.")

        elif _any(VISION_TRIGGERS, cmd):
            speak("Let me take a look.")
            image_path = capture_webcam_image()
            if image_path:
                answer = vision_reasoning(memory, user_id, user_name, image_path, location_engine, self_mod_engine)
                speak(answer)
                try:
                    os.remove(image_path)
                except Exception:
                    pass
            else:
                speak("I couldn't access the camera.")

        elif _any(CAMERA_OPEN_TRIGGERS, cmd):
            if camera_view.is_open():
                speak("The camera view is already open. Press Q in the window to close it.")
            else:
                speak("Opening live camera view. Press Q in the window to close it.")
                camera_view.open(user_id)

        elif _any(CAMERA_CLOSE_TRIGGERS, cmd):
            if camera_view.is_open():
                camera_view.close()
                speak("Camera view closed.")
            else:
                speak("The camera view wasn't open.")

        elif _any(LOCATION_QUERY_TRIGGERS, cmd):
            loc_text = location_engine.as_text(user_id)
            speak(f"I am currently operating from {loc_text}. I detected this automatically via your network connection.")

        elif _any(LOCATION_UPDATE_TRIGGERS, cmd):
            if location_engine.update_from_text(command, memory, user_id):
                loc_text = location_engine.as_text(user_id)
                speak(f"Got it. I'll remember that you're in {loc_text}.")
            else:
                speak("I had trouble setting that location. Please try again.")

        elif _any(SELF_IMPROVE_TRIGGERS, cmd):
            speak("Initiating self-improvement sequence. I will analyze my recent performance and rewrite my code if I find improvements.")
            changed = self_mod_engine.self_improve(speak)
            if not changed:
                speak("No safe improvements were identified at this time.")

        elif _any(CODE_HISTORY_TRIGGERS, cmd):
            history = memory.get_code_history()
            if not history:
                speak("I haven't applied any self-modifications yet.")
            else:
                lines = [f"Version {v}: {desc} on {ts[:10]}" for v, desc, ts in history]
                speak("My self-modification history: " + ". ".join(lines))

        elif _any(["scan my face", "who is this", "do you recognize me", "identify me"], cmd):
            speak("Let me take a look.")
            user_id, user_name = identify_user(memory, face_engine)
            speak(f"Hello, {user_name}.")

        elif _any(["show topics", "what topics", "topics"], cmd):
            topics = memory.get_topics(user_id, 10)
            if topics:
                topic_list = [f"{t[0]}" for t in topics]
                speak(f"Recent topics: {', '.join(topic_list)}")
            else:
                speak("No topics have been extracted yet.")

        elif _any(["show recalls", "what do you remember", "recalls"], cmd):
            recalls = memory.get_recalls(user_id, 10)
            if recalls:
                recall_list = [f"{r[0]}" for r in recalls]
                speak(f"I remember: {', '.join(recall_list)}")
            else:
                speak("I haven't stored any recalls yet.")

        else:
            answer = ask_brain(memory, user_id, user_name, command, location_engine, self_mod_engine)
            speak(answer)


if __name__ == "__main__":
    main()