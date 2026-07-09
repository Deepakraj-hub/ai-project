# Lily Streaming Voice Assistant — Troubleshooting Guide

Common issues and their solutions.

---

## Installation Issues

### ❌ "pip install failed for pyaudio"

**Cause**: PyAudio requires compilation on Windows.

**Solution 1** — Use pre-built wheel:
```cmd
# Find your Python version
python --version

# Download matching wheel from:
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

# Install the .whl file
pip install PyAudio-0.2.11-cp311-cp311-win_amd64.whl
```

**Solution 2** — Alternative audio backend:
```cmd
pip install sounddevice soundfile
# Lily will use sounddevice instead
```

### ❌ "No module named 'whisper'"

**Cause**: Whisper not installed.

**Solution**:
```cmd
pip install openai-whisper
```

**If that fails**:
```cmd
pip install git+https://github.com/openai/whisper.git
```

### ❌ "edge-tts not found"

**Cause**: Missing TTS library.

**Solution**:
```cmd
pip install edge-tts
```

### ❌ "ollama not found"

**Cause**: Ollama Python package not installed.

**Solution**:
```cmd
pip install ollama
```

---

## Ollama Issues

### ❌ "Ollama not available"

**Diagnosis**:
```cmd
ollama list
```

If this fails, Ollama isn't running.

**Solution 1** — Start Ollama (Windows):
1. Check system tray for Ollama icon
2. If not there, run Ollama from Start menu
3. Wait for it to initialize (~10 seconds)

**Solution 2** — Reinstall:
1. Download from https://ollama.com/download
2. Run installer
3. Restart computer

### ❌ "Model 'gemma4:cloud' not found"

**Cause**: Model not pulled.

**Solution**:
```cmd
ollama pull gemma4:cloud
```

**If this fails**, try alternative models:
```cmd
ollama pull gemma2:latest
ollama pull llama2:latest
```

Then edit `lily_main.py`:
```python
self.llm_manager = LLMManager(self.event_bus, model="gemma2:latest")
```

### ❌ "Connection refused to localhost:11434"

**Cause**: Ollama API not accessible.

**Solution**:
```cmd
# Check if Ollama is running
netstat -an | findstr "11434"

# If nothing appears, restart Ollama
```

---

## Audio Issues

### ❌ "No microphone detected"

**Diagnosis**:
```python
import sounddevice as sd
print(sd.query_devices())
```

**Solution 1** — Check Windows settings:
1. Right-click speaker icon → Sounds
2. Recording tab
3. Enable your microphone
4. Set as default device
5. Test by speaking

**Solution 2** — Check device index:
Edit `lily/audio_manager.py`:
```python
# Try different indices
with sd.InputStream(device=0, ...):  # Try 0, 1, 2, etc.
```

### ❌ "Audio playback not working"

**Diagnosis**:
```python
import sounddevice as sd
import numpy as np

# Play test tone
tone = (np.sin(2*np.pi*440*np.arange(16000*0.5)/16000)*16000).astype(np.int16)
sd.play(tone, 16000)
sd.wait()
```

**If you hear nothing**:
1. Check Windows volume mixer
2. Check speaker is connected
3. Try different audio device:
   ```python
   sd.play(tone, 16000, device=1)  # Try different indices
   ```

### ❌ "Can't import sounddevice"

**Cause**: Missing audio backend.

**Solution**:
```cmd
pip uninstall sounddevice soundfile
pip install sounddevice soundfile
```

**If still fails**, install PortAudio:
```cmd
# Windows with chocolatey
choco install portaudio

# Or download from:
# http://www.portaudio.com/download.html
```

---

## Voice Activity Detection Issues

### ❌ "Lily doesn't detect my voice"

**Cause**: Threshold too high.

**Solution**: Lower sensitivity in `lily/vad_manager.py`:
```python
VADManager(
    event_bus,
    speech_threshold=200.0,  # Lower = more sensitive (default: 300.0)
)
```

### ❌ "Lily thinks I'm speaking when I'm not"

**Cause**: Threshold too low or background noise.

**Solution 1** — Raise threshold:
```python
VADManager(
    event_bus,
    speech_threshold=500.0,  # Higher = less sensitive
)
```

**Solution 2** — Reduce background noise:
- Close windows
- Turn off fans
- Move microphone away from computer fans

### ❌ "Lily cuts me off mid-sentence"

**Cause**: Silence timeout too short.

**Solution**: Increase timeout in `lily/vad_manager.py`:
```python
VADManager(
    event_bus,
    silence_timeout=1.5,  # Wait longer before ending (default: 0.7s)
)
```

---

## Transcription Issues

### ❌ "Whisper model downloading very slow"

**Cause**: First run downloads model (~140MB).

**Solution**: Wait for download to complete. Check progress:
```python
import whisper
model = whisper.load_model("base")  # Shows download progress
```

**Speed up with smaller model**:
Edit `lily_main.py`:
```python
self.stt_manager = STTManager(self.event_bus, model_size="tiny")  # 39MB
```

### ❌ "Transcription is inaccurate"

**Solution 1** — Use larger model:
```python
self.stt_manager = STTManager(self.event_bus, model_size="small")
```

**Solution 2** — Speak more clearly:
- Speak at moderate pace
- Enunciate words
- Reduce background noise

**Solution 3** — Enable GPU acceleration:
```cmd
# Install CUDA-enabled PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### ❌ "Transcription is too slow"

**Solution**: Use smaller model:
```python
self.stt_manager = STTManager(self.event_bus, model_size="tiny")
```

---

## Response Generation Issues

### ❌ "LLM responses are too slow"

**Solution 1** — Reduce max tokens:
Edit `lily/llm_manager.py`:
```python
default_options = {
    "num_predict": 80,  # Shorter responses (default: 150)
}
```

**Solution 2** — Use faster model:
```cmd
ollama pull tinyllama
```
```python
self.llm_manager = LLMManager(self.event_bus, model="tinyllama")
```

**Solution 3** — Reduce context:
```python
self.llm_manager = LLMManager(
    self.event_bus,
    max_context_messages=3,  # Less history (default: 6)
)
```

### ❌ "LLM responses are too verbose"

**Solution**: Update system prompt in `lily/llm_manager.py`:
```python
PERSONALITY & STYLE:
- Maximum 1 sentence, 20 words
- Ultra-concise, no explanations
```

### ❌ "LLM hallucinates or gives wrong info"

**Solution 1** — Lower temperature:
```python
options={"temperature": 0.3}  # Less creative (default: 0.7)
```

**Solution 2** — Add constraints to system prompt:
```python
RULES:
- If you don't know, say "I don't know"
- Never invent facts
- Cite sources when possible
```

---

## Interruption Issues

### ❌ "Can't interrupt Lily"

**Cause**: Barge-in threshold too high.

**Solution**: Lower threshold in `lily/vad_manager.py`:
```python
VADManager(
    event_bus,
    barge_in_threshold=600.0,  # Easier to interrupt (default: 900.0)
)
```

### ❌ "Lily stops talking too easily"

**Cause**: Barge-in threshold too low.

**Solution**: Raise threshold:
```python
VADManager(
    event_bus,
    barge_in_threshold=1200.0,  # Harder to interrupt
)
```

---

## Performance Issues

### ❌ "High CPU usage"

**Solution 1** — Use smaller models:
```python
# Tiny Whisper
self.stt_manager = STTManager(self.event_bus, model_size="tiny")

# Smaller LLM
self.llm_manager = LLMManager(self.event_bus, model="tinyllama")
```

**Solution 2** — Reduce audio sample rate:
Edit `lily/audio_manager.py`:
```python
AudioManager(event_bus, sample_rate=8000)  # Lower quality (default: 16000)
```

**Solution 3** — Close other applications.

### ❌ "High memory usage"

**Normal**: Lily uses ~4GB RAM.

**If > 6GB**:
1. Close unused applications
2. Use smaller Whisper model
3. Reduce context window:
   ```python
   max_context_messages=2
   ```

### ❌ "Lily crashes after running for hours"

**Cause**: Memory leak or resource exhaustion.

**Solution 1** — Restart periodically:
```python
# Add to lily_main.py
import schedule
schedule.every(6).hours.do(restart_lily)
```

**Solution 2** — Check for memory leaks:
```python
import tracemalloc
tracemalloc.start()
# Monitor memory growth
```

---

## Conversation Flow Issues

### ❌ "Lily doesn't remember previous conversation"

**Cause 1**: Context window too small.

**Solution**:
```python
self.llm_manager = LLMManager(
    event_bus,
    max_context_messages=10,  # More history
)
```

**Cause 2**: Database not saving.

**Solution**: Check if `jarvis_memory.db` is being written:
```cmd
dir jarvis_memory.db
# Should show file size > 0
```

### ❌ "Lily repeats herself"

**Solution**: Increase LLM temperature:
```python
options={"temperature": 0.8}  # More variety
```

### ❌ "Lily doesn't understand my accent"

**Solution 1** — Speak more clearly.

**Solution 2** — Use larger Whisper model:
```python
self.stt_manager = STTManager(self.event_bus, model_size="medium")
```

**Solution 3** — Train custom acoustic model (advanced).

---

## Tool Execution Issues

### ❌ "Tool execution doesn't work"

**Diagnosis**:
```python
# Check if Hermes is loaded
print(lily.hermes_agent)  # Should not be None
```

**Solution**: Verify Hermes dependencies:
```cmd
pip install -r lily_requirements.txt
```

### ❌ "Tools fail with permission errors"

**Cause**: Windows UAC restrictions.

**Solution**: Run as administrator (one time):
```cmd
# Right-click cmd → Run as administrator
python lily_main.py
```

---

## Testing Issues

### ❌ "test_lily_streaming.py fails"

Run individual tests to identify the issue:
```python
# In test file
test_event_bus()  # Test this one
# Comment out others
```

**Common failures**:
- Audio backend: Install sounddevice
- Whisper: Install openai-whisper
- Ollama: Check Ollama is running
- LLM: Pull gemma4:cloud model

---

## Emergency Fixes

### ❌ Nothing works, complete reset:

```cmd
# 1. Uninstall all
pip uninstall -y ollama whisper edge-tts sounddevice soundfile pyaudio

# 2. Clean cache
pip cache purge

# 3. Reinstall
pip install -r lily_requirements.txt

# 4. Verify Ollama
ollama list
ollama pull gemma4:cloud

# 5. Test
python test_lily_streaming.py
```

### ❌ Lily is stuck in a state:

```python
# Press Ctrl+C to stop
# Then restart
python lily_main.py
```

---

## Getting Help

### Debug Mode

Enable verbose logging in `lily_main.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Collect Information

Before asking for help:
```cmd
# Python version
python --version

# Installed packages
pip list > packages.txt

# Ollama status
ollama list > ollama_models.txt

# Audio devices
python -c "import sounddevice; print(sounddevice.query_devices())" > audio.txt

# Test results
python test_lily_streaming.py > test_results.txt 2>&1
```

### Common Error Messages

**"module 'ollama' has no attribute 'chat'"**
→ Update ollama package: `pip install --upgrade ollama`

**"torch not compiled with CUDA"**
→ Normal, uses CPU. For GPU: reinstall PyTorch with CUDA

**"FFmpeg not found"**
→ Edge TTS might need FFmpeg. Install from https://ffmpeg.org/

**"Access denied" errors**
→ Run as administrator or check antivirus

---

## Still Having Issues?

1. **Check logs**: Terminal output shows detailed errors
2. **Run tests**: `python test_lily_streaming.py`
3. **Verify setup**: Ensure all dependencies installed
4. **Try examples**: Test with simple prompts first
5. **Check resources**: Ensure sufficient RAM and CPU

---

## Prevention Tips

✅ **Keep dependencies updated:**
```cmd
pip install --upgrade ollama whisper edge-tts
```

✅ **Regular Ollama updates:**
Download latest from https://ollama.com/download

✅ **Clean old models:**
```cmd
ollama rm old_model
```

✅ **Monitor resources:**
Task Manager → Performance tab

✅ **Backup memory:**
```cmd
copy jarvis_memory.db jarvis_memory.db.backup
```

---

**Most issues are fixed by ensuring:**
1. ✓ Ollama is running
2. ✓ gemma4:cloud model is pulled
3. ✓ Audio devices are working
4. ✓ All dependencies are installed

Happy troubleshooting! 🔧
