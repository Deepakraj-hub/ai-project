"""
LILY — Streaming Voice AI Assistant
====================================

A conversational AI with:
- Streaming VAD, STT, LLM, and TTS
- Natural interruption (barge-in)
- Memory and learning
- Autonomous tool execution via Hermes agent
- Location awareness

Architecture:
    Microphone → VAD → STT → Intent → {LLM | Hermes} → Sentence Builder → TTS → Speaker

All components communicate via EventBus for loose coupling.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

# Add lily to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lily.audio_manager import AudioManager
from lily.conversation_manager import ConversationManager, ConversationState
from lily.event_bus import EventBus, EventTypes
from lily.intent_manager import IntentManager
from lily.llm_manager import LLMManager
from lily.sentence_builder import SentenceBuilder
from lily.stt_manager import STTManager
from lily.tts_manager import TTSManager
from lily.vad_manager import VADManager

# Import existing Lily modules
from lily.brain.agent import AutonomousAgent
from lily.memory.memory import AgentMemory

# Import old jarvis modules for compatibility
import sqlite3
from datetime import datetime


class SimpleMemory:
    """Simple memory wrapper for conversation history and facts."""
    
    def __init__(self, db_path: str = "jarvis_memory.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._init_tables()
    
    def _init_tables(self):
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                fact TEXT NOT NULL,
                category TEXT,
                timestamp TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                context TEXT,
                timestamp TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS recalls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                recall TEXT NOT NULL,
                context TEXT,
                timestamp TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS location_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                city TEXT,
                region TEXT,
                country TEXT,
                latitude REAL,
                longitude REAL,
                source TEXT,
                timestamp TEXT
            );
        """)
        self.conn.commit()
    
    def add_message(self, user_id: int, role: str, content: str):
        with self.lock:
            c = self.conn.cursor()
            c.execute(
                "INSERT INTO conversations (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, role, content, datetime.now().isoformat())
            )
            self.conn.commit()
    
    def get_facts(self, user_id: int):
        c = self.conn.cursor()
        c.execute("SELECT fact, category FROM facts WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,))
        return c.fetchall()
    
    def add_fact(self, user_id: int, fact: str, category: str = "general"):
        with self.lock:
            c = self.conn.cursor()
            c.execute(
                "INSERT INTO facts (user_id, fact, category, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, fact, category, datetime.now().isoformat())
            )
            self.conn.commit()
    
    def fact_exists(self, user_id: int, fact: str) -> bool:
        c = self.conn.cursor()
        c.execute("SELECT fact FROM facts WHERE user_id = ?", (user_id,))
        existing = [row[0].lower().strip() for row in c.fetchall()]
        return fact.lower().strip() in existing
    
    def get_recent_topics_text(self, user_id: int, limit: int = 5) -> list[str]:
        c = self.conn.cursor()
        c.execute("SELECT topic FROM topics WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        return [row[0] for row in c.fetchall()]
    
    def get_recent_recalls_text(self, user_id: int, limit: int = 3) -> list[str]:
        c = self.conn.cursor()
        c.execute("SELECT recall FROM recalls WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        return [row[0] for row in c.fetchall()]
    
    def ensure_guest_user(self) -> tuple[int, str]:
        """Ensure Guest user exists and return (user_id, name)."""
        c = self.conn.cursor()
        c.execute("SELECT id FROM users WHERE name = ?", ("Guest",))
        row = c.fetchone()
        if row:
            return row[0], "Guest"
        
        with self.lock:
            c.execute("INSERT INTO users (name, created_at) VALUES (?, ?)",
                     ("Guest", datetime.now().isoformat()))
            self.conn.commit()
            return c.lastrowid, "Guest"
    
    def save_location(self, user_id: int, city: str, region: str, country: str,
                     lat: float, lon: float, source: str = "ip"):
        with self.lock:
            c = self.conn.cursor()
            c.execute("""INSERT INTO location_history
                         (user_id, city, region, country, latitude, longitude, source, timestamp)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                     (user_id, city, region, country, lat, lon, source, datetime.now().isoformat()))
            self.conn.commit()
    
    def get_last_location(self, user_id: int = None):
        c = self.conn.cursor()
        if user_id:
            c.execute("""SELECT city, region, country, latitude, longitude, source, timestamp
                        FROM location_history WHERE user_id = ? ORDER BY id DESC LIMIT 1""", (user_id,))
        else:
            c.execute("""SELECT city, region, country, latitude, longitude, source, timestamp
                        FROM location_history ORDER BY id DESC LIMIT 1""")
        return c.fetchone()


class LocationEngine:
    """Simple location detection via IP geolocation."""
    
    PROVIDERS = [
        "http://ip-api.com/json/",
        "https://ipapi.co/json/",
    ]
    
    def __init__(self, memory: SimpleMemory):
        self.memory = memory
        self._cache: dict | None = None
    
    def detect(self, user_id: int = None, force: bool = False) -> dict:
        if self._cache and not force:
            return self._cache
        
        # Check DB cache first
        row = self.memory.get_last_location(user_id)
        if row and not force:
            city, region, country, lat, lon, source, ts = row
            result = {
                "city": city, "region": region, "country": country,
                "latitude": lat, "longitude": lon,
                "source": f"{source} (cached)", "timestamp": ts
            }
            self._cache = result
            return result
        
        # Fetch from network
        return self._fetch_network(user_id)
    
    def _fetch_network(self, user_id: int = None) -> dict:
        import requests
        
        for url in self.PROVIDERS:
            try:
                r = requests.get(url, timeout=3)
                if r.status_code != 200:
                    continue
                data = r.json()
                
                city = data.get("city") or data.get("city_name", "Unknown")
                region = data.get("regionName") or data.get("region") or ""
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
        
        return {
            "city": "Unknown", "region": "", "country": "Unknown",
            "latitude": 0.0, "longitude": 0.0,
            "source": "unavailable", "timestamp": datetime.now().isoformat()
        }
    
    def as_text(self, user_id: int = None) -> str:
        loc = self.detect(user_id)
        parts = [p for p in [loc["city"], loc["region"], loc["country"]] if p]
        return ", ".join(parts) if parts else "unknown location"


class LilyCore:
    """Main Lily application coordinator."""
    
    def __init__(self):
        print("╔═══════════════════════════════════════╗")
        print("║   LILY — Streaming Voice Assistant    ║")
        print("╚═══════════════════════════════════════╝\n")
        
        # Core components
        self.event_bus = EventBus()
        self.memory = SimpleMemory()
        self.location_engine = LocationEngine(self.memory)
        
        # Get or create user
        self.user_id, self.user_name = self.memory.ensure_guest_user()
        
        # Detect location in background
        threading.Thread(target=self._detect_location, daemon=True).start()
        
        # Audio pipeline
        self.audio_manager = AudioManager(self.event_bus)
        self.vad_manager = VADManager(self.event_bus)
        self.stt_manager = STTManager(self.event_bus, model_size="base")
        
        # Intent and LLM
        self.intent_manager = IntentManager(self.event_bus)
        self.llm_manager = LLMManager(self.event_bus, model="gemma4:cloud")
        
        # TTS pipeline
        self.sentence_builder = SentenceBuilder(self.event_bus)
        self.tts_manager = TTSManager(self.event_bus)
        
        # Hermes agent (optional)
        self.hermes_agent = None
        try:
            agent_memory = AgentMemory(project_root / "jarvis_memory.db")
            self.hermes_agent = AutonomousAgent(
                project_root=project_root,
                memory=agent_memory,
            )
            print("[Lily] Hermes agent loaded")
        except Exception as e:
            print(f"[Lily] Hermes agent not available: {e}")
        
        # Conversation orchestrator
        self.conversation = ConversationManager(
            event_bus=self.event_bus,
            stt_manager=self.stt_manager,
            intent_manager=self.intent_manager,
            llm_manager=self.llm_manager,
            tts_manager=self.tts_manager,
            sentence_builder=self.sentence_builder,
            memory=self.memory,
            location_engine=self.location_engine,
            hermes_agent=self.hermes_agent,
        )
        
        # Subscribe to state changes for UI feedback
        self.event_bus.subscribe(EventTypes.STATE_CHANGED, self._on_state_changed)
        self.event_bus.subscribe(EventTypes.ERROR, self._on_error)
    
    def _detect_location(self):
        """Detect location in background."""
        loc_text = self.location_engine.as_text(self.user_id)
        print(f"[Location] {loc_text}\n")
    
    def _on_state_changed(self, event):
        """Show state changes in UI."""
        new_state = event.payload.get("new_state", "")
        indicators = {
            "idle": "💤",
            "listening": "🎤",
            "thinking": "🧠",
            "speaking": "🔊",
            "tool_executing": "🔧",
            "interrupted": "⚠️",
        }
        icon = indicators.get(new_state, "")
        print(f"\r{icon} {new_state.upper():<20}", end="", flush=True)
    
    def _on_error(self, event):
        """Log errors."""
        source = event.payload.get("source", "unknown")
        error = event.payload.get("error", "unknown error")
        print(f"\n[ERROR] {source}: {error}")
    
    def start(self):
        """Start all managers and begin listening."""
        print(f"[Lily] Starting for {self.user_name}...")
        
        # Start audio pipeline
        self.audio_manager.start()
        
        # Start STT
        self.stt_manager.start()
        
        # Start TTS
        self.tts_manager.start()
        
        # Start conversation manager
        self.conversation.start(self.user_id, self.user_name)
        
        print(f"[Lily] Online. Listening...\n")
        print("Say 'exit' or 'shutdown' to stop.\n")
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Lily] Shutting down...")
            self.stop()
    
    def stop(self):
        """Stop all managers."""
        self.conversation.close()
        self.tts_manager.close()
        self.stt_manager.close()
        self.vad_manager.close()
        self.audio_manager.stop()
        print("[Lily] Goodbye!")


def main():
    """Main entry point."""
    lily = LilyCore()
    lily.start()


if __name__ == "__main__":
    main()
