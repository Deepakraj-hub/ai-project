# Lily Streaming Voice Assistant — Quick Start

Get Lily up and running in 5 minutes.

## Prerequisites

- Python 3.9 or higher
- Windows 10/11 with working microphone and speakers
- Internet connection (for initial setup)

## Step 1: Install Ollama

Ollama runs the Gemma language model locally.

1. Download Ollama for Windows:
   - Visit: https://ollama.com/download
   - Run the installer

2. Pull the Gemma model:
   ```cmd
   ollama pull gemma4:cloud
   ```

3. Verify installation:
   ```cmd
   ollama list
   ```
   You should see `gemma4:cloud` in the list.

## Step 2: Install Python Dependencies

```cmd
cd c:\Users\DSEPY18239\Documents\ai-project
pip install -r lily_requirements.txt
```

This installs:
- Whisper (speech-to-text)
- Edge TTS (text-to-speech)
- Audio libraries (sounddevice, soundfile)
- Ollama Python client
- Other dependencies

## Step 3: Test Components

Run the test suite to verify everything works:

```cmd
python test_lily_streaming.py
```

You should see output like:
```
============================================================
LILY STREAMING ARCHITECTURE — Component Tests
============================================================

────────────────────────────────────────────────────────────
Core Components
────────────────────────────────────────────────────────────
Testing EventBus...
✓ EventBus working

Testing Memory...
✓ Memory working
...
```

If any tests fail, check the error messages and install missing dependencies.

## Step 4: Start Lily

```cmd
python lily_main.py
```

You should see:
```
╔═══════════════════════════════════════╗
║   LILY — Streaming Voice Assistant    ║
╚═══════════════════════════════════════╝

[STT] Whisper model 'base' loaded
[Lily] Hermes agent loaded
[Location] New York, New York, United States

[Lily] Starting for Guest...
[Lily] Online. Listening...

Say 'exit' or 'shutdown' to stop.

💤 IDLE
```

## Step 5: Talk to Lily

Just start speaking! The status indicator will change:

- **💤 IDLE**: Lily is waiting
- **🎤 LISTENING**: Recording your voice
- **🧠 THINKING**: Processing your request
- **🔊 SPEAKING**: Lily is responding

### Try These Commands:

**Simple conversation:**
```
You: "What's your name?"
Lily: "I'm Lily, your AI assistant."
```

**Ask about location:**
```
You: "Where are you?"
Lily: "I'm currently operating from [your city], [your country]."
```

**Tool execution:**
```
You: "Open Chrome"
Lily: "Let me handle that... Done."
```

**Interrupt Lily:**
```
Lily: "Today the weather is sunny with a high of—"
You: "Wait!"
Lily: [stops] "Yes?"
```

## Step 6: Exit Lily

Say: **"exit"** or **"shutdown"**

Or press `Ctrl+C` in the terminal.

## Troubleshooting

### "Ollama not available"

Make sure Ollama is running:
```cmd
ollama list
```

If not running, restart it from the system tray icon.

### "Whisper model not found"

The first run downloads Whisper (~140MB). Wait for it to complete.

### No microphone input detected

Check Windows sound settings:
1. Right-click speaker icon → Sounds
2. Recording tab → Enable your microphone
3. Set as default device

### Audio playback issues

Try reinstalling audio libraries:
```cmd
pip uninstall sounddevice soundfile
pip install sounddevice soundfile
```

### "Can't connect to audio backend"

Install PyAudio:
```cmd
pip install pyaudio
```

If that fails, download a pre-built wheel from:
https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

### Lily doesn't understand me

Speak clearly and wait for the status to change to 🎤 LISTENING before speaking.

If VAD is too sensitive/insensitive, edit `lily/vad_manager.py`:
```python
speech_threshold=300.0  # Lower = more sensitive
```

## Configuration

### Change Voice

Edit `lily_main.py`:
```python
self.tts_manager = TTSManager(self.event_bus, voice="en-US-JennyNeural")
```

Available voices:
- `en-US-AvaMultilingualNeural` (default, friendly)
- `en-US-JennyNeural` (professional)
- `en-US-AriaNeural` (conversational)
- `en-GB-SoniaNeural` (British)

### Change LLM Model

Edit `lily_main.py`:
```python
self.llm_manager = LLMManager(self.event_bus, model="llama2")
```

First pull the model:
```cmd
ollama pull llama2
```

### Adjust Response Length

Edit `lily/llm_manager.py`:
```python
"num_predict": 150,  # Max tokens (shorter = faster)
```

### Faster Transcription

Use a smaller Whisper model in `lily_main.py`:
```python
self.stt_manager = STTManager(self.event_bus, model_size="tiny")
```

Options: `tiny`, `base`, `small`, `medium`, `large`

## Next Steps

- Read `LILY_STREAMING_README.md` for full documentation
- Explore `lily/` folder to understand the architecture
- Customize system prompts in `lily/llm_manager.py`
- Add custom tools in `lily/tools/`
- Enable face recognition (see original `jarvis.py`)

## Support

For issues or questions:
1. Check the test suite: `python test_lily_streaming.py`
2. Review error logs in terminal
3. Verify Ollama is running: `ollama list`
4. Check microphone permissions in Windows

---

**Enjoy talking to Lily!** 🎙️✨
