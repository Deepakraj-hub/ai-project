import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { Avatar } from './Avatar';
import './App.css';

/* ── Helpers ───────────────────────────────── */
const analyzeAIResponse = (text) => {
  if (!text) return 'neutral';
  const t = text.toLowerCase();
  if (/haha|hehe|funny|joke|comedy|😂|🤣/.test(t)) return 'smiling';
  if (/sorry|shy|blush|maybe|😳|🙈/.test(t)) return 'shy';
  if (/sad|bad|hurt|cry|unfortunately|😔/.test(t)) return 'sad';
  if (/angry|wrong|stop|hate|😡/.test(t)) return 'angry';
  return 'neutral';
};

const FEMALE_VOICE_RX = [/zira/i, /jenny/i, /aria/i, /sonia/i, /samantha/i, /michelle/i, /linda/i, /heera/i, /priya/i, /neerja/i, /emily/i];
const MALE_VOICE_RX = [/david/i, /mark/i, /guy/i, /james/i, /george/i, /richard/i, /paul/i, /ryan/i, /brian/i, /male/i];

const scoreVoice = (v) => {
  let s = 0;
  if (FEMALE_VOICE_RX.some(rx => rx.test(v.name))) s += 20;
  if (/microsoft/i.test(v.name)) s += 8;
  if (/natural/i.test(v.name)) s += 4;
  if (/en[-_]?us/i.test(v.lang)) s += 3;
  if (MALE_VOICE_RX.some(rx => rx.test(v.name))) s -= 100;
  return s;
};

const pickLilyVoice = () => {
  const voices = window.speechSynthesis?.getVoices?.() || [];
  return voices.length ? [...voices].sort((a, b) => scoreVoice(b) - scoreVoice(a))[0] : null;
};

const cleanForSpeech = (text) =>
  (text || '')
    .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE00}-\u{FE0F}\u{200D}]/gu, '')
    .replace(/[*_#`~[\]()]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 400);

/* ── App Component ─────────────────────────── */
function App() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'System online. LILY Core initialised. Memory core connected.' },
  ]);
  const [input, setInput] = useState('');
  const [expression, setExpression] = useState('neutral');
  const [isTalking, setIsTalking] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [topics, setTopics] = useState([]);
  const [recalls, setRecalls] = useState([]);
  const [isMemoryConnected, setIsMemoryConnected] = useState(true);
  const [showTopics, setShowTopics] = useState(false);
  const [showRecalls, setShowRecalls] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [lastSearch, setLastSearch] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  const recognitionRef = useRef(null);
  const messagesEndRef = useRef(null);
  const lilyVoiceRef = useRef(null);
  const inputRef = useRef(null);

  /* auto-scroll */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /* voice preload */
  useEffect(() => {
    const load = () => { const v = pickLilyVoice(); if (v) lilyVoiceRef.current = v; };
    load();
    window.speechSynthesis?.addEventListener?.('voiceschanged', load);
    return () => window.speechSynthesis?.removeEventListener?.('voiceschanged', load);
  }, []);

  /* global mouse tracking for avatar eye follow */
  useEffect(() => {
    const onMove = (e) => {
      const x = (e.clientX / window.innerWidth) * 2 - 1;
      const y = -((e.clientY / window.innerHeight) * 2 - 1);
      setMousePos({ x, y });
    };
    window.addEventListener('mousemove', onMove);
    return () => window.removeEventListener('mousemove', onMove);
  }, []);

  /* speech recognition setup */
  useEffect(() => {
    const SR = window.webkitSpeechRecognition || window.SpeechRecognition;
    if (!SR) return;
    const rec = new SR();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = 'en-US';
    rec.onresult = (e) => {
      const transcript = Array.from(e.results).map(r => r[0].transcript).join('');
      if (e.results[0].isFinal) {
        setInput(transcript);
        setTimeout(() => handleSendMessage({ preventDefault: () => {} }), 400);
      }
    };
    rec.onend = () => setIsListening(false);
    recognitionRef.current = rec;
  }, []);

  /* ── send message ──────────────────────── */
  const handleSendMessage = useCallback(async (e, options = {}) => {
    e?.preventDefault();
    if (!input.trim()) return;

    const userMessage = options.prefix ? `${options.prefix} ${input.trim()}` : input.trim();
    const forceSearch = Boolean(options.forceSearch);
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:5000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          topics, recalls,
          memory_connected: isMemoryConnected,
          force_search: forceSearch,
        }),
      });

      const data = await res.json();
      const aiText = (data.text || '').trim() || "Sorry, I didn't catch that — try again?";

      setMessages(prev => [...prev, { role: 'assistant', content: aiText }]);

      if (data.search_used) {
        setLastSearch({ query: data.search_query, mode: data.search_mode, sources: data.sources || [] });
      } else {
        setLastSearch(null);
      }

      if (data.topics) setTopics(prev => [...new Set([...prev, ...data.topics])]);
      if (data.recalls) setRecalls(prev => [...new Set([...prev, ...data.recalls])]);

      setExpression(analyzeAIResponse(aiText));

      /* browser TTS */
      const speak = (text) => {
        if (!('speechSynthesis' in window)) return false;
        const clean = cleanForSpeech(text);
        if (!clean) return false;
        try {
          window.speechSynthesis.cancel();
          const u = new SpeechSynthesisUtterance(clean);
          u.lang = 'en-US';
          u.rate = 1.05;
          u.pitch = 1.35;
          const voice = lilyVoiceRef.current || pickLilyVoice();
          if (voice) { u.voice = voice; lilyVoiceRef.current = voice; }
          u.onstart = () => setIsTalking(true);
          u.onend = () => { setIsTalking(false); setExpression('neutral'); };
          u.onerror = () => setIsTalking(false);
          window.speechSynthesis.speak(u);
          return true;
        } catch { return false; }
      };

      if (!speak(aiText)) {
        setIsTalking(true);
        setTimeout(() => { setIsTalking(false); setExpression('neutral'); }, Math.max(2000, aiText.length * 60));
      }

    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Connection to LILY core interrupted. Retrying...' }]);
      setExpression('sad');
      setIsTalking(false);
    } finally {
      setLoading(false);
    }
  }, [input, topics, recalls, isMemoryConnected]);

  const toggleVoice = () => {
    if (isListening) { recognitionRef.current?.stop(); setIsListening(false); }
    else if (recognitionRef.current) { recognitionRef.current.start(); setIsListening(true); setInput(''); }
    else alert('Speech recognition not supported.');
  };

  const toggleMemory = () => {
    setIsMemoryConnected(prev => !prev);
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: isMemoryConnected ? 'Memory core disconnected. Operating in ephemeral mode.' : 'Memory core reconnected. Full cognitive suite online.',
    }]);
  };

  const toggleScreenShare = async () => {
    if (isScreenSharing) {
      setIsScreenSharing(false);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Screen sharing terminated.' }]);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
      setIsScreenSharing(true);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Screen sharing active. Analysing display...' }]);
      stream.getVideoTracks()[0].onended = () => {
        setIsScreenSharing(false);
        setMessages(prev => [...prev, { role: 'assistant', content: 'Screen sharing ended.' }]);
      };
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Screen sharing permission denied.' }]);
    }
  };

  return (
    <div className="lily-app">

      {/* ── AVATAR VIEWPORT ────────────────── */}
      <div className="avatar-viewport">
        <div className="avatar-glow" />

        <div className="avatar-brand">
          <h1>LILY</h1>
          <div className="avatar-brand-sub">COGNITIVE AI CORE v2.0</div>
        </div>

        <Canvas camera={{ position: [0, 0, 4.5], fov: 40 }}>
          <ambientLight intensity={1.2} />
          <directionalLight position={[2, 2, 2]} intensity={1.1} />
          <spotLight position={[-2, 4, 2]} intensity={0.6} color="#a855f7" />
          <spotLight position={[3, 1, 3]} intensity={0.3} color="#22d3ee" />
          <Avatar expression={expression} isTalking={isTalking} mousePos={mousePos} />
          <OrbitControls enableZoom enablePan={false} target={[0, 0, 0]} />
        </Canvas>

        <div className="avatar-status-bar">
          <div className={`status-indicator ${isMemoryConnected ? 'status-indicator--online' : 'status-indicator--offline'}`}>
            <span className={`status-dot ${isMemoryConnected ? 'status-dot--online' : 'status-dot--offline'}`} />
            {isMemoryConnected ? 'CORE ONLINE' : 'CORE OFFLINE'}
          </div>
          {isScreenSharing && (
            <div className="status-indicator status-indicator--sharing">
              <span className="status-dot status-dot--sharing" />
              SCREEN SHARING
            </div>
          )}
          <div className="avatar-expression-tag">
            {isTalking ? '● SPEAKING' : expression !== 'neutral' ? `● ${expression.toUpperCase()}` : '○ IDLE'}
          </div>
        </div>
      </div>

      {/* ── CONTROL PANEL ──────────────────── */}
      <div className="control-panel">
        <div className="panel-header">
          <span className="panel-title">CONSOLE</span>
          <span className="panel-time">{new Date().toLocaleTimeString()}</span>
        </div>

        {/* Toolbar */}
        <div className="toolbar">
          <button
            className={`toolbar-btn ${isMemoryConnected ? 'toolbar-btn--memory-on' : 'toolbar-btn--memory-off'}`}
            onClick={toggleMemory}
          >
            {isMemoryConnected ? '●' : '○'} MEMORY
          </button>
          <button
            className={`toolbar-btn ${showTopics ? 'toolbar-btn--active' : ''}`}
            onClick={() => setShowTopics(!showTopics)}
          >
            📋 TOPICS {topics.length > 0 && `(${topics.length})`}
          </button>
          <button
            className={`toolbar-btn ${showRecalls ? 'toolbar-btn--active' : ''}`}
            onClick={() => setShowRecalls(!showRecalls)}
          >
            🔄 RECALLS {recalls.length > 0 && `(${recalls.length})`}
          </button>
          <button
            className={`toolbar-btn ${isScreenSharing ? 'toolbar-btn--active' : ''}`}
            onClick={toggleScreenShare}
          >
            {isScreenSharing ? '🟡 SHARING' : '🖥️ SCREEN'}
          </button>
          <button
            className="toolbar-btn toolbar-btn--search"
            onClick={(e) => handleSendMessage(e, { prefix: 'smart search', forceSearch: true })}
            disabled={!input.trim() || loading}
          >
            🔍 SEARCH
          </button>
        </div>

        {/* Search results banner */}
        {lastSearch && (
          <div className="search-banner">
            <div className="search-banner-title">
              ▸ SEARCH ({lastSearch.mode || 'web'}) — {lastSearch.query}
            </div>
            {(lastSearch.sources || []).slice(0, 3).map((s, i) => (
              <div key={i} className="search-source">↳ {s.title}</div>
            ))}
          </div>
        )}

        {/* Topics panel */}
        {showTopics && topics.length > 0 && (
          <div className="info-panel">
            <div className="info-panel-label">▸ TOPICS</div>
            {topics.map((t, i) => <span key={i} className="topic-tag">#{t}</span>)}
          </div>
        )}

        {/* Recalls panel */}
        {showRecalls && recalls.length > 0 && (
          <div className="info-panel">
            <div className="info-panel-label">▸ RECALLS</div>
            {recalls.map((r, i) => <div key={i} className="recall-item">↳ {r}</div>)}
          </div>
        )}

        {/* Chat messages */}
        <div className="chat-container">
          {messages.map((msg, i) => (
            <div key={i} className={`chat-msg ${msg.role === 'user' ? 'chat-msg--user' : 'chat-msg--lily'}`}>
              <div className={`chat-role ${msg.role === 'user' ? 'chat-role--user' : 'chat-role--lily'}`}>
                {msg.role === 'user' ? '▸ YOU' : '◈ LILY'}
              </div>
              <div className="chat-text">{msg.content}</div>
            </div>
          ))}
          {loading && (
            <div className="chat-thinking">
              <div className="thinking-dots">
                <span /><span /><span />
              </div>
              Lily is thinking...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form className="input-area" onSubmit={handleSendMessage}>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isListening ? '🎤  Listening...' : 'Ask LILY anything...'}
            className={`input-field ${isListening ? 'input-field--listening' : ''}`}
          />
          <button
            type="button"
            onClick={toggleVoice}
            className={`btn-icon ${isListening ? 'btn-icon--listening' : ''}`}
          >
            {isListening ? '🔴' : '🎤'}
          </button>
          <button type="submit" className="btn-send">SEND</button>
        </form>
      </div>
    </div>
  );
}

export default App;