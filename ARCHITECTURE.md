# Lily Streaming Voice Assistant — Architecture

## Overview

Lily is built on a **modular, event-driven architecture** where independent managers communicate through a central EventBus. This design enables:

- **Real-time streaming** at every stage
- **Natural interruption** without blocking
- **Concurrent processing** across multiple threads
- **Loose coupling** for easy testing and extension

## High-Level Data Flow

```
┌─────────────┐
│     User    │
└──────┬──────┘
       │ speaks
       ▼
┌──────────────────────────────────────────────────────────┐
│                    AUDIO MANAGER                          │
│  • Captures microphone input continuously                │
│  • Publishes audio chunks to EventBus                    │
│  • Manages speaker output queue                          │
└──────────────────────┬───────────────────────────────────┘
                       │ AudioChunk events
                       ▼
┌──────────────────────────────────────────────────────────┐
│                     VAD MANAGER                           │
│  • Detects voice activity in real-time                   │
│  • Emits USER_STARTED_SPEAKING / USER_STOPPED_SPEAKING   │
│  • Detects barge-in during TTS playback                  │
└──────────────────────┬───────────────────────────────────┘
                       │ Voice activity events
                       ▼
┌──────────────────────────────────────────────────────────┐
│                     STT MANAGER                           │
│  • Accumulates audio when user is speaking               │
│  • Streams partial transcripts via Whisper               │
│  • Emits TRANSCRIPT_READY when user stops                │
└──────────────────────┬───────────────────────────────────┘
                       │ Transcript text
                       ▼
┌──────────────────────────────────────────────────────────┐
│                   INTENT MANAGER                          │
│  • Classifies user intent (conversation vs tool)         │
│  • Fast rule-based matching                              │
│  • Emits INTENT_CLASSIFIED                               │
└──────────────────────┬───────────────────────────────────┘
                       │ Intent decision
           ┌───────────┴────────────┐
           ▼                        ▼
  ┌─────────────────┐      ┌─────────────────┐
  │  LLM MANAGER    │      │  HERMES AGENT   │
  │  (Conversation) │      │  (Tool Exec)    │
  └────────┬────────┘      └────────┬────────┘
           │ Streams tokens         │ Executes tasks
           │ LLM_TOKEN events       │ TOOL_FINISHED event
           └───────────┬────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│                  SENTENCE BUILDER                         │
│  • Collects streaming tokens                             │
│  • Emits complete sentences (LLM_SENTENCE)               │
│  • Enables low-latency TTS start                         │
└──────────────────────┬───────────────────────────────────┘
                       │ Complete sentences
                       ▼
┌──────────────────────────────────────────────────────────┐
│                     TTS MANAGER                           │
│  • Queues sentences for synthesis                        │
│  • Generates speech with Edge TTS                        │
│  • Plays audio in chunks (interruptible)                 │
│  • Emits TTS_STARTED / TTS_STOPPED / TTS_INTERRUPTED     │
└──────────────────────┬───────────────────────────────────┘
                       │ Audio output
                       ▼
┌──────────────────────────────────────────────────────────┐
│                     SPEAKER                               │
│  • Plays synthesized speech                              │
└──────────────────────────────────────────────────────────┘
                       │
                       ▼
                  User hears Lily
```

## Component Details

### 1. Audio Manager (`audio_manager.py`)

**Responsibilities:**
- Runs microphone capture loop in dedicated thread
- Publishes `AudioChunk` events continuously
- Manages speaker output queue (not directly used yet)
- Handles interrupt events for barge-in

**Key Methods:**
- `start()` — Begin microphone capture
- `stop()` — Stop capture and cleanup
- `_mic_loop()` — Main capture thread

**Events Published:**
- `AUDIO_CHUNK` — Raw audio data

### 2. VAD Manager (`vad_manager.py`)

**Responsibilities:**
- Monitors audio volume in real-time
- Detects when user starts/stops speaking
- Detects barge-in (user speaks while Lily is talking)
- Uses RMS energy (fallback to Silero VAD if available)

**Configuration:**
- `speech_threshold` — Volume to detect speech (default: 300.0)
- `silence_timeout` — Time before declaring silence (default: 0.7s)
- `barge_in_threshold` — Volume to interrupt TTS (default: 900.0)

**Events Subscribed:**
- `AUDIO_CHUNK` — Process audio
- `TTS_STARTED` / `TTS_STOPPED` — Track Lily's speech

**Events Published:**
- `USER_STARTED_SPEAKING` — User began talking
- `USER_STOPPED_SPEAKING` — User finished talking
- `TTS_INTERRUPTED` — User interrupted Lily

### 3. STT Manager (`stt_manager.py`)

**Responsibilities:**
- Accumulates audio when user is speaking
- Runs Whisper transcription in background
- Emits partial transcripts during speech
- Provides final transcript when user stops

**Whisper Models:**
- `tiny` — Fastest, least accurate (~39M params)
- `base` — Good balance (~74M params) **[Default]**
- `small` — More accurate (~244M params)
- `medium` / `large` — Best quality, slower

**Events Subscribed:**
- `USER_STARTED_SPEAKING` — Clear buffer
- `USER_STOPPED_SPEAKING` — Trigger final transcription
- `AUDIO_CHUNK` — Accumulate audio

**Events Published:**
- `TRANSCRIPT_PARTIAL` — Streaming transcript
- `TRANSCRIPT_READY` — Final transcript

### 4. Intent Manager (`intent_manager.py`)

**Responsibilities:**
- Classify user intent from transcript
- Route to appropriate handler (LLM or Hermes)
- Fast rule-based matching (no LLM needed)

**Intent Types:**
- `CONVERSATION` — General chat, questions
- `TOOL` — Actions, commands, tasks

**Classification Rules:**
```python
TOOL triggers:
  - Starts with "agent", "task"
  - Contains action verbs: "open", "create", "send", etc.
  - Mentions tool objects: "chrome", "file", "email", etc.

CONVERSATION (default):
  - Everything else
```

**Events Published:**
- `INTENT_CLASSIFIED` — Intent decision

### 5. LLM Manager (`llm_manager.py`)

**Responsibilities:**
- Generate streaming responses via Ollama
- Manage conversation context and history
- Build system prompts with user context
- Emit tokens for sentence builder

**System Prompt Includes:**
- User name and personalization
- Current location
- Known facts about user
- Recent conversation topics
- Capabilities list

**Events Published:**
- `LLM_STARTED` — Generation begins
- `LLM_TOKEN` — Each token generated
- `LLM_FINISHED` — Generation complete

**Key Methods:**
- `generate_stream()` — Streaming response
- `generate_sync()` — Non-streaming (for quick queries)
- `build_system_prompt()` — Context-aware prompt

### 6. Sentence Builder (`sentence_builder.py`)

**Responsibilities:**
- Collect streaming tokens
- Detect sentence boundaries
- Emit complete sentences to TTS
- Reduce perceived latency

**Sentence Boundaries:**
- `.`, `!`, `?` followed by space
- `,` after 80+ characters (for flow)

**Why It Matters:**
Without sentence builder:
```
LLM: "Today" "the" "weather" "is" "sunny" ...
TTS: Waits for entire response (slow)
```

With sentence builder:
```
LLM: "Today the weather is sunny."
TTS: Starts speaking immediately ✓
```

**Events Subscribed:**
- `LLM_TOKEN` — Accumulate tokens

**Events Published:**
- `LLM_SENTENCE` — Complete sentence

### 7. TTS Manager (`tts_manager.py`)

**Responsibilities:**
- Queue sentences for speech synthesis
- Generate audio with Edge TTS
- Play audio in interruptible chunks
- Handle barge-in interruption

**Interruption Flow:**
1. TTS is speaking
2. User starts talking (VAD detects)
3. `TTS_INTERRUPTED` event
4. Stop current playback immediately
5. Clear sentence queue

**Events Subscribed:**
- `LLM_SENTENCE` — Queue for speaking
- `TTS_INTERRUPTED` — Stop immediately

**Events Published:**
- `TTS_STARTED` — Begin speaking
- `TTS_STOPPED` — Finished speaking

### 8. Conversation Manager (`conversation_manager.py`)

**Responsibilities:**
- Orchestrate the full conversation flow
- Manage conversation state machine
- Coordinate between all managers
- Handle tool execution via Hermes
- Manage conversation history and memory

**State Machine:**
```
     ┌──────┐
     │ IDLE │◄───────────────────┐
     └───┬──┘                    │
         │ user speaks           │
         ▼                       │
   ┌───────────┐                 │
   │ LISTENING │                 │
   └─────┬─────┘                 │
         │ user stops            │
         ▼                       │
   ┌──────────┐                  │
   │ THINKING │                  │
   └─────┬────┘                  │
         │ intent classified     │
     ┌───┴────┐                  │
     ▼        ▼                  │
┌─────────┐ ┌──────────────┐    │
│SPEAKING │ │TOOL_EXECUTING│    │
└────┬────┘ └──────┬───────┘    │
     │             │             │
     │ TTS done    │ tool done   │
     └─────────────┴─────────────┘
```

**Key Methods:**
- `_handle_conversation()` — Route to LLM
- `_handle_tool_request()` — Route to Hermes
- `_stream_llm_response()` — Background LLM streaming
- `_extract_facts()` — Learn from conversation

**Events Subscribed:**
- `USER_STARTED_SPEAKING` / `USER_STOPPED_SPEAKING`
- `TRANSCRIPT_READY`
- `TOOL_FINISHED`
- `TTS_INTERRUPTED`

**Events Published:**
- `STATE_CHANGED` — Conversation state transitions

### 9. Event Bus (`event_bus.py`)

**Responsibilities:**
- Central pub/sub communication hub
- Thread-safe event delivery
- Support wildcard subscriptions
- Enable loose coupling

**Event Types:**
```python
AUDIO_CHUNK              # Raw audio data
USER_STARTED_SPEAKING    # User began talking
USER_STOPPED_SPEAKING    # User finished
TRANSCRIPT_PARTIAL       # Streaming transcript
TRANSCRIPT_READY         # Final transcript
INTENT_CLASSIFIED        # Intent decision
TOOL_STARTED             # Tool execution began
TOOL_FINISHED            # Tool execution done
LLM_STARTED              # LLM generation began
LLM_TOKEN                # LLM token streamed
LLM_SENTENCE             # Complete sentence
LLM_FINISHED             # LLM generation done
TTS_STARTED              # TTS playback began
TTS_STOPPED              # TTS playback done
TTS_INTERRUPTED          # TTS interrupted
STATE_CHANGED            # Conversation state change
ERROR                    # Error occurred
```

**Usage:**
```python
# Subscribe
def handler(event):
    print(event.payload)

unsub = bus.subscribe(EventTypes.LLM_TOKEN, handler)

# Publish
bus.publish(EventTypes.LLM_TOKEN, {"token": "Hello"})

# Unsubscribe
unsub()
```

## Memory Architecture

```
┌──────────────────────────────────────┐
│         SimpleMemory (SQLite)        │
├──────────────────────────────────────┤
│  Tables:                             │
│    • users                           │
│    • conversations                   │
│    • facts (learned info)            │
│    • topics (conversation themes)    │
│    • recalls (references)            │
│    • location_history                │
└──────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│      Fact Extraction (LLM-based)     │
│  • Runs in background after reply   │
│  • Extracts long-term facts          │
│  • Categories: preferences,          │
│    projects, skills, goals, etc.     │
└──────────────────────────────────────┘
```

## Thread Layout

```
Thread 1: Main thread (coordinator)
Thread 2: Microphone capture (audio_manager)
Thread 3: Whisper transcription (stt_manager)
Thread 4: LLM streaming (llm_manager)
Thread 5: TTS synthesis (tts_manager)
Thread 6: Hermes agent execution (when tools used)
Thread 7: Background fact extraction (memory)
Thread 8: Location detection (on startup)
```

## Latency Optimization

### Traditional Pipeline (High Latency):
```
User speaks → Wait → Full transcript → Wait → 
Full LLM response → Wait → Full TTS → Speak

Total delay: 3-5 seconds
```

### Lily Pipeline (Low Latency):
```
User speaks → Partial transcript (0.5s) →
Stream tokens → First sentence (1.5s) →
Stream TTS → Start speaking (2.0s)

Total delay: 2 seconds
```

**Key Optimizations:**
1. **Streaming at every stage** — No waiting for complete processing
2. **Sentence-level TTS** — Start speaking before full response
3. **Parallel processing** — Multiple threads work concurrently
4. **VAD-triggered actions** — React immediately to voice activity
5. **Interruptible TTS** — User can barge in anytime

## Interruption Mechanism

```
┌─────────────────────────────────────┐
│  Lily is speaking...                │
│  "Today the weather is—"            │
└──────────────┬──────────────────────┘
               │
               ▼
   User starts speaking (VAD detects high volume)
               │
               ▼
┌─────────────────────────────────────┐
│  TTS_INTERRUPTED event published    │
└──────────────┬──────────────────────┘
               │
         ┌─────┴──────┐
         ▼            ▼
  ┌───────────┐  ┌──────────┐
  │ TTS stops │  │ Clear    │
  │ playback  │  │ sentence │
  │ instantly │  │ queue    │
  └───────────┘  └──────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  State → LISTENING                  │
│  Ready for new user input           │
└─────────────────────────────────────┘
```

## Extension Points

### Adding New Events
```python
# 1. Define in EventTypes
class EventTypes:
    NEW_EVENT = "NEW_EVENT"

# 2. Subscribe in your manager
unsub = bus.subscribe(EventTypes.NEW_EVENT, handler)

# 3. Publish from anywhere
bus.publish(EventTypes.NEW_EVENT, {"data": "value"})
```

### Adding New Managers
```python
class CustomManager:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._unsubs = [
            event_bus.subscribe(EventTypes.SOME_EVENT, self._handler),
        ]
    
    def _handler(self, event):
        # Process event
        self.event_bus.publish(EventTypes.RESULT_EVENT, {...})
    
    def close(self):
        for unsub in self._unsubs:
            unsub()
```

### Adding Tools to Hermes
```python
# See lily/tools/ for examples
from lily.tools.base import Tool

class MyTool(Tool):
    name = "my_tool"
    description = "What this tool does"
    
    def execute(self, context, **kwargs):
        # Implement tool logic
        return {"success": True, "data": "result"}
```

## Performance Characteristics

| Component      | Latency    | CPU Usage | Memory    |
|----------------|------------|-----------|-----------|
| Audio Capture  | <10ms      | Low       | Minimal   |
| VAD            | <50ms      | Very Low  | Minimal   |
| Whisper (base) | 200-500ms  | Medium    | ~1GB      |
| Gemma (cloud)  | 50-150ms/token | Medium | ~2GB   |
| Edge TTS       | 300-800ms  | Low       | ~100MB    |
| EventBus       | <1ms       | Very Low  | Minimal   |

**Total System:**
- Memory: ~4GB RAM
- CPU: 30-50% during active use
- Latency: ~2s from speech to response

## Design Principles

1. **Event-Driven**: All communication via EventBus
2. **Streaming**: Process data as it arrives
3. **Non-Blocking**: Independent threads, no waits
4. **Interruptible**: User can barge in anytime
5. **Modular**: Each manager is independent
6. **Testable**: Components can be tested in isolation
7. **Extensible**: Easy to add new managers and events

---

**This architecture enables Lily to feel like a natural conversation partner rather than a walkie-talkie.**
