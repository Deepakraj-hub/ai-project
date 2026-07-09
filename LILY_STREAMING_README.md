# LILY — Streaming Voice AI Assistant

A fully conversational AI assistant with natural voice interaction, interruption support, autonomous tool execution, and memory.

## Architecture

```
                    LILY CORE
                ┌─────────────────┐
Mic ───────────▶│ Audio Manager   │◀──────────── Speaker
                └────────┬────────┘
                         │
                         ▼
                 Voice Activity Detection
                     (Silero VAD / RMS)
                         │
              speech detected?
                         │
             ┌───────────┴────────────┐
             │                        │
             ▼                        ▼
      User Speaking             User Silent
             │                        │
             ▼                        ▼
      Interrupt TTS            Continue speaking
             │
             ▼
      Streaming Whisper
             │
             ▼
      Partial Transcript
             │
             ▼
      Intent Classifier
             │
      ┌──────┴────────┐
      ▼               ▼
Conversation      Tool Request
      │               │
      ▼               ▼
 Gemma 4        Hermes Agent
      │               │
      └──────┬────────┘
             ▼
      Memory Manager
             │
             ▼
     Response Stream
             │
             ▼
 Streaming Sentence Builder
             │
             ▼
     Streaming Edge TTS
             │
             ▼
         Speaker
```

## Key Features

### 🎙️ **Natural Voice Interaction**
- **Streaming VAD**: Detects when you start/stop speaking in real-time
- **Barge-in Support**: Interrupt Lily mid-sentence naturally
- **Streaming STT**: Whisper transcribes as you speak
- **Streaming LLM**: Gemma generates responses token-by-token
- **Streaming TTS**: Edge TTS speaks sentences as they complete

### 🧠 **Intelligence**
- Memory of facts, topics, and conversation history
- Location awareness (automatic IP geolocation)
- Intent classification (conversation vs tool execution)
- Autonomous tool execution via Hermes agent
- Self-learning from conversations

### 🔧 **Modular Design**
Each component runs independently and communicates via EventBus:
- `audio_manager.py` — Microphone and speaker queues
- `vad_manager.py` — Voice activity detection
- `stt_manager.py` — Streaming speech-to-text
- `intent_manager.py` — Fast intent classification
- `llm_manager.py` — Streaming LLM (Gemma)
- `sentence_builder.py` — Collects tokens into sentences
- `tts_manager.py` — Interruptible text-to-speech
- `conversation_manager.py` — Orchestrates the flow
- `event_bus.py` — Pub/sub event system

## Installation

### 1. Install Python Dependencies

```bash
pip install -r lily_requirements.txt
```

### 2. Install Ollama

Ollama is required for the LLM (Gemma):

**Windows:**
```bash
# Download from: https://ollama.com/download
```

**Linux/Mac:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 3. Pull the Gemma Model

```bash
ollama pull gemma4:cloud
```

### 4. Install Whisper Model

The first time you run Lily, Whisper will automatically download the `base` model (~140MB).

## Usage

### Start Lily

```bash
python lily_main.py
```

### Conversation States

Lily operates in different states:

- **💤 IDLE**: Waiting for you to speak
- **🎤 LISTENING**: Recording your voice
- **🧠 THINKING**: Processing your request
- **🔊 SPEAKING**: Lily is responding
- **🔧 TOOL_EXECUTING**: Running a tool/action
- **⚠️ INTERRUPTED**: You interrupted Lily

### Example Interactions

**Simple Conversation:**
```
You: What's the weather like?
Lily: I don't have live weather data, but I'm in [your city]. 
      Would you like me to search for current conditions?
```

**Tool Execution:**
```
You: Open Chrome and go to YouTube
Lily: Let me handle that...
      [Opens Chrome and navigates to YouTube]
      Done.
```

**Interruption:**
```
Lily: Today the weather is sunny with a high of—
You: Wait!
Lily: [stops immediately] Yes?
```

**Memory:**
```
You: I'm working on a Python project
Lily: That sounds interesting! What's the project about?
You: [later] What am I working on?
Lily: You mentioned you're working on a Python project.
```

## Configuration

### Environment Variables

```bash
# Voice settings
export LILY_VOICE="en-US-AvaMultilingualNeural"
export LILY_VOICE_RATE="-6%"
export LILY_VOICE_PITCH="+3Hz"
export LILY_VOICE_VOLUME="+0%"

# Whisper model size (tiny, base, small, medium, large)
export LILY_WHISPER_MODEL="base"

# Ollama model
export LILY_LLM_MODEL="gemma4:cloud"
```

### VAD Tuning

In `lily/vad_manager.py`:
- `speech_threshold`: Lower = more sensitive (default: 300.0)
- `silence_timeout`: How long to wait before ending speech (default: 0.7s)
- `barge_in_threshold`: Volume needed to interrupt (default: 900.0)

### Conversation Tuning

In `lily/llm_manager.py`:
- `max_context_messages`: Conversation history length (default: 6)
- `temperature`: LLM creativity (default: 0.7)
- `num_predict`: Max tokens per response (default: 150)

## Thread Layout

Lily runs multiple concurrent threads:

```
Thread 1: Microphone capture (audio_manager)
Thread 2: VAD detection (vad_manager)
Thread 3: Whisper transcription (stt_manager)
Thread 4: Gemma streaming (llm_manager)
Thread 5: Hermes agent (when tools are used)
Thread 6: TTS synthesis (tts_manager)
Thread 7: Conversation orchestration (conversation_manager)
Thread 8: Background fact extraction
```

## Event Flow

### Listening → Responding Flow

```
1. AudioChunk → VAD → USER_STARTED_SPEAKING
2. User speaks → STT accumulates audio
3. USER_STOPPED_SPEAKING → TRANSCRIPT_READY
4. Intent classification → INTENT_CLASSIFIED
5. LLM_STARTED → LLM_TOKEN stream → LLM_FINISHED
6. Sentence Builder → LLM_SENTENCE
7. TTS_STARTED → Speech playback → TTS_STOPPED
8. STATE_CHANGED → IDLE
```

### Interruption Flow

```
1. TTS_STARTED (Lily speaking)
2. AudioChunk → VAD detects high volume
3. USER_STARTED_SPEAKING → TTS_INTERRUPTED
4. TTS stops immediately
5. STATE_CHANGED → LISTENING
```

## Project Structure

```
lily/
├── audio_manager.py          # Mic/speaker queues
├── vad_manager.py            # Voice activity detection
├── stt_manager.py            # Streaming Whisper STT
├── intent_manager.py         # Intent classification
├── llm_manager.py            # Streaming Gemma LLM
├── sentence_builder.py       # Token → sentence collector
├── tts_manager.py            # Interruptible TTS
├── conversation_manager.py   # Orchestrates flow
├── event_bus.py              # Event pub/sub system
├── voice.py                  # Voice configuration
│
├── brain/                    # Hermes autonomous agent
│   ├── agent.py
│   ├── executor.py
│   ├── planner.py
│   ├── reasoner.py
│   └── permissions.py
│
├── memory/                   # Long-term memory
│   ├── memory.py
│   ├── facts.py
│   └── history.py
│
├── tools/                    # Tool registry
│   ├── browser.py
│   ├── desktop.py
│   ├── filesystem.py
│   └── ...
│
└── config/
    └── settings.py

lily_main.py                  # Main entry point
lily_requirements.txt         # Python dependencies
```

## Troubleshooting

### No audio input/output

```bash
# Install audio backend
pip install sounddevice soundfile pyaudio
```

### Whisper not working

```bash
# Install Whisper
pip install openai-whisper

# Check CUDA availability (for GPU acceleration)
python -c "import torch; print(torch.cuda.is_available())"
```

### Ollama connection issues

```bash
# Check Ollama is running
ollama list

# Restart Ollama service
# Windows: Restart from system tray
# Linux: sudo systemctl restart ollama
```

### Voice not detected

Increase VAD sensitivity in `vad_manager.py`:
```python
speech_threshold=200.0  # Lower = more sensitive
```

### Lily interrupts too easily

Increase barge-in threshold in `vad_manager.py`:
```python
barge_in_threshold=1200.0  # Higher = harder to interrupt
```

## Performance Tips

### Faster Transcription
Use a smaller Whisper model:
```python
stt_manager = STTManager(event_bus, model_size="tiny")  # tiny, base, small
```

### Faster LLM Responses
Reduce max tokens:
```python
options={"num_predict": 80}  # Shorter responses
```

### Lower Latency TTS
Use faster voice models (though quality may vary):
```python
voice="en-US-JennyNeural"  # Experiment with different voices
```

## Future Enhancements

- [ ] **Silero VAD Integration**: More accurate voice detection
- [ ] **Faster Whisper**: Hardware-accelerated transcription
- [ ] **Kokoro TTS**: Local, streaming TTS alternative
- [ ] **Multiple Users**: Face recognition for user switching
- [ ] **Emotion Detection**: Adjust responses based on tone
- [ ] **Wake Word**: "Hey Lily" activation
- [ ] **Multi-language Support**: Real-time translation

## License

MIT License — See LICENSE file

## Credits

- **Whisper**: OpenAI
- **Gemma**: Google
- **Edge TTS**: Microsoft
- **Ollama**: Ollama team
- **Architecture**: Inspired by Hugging Face speech-to-speech pipeline

---

**Built with ❤️ by the Lily team**
