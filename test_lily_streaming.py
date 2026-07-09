"""
Test script for Lily streaming architecture.
Tests each component independently before running the full system.
"""

import sys
import time
from pathlib import Path

# Add lily to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_event_bus():
    """Test event bus pub/sub."""
    print("Testing EventBus...")
    from lily.event_bus import EventBus, EventTypes
    
    bus = EventBus()
    events_received = []
    
    def handler(event):
        events_received.append(event.type)
    
    unsub = bus.subscribe(EventTypes.LLM_TOKEN, handler)
    bus.publish(EventTypes.LLM_TOKEN, {"token": "test"})
    
    assert EventTypes.LLM_TOKEN in events_received, "Event not received"
    unsub()
    print("✓ EventBus working")


def test_vad():
    """Test VAD manager."""
    print("\nTesting VAD Manager...")
    from lily.event_bus import EventBus, EventTypes
    from lily.vad_manager import VADManager
    import numpy as np
    
    bus = EventBus()
    vad = VADManager(bus)
    
    speaking_events = []
    bus.subscribe(EventTypes.USER_STARTED_SPEAKING, lambda e: speaking_events.append("started"))
    bus.subscribe(EventTypes.USER_STOPPED_SPEAKING, lambda e: speaking_events.append("stopped"))
    
    # Simulate loud audio (speaking)
    from lily.audio_manager import AudioChunk
    loud_audio = np.ones((1600,), dtype=np.int16) * 5000
    chunk = AudioChunk(samples=loud_audio, sample_rate=16000, timestamp=time.monotonic())
    bus.publish(EventTypes.AUDIO_CHUNK, {"chunk": chunk})
    
    time.sleep(0.1)
    assert "started" in speaking_events, "VAD didn't detect speech"
    
    vad.close()
    print("✓ VAD Manager working")


def test_intent():
    """Test intent classification."""
    print("\nTesting Intent Manager...")
    from lily.intent_manager import IntentManager, IntentKinds
    
    intent_mgr = IntentManager()
    
    # Test conversational intent
    intent = intent_mgr.classify("What's the weather today?")
    assert intent.kind == IntentKinds.CONVERSATION, f"Expected conversation, got {intent.kind}"
    
    # Test tool intent
    intent = intent_mgr.classify("Open Chrome")
    assert intent.kind == IntentKinds.TOOL, f"Expected tool, got {intent.kind}"
    
    print("✓ Intent Manager working")


def test_sentence_builder():
    """Test sentence builder."""
    print("\nTesting Sentence Builder...")
    from lily.event_bus import EventBus, EventTypes
    from lily.sentence_builder import SentenceBuilder
    
    bus = EventBus()
    builder = SentenceBuilder(bus)
    builder.start()
    
    sentences = []
    bus.subscribe(EventTypes.LLM_SENTENCE, lambda e: sentences.append(e.payload["sentence"]))
    
    # Simulate streaming tokens
    tokens = ["Hello", " there", ".", " How", " are", " you", "?"]
    for token in tokens:
        bus.publish(EventTypes.LLM_TOKEN, {"token": token})
        time.sleep(0.01)
    
    bus.publish(EventTypes.LLM_FINISHED, {})
    time.sleep(0.1)
    
    assert len(sentences) > 0, "No sentences emitted"
    print(f"✓ Sentence Builder working (emitted {len(sentences)} sentences)")
    
    builder.close()


def test_llm():
    """Test LLM manager (requires Ollama)."""
    print("\nTesting LLM Manager...")
    from lily.event_bus import EventBus
    from lily.llm_manager import LLMManager
    
    bus = EventBus()
    llm = LLMManager(bus, model="gemma4:cloud")
    
    try:
        # Quick sync test
        response = llm.generate_sync(
            prompt="Say 'test passed' and nothing else",
            options={"num_predict": 10, "temperature": 0.1},
        )
        
        if "[Error" in response or not response:
            print("⚠ LLM Manager: Ollama might not be available")
            return
        
        print(f"✓ LLM Manager working (response: {response[:50]}...)")
        
    except Exception as e:
        print(f"⚠ LLM Manager: {e}")


def test_memory():
    """Test memory system."""
    print("\nTesting Memory...")
    from lily_main import SimpleMemory
    
    memory = SimpleMemory(":memory:")  # In-memory DB for testing
    user_id, user_name = memory.ensure_guest_user()
    
    assert user_id > 0, "Failed to create user"
    assert user_name == "Guest", f"Expected 'Guest', got {user_name}"
    
    # Test conversation
    memory.add_message(user_id, "user", "Hello")
    memory.add_message(user_id, "assistant", "Hi there")
    
    # Test facts
    memory.add_fact(user_id, "Likes Python", "preferences")
    facts = memory.get_facts(user_id)
    assert len(facts) > 0, "Failed to store fact"
    
    print("✓ Memory working")


def test_location():
    """Test location detection."""
    print("\nTesting Location Engine...")
    from lily_main import SimpleMemory, LocationEngine
    
    memory = SimpleMemory(":memory:")
    location = LocationEngine(memory)
    
    try:
        loc = location.detect()
        loc_text = location.as_text()
        
        if loc["city"] == "Unknown":
            print("⚠ Location: Network might not be available")
        else:
            print(f"✓ Location working (detected: {loc_text})")
    except Exception as e:
        print(f"⚠ Location: {e}")


def test_audio_backend():
    """Test audio I/O."""
    print("\nTesting Audio Backend...")
    
    try:
        import sounddevice as sd
        import soundfile as sf
        import numpy as np
        
        # Test recording
        duration = 0.5  # seconds
        samplerate = 16000
        print("  Recording test audio...")
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
        sd.wait()
        
        # Test playback
        print("  Playing test tone...")
        tone = (np.sin(2 * np.pi * 440 * np.arange(samplerate * 0.2) / samplerate) * 16000).astype(np.int16)
        sd.play(tone, samplerate)
        sd.wait()
        
        print("✓ Audio Backend working")
        
    except ImportError:
        print("⚠ Audio Backend: sounddevice/soundfile not installed")
    except Exception as e:
        print(f"⚠ Audio Backend: {e}")


def test_whisper():
    """Test Whisper installation."""
    print("\nTesting Whisper...")
    
    try:
        import whisper
        
        # Try to load model (will download if not present)
        print("  Loading Whisper base model...")
        model = whisper.load_model("base")
        
        print("✓ Whisper working")
        
    except ImportError:
        print("⚠ Whisper: not installed (pip install openai-whisper)")
    except Exception as e:
        print(f"⚠ Whisper: {e}")


def test_edge_tts():
    """Test Edge TTS."""
    print("\nTesting Edge TTS...")
    
    try:
        import edge_tts
        import asyncio
        import tempfile
        import os
        
        async def test_tts():
            temp_file = tempfile.mktemp(suffix=".mp3")
            communicate = edge_tts.Communicate(
                text="Test",
                voice="en-US-AvaMultilingualNeural",
            )
            await communicate.save(temp_file)
            
            if os.path.exists(temp_file):
                os.remove(temp_file)
                return True
            return False
        
        success = asyncio.run(test_tts())
        
        if success:
            print("✓ Edge TTS working")
        else:
            print("⚠ Edge TTS: Failed to generate speech")
            
    except ImportError:
        print("⚠ Edge TTS: not installed (pip install edge-tts)")
    except Exception as e:
        print(f"⚠ Edge TTS: {e}")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("LILY STREAMING ARCHITECTURE — Component Tests")
    print("=" * 60)
    
    tests = [
        ("Core", [
            test_event_bus,
            test_memory,
        ]),
        ("Voice Pipeline", [
            test_audio_backend,
            test_vad,
            test_whisper,
            test_edge_tts,
        ]),
        ("Intelligence", [
            test_intent,
            test_sentence_builder,
            test_llm,
        ]),
        ("External", [
            test_location,
        ]),
    ]
    
    for category, test_funcs in tests:
        print(f"\n{'─' * 60}")
        print(f"{category} Components")
        print('─' * 60)
        
        for test_func in test_funcs:
            try:
                test_func()
            except Exception as e:
                print(f"✗ {test_func.__name__}: {e}")
    
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)
    print("\nIf all tests passed, you can run:")
    print("  python lily_main.py")
    print("\nFor any missing dependencies:")
    print("  pip install -r lily_requirements.txt")


if __name__ == "__main__":
    run_all_tests()
