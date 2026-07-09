# How to Start Lily Desktop Application

## Quick Start (3 Steps)

### Step 1: Open TWO Command Prompt windows

Press `Win + R`, type `cmd`, press Enter (do this twice)

---

### Step 2: Start the Backend (Terminal 1)

In the **first** command prompt:

```cmd
cd c:\Users\DSEPY18239\Documents\ai-project
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
```

**Keep this window open!**

---

### Step 3: Start the Frontend (Terminal 2)

In the **second** command prompt:

```cmd
cd c:\Users\DSEPY18239\Documents\ai-project\ai-avatar
npm run dev
```

You should see:
```
VITE v8.x.x  ready in XXX ms

  ➜  Local:   http://localhost:5173/
```

**Your browser should automatically open to the app!**

If not, open: **http://localhost:5173**

---

## What You'll See

✨ **3D Avatar Interface** with:
- Animated 3D character (Lily)
- Chat interface
- Real-time responses
- Emotion expressions (happy, sad, shy, etc.)
- Topics and recalls tracking
- Smart web search integration

---

## Using the App

1. **Type a message** in the chat box
2. **Press Enter** or click Send
3. **Lily responds** with:
   - Text response
   - Animated avatar expressions
   - Extracted topics
   - Memory recalls

---

## Features

### Chat with Lily
```
You: "Hello Lily!"
Lily: *smiling* "Hi! How can I help you today?"
```

### Ask Questions
```
You: "What's the weather like?"
Lily: "I'm currently in Chennai, Tamil Nadu, India..."
```

### Use Tools (Agent Mode)
```
You: "Open Chrome"
Lily: "Let me handle that..."
[Opens Chrome browser]
```

### Smart Search
```
You: "What's trending today?"
Lily: [Searches web and responds with current info]
```

---

## Troubleshooting

### ❌ "ModuleNotFoundError: No module named 'flask'"

```cmd
pip install flask flask-cors
```

### ❌ "npm: command not found"

Install Node.js from: https://nodejs.org/

### ❌ Backend won't start

Check if port 5000 is already in use:
```cmd
netstat -ano | findstr :5000
```

### ❌ Frontend won't start

```cmd
cd ai-avatar
npm install
npm run dev
```

### ❌ "Ollama not available"

1. Check if Ollama is running (system tray icon)
2. Verify model is pulled:
   ```cmd
   ollama list
   ollama pull gemma4:cloud
   ```

---

## Alternative: Use the Batch Script

Double-click: **`start_lily_desktop.bat`**

This will:
1. Install missing dependencies
2. Start backend automatically
3. Start frontend automatically
4. Open browser

---

## Stopping the App

1. Press `Ctrl+C` in **both** command prompt windows
2. Or simply close both windows

---

## Tech Stack

- **Frontend**: React + Vite + Three.js + @pixiv/three-vrm
- **Backend**: Python Flask
- **AI**: Ollama (Gemma4)
- **3D Avatar**: VRM format with animations

---

## Port Configuration

- **Backend**: http://localhost:5000
- **Frontend**: http://localhost:5173

If these ports are in use, edit:
- Backend port: `app.py` (line: `app.run(port=5000)`)
- Frontend port: `ai-avatar/vite.config.js`

---

**Enjoy talking with Lily! 🎙️✨**
