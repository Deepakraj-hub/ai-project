import React, { useState, useRef, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { Avatar } from './Avatar';

// Text analyzer helper function to scan for emotions
const analyzeAIResponse = (text) => {
  if (!text) return 'neutral';
  const lowerText = text.toLowerCase();

  // Comedy / Laughter -> smiling
  if (
    lowerText.includes('haha') || lowerText.includes('hehe') || 
    lowerText.includes('funny') || lowerText.includes('joke') || 
    lowerText.includes('comedy') || lowerText.includes('😂') || lowerText.includes('🤣')
  ) {
    return 'smiling';
  }

  // Shy / Blushing -> shy
  if (
    lowerText.includes('sorry') || lowerText.includes('shy') || 
    lowerText.includes('blush') || lowerText.includes('maybe') || 
    lowerText.includes('😳') || lowerText.includes('🙈')
  ) {
    return 'shy';
  }

  // Sad / Emotional -> sad
  if (
    lowerText.includes('sad') || lowerText.includes('bad') || 
    lowerText.includes('hurt') || lowerText.includes('cry') || 
    lowerText.includes('unfortunately') || lowerText.includes('😔')
  ) {
    return 'sad';
  }

  // Angry / Frustrated -> angry
  if (
    lowerText.includes('angry') || lowerText.includes('wrong') || 
    lowerText.includes('stop') || lowerText.includes('hate') || lowerText.includes('😡')
  ) {
    return 'angry';
  }

  return 'neutral';
};

function App() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'System initialized. JARVIS Core ready. Memory core connected.' }
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
  
  const recognitionRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Initialize speech recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0].transcript)
          .join('');
        
        if (event.results[0].isFinal) {
          setInput(transcript);
          // Auto-send after voice input
          setTimeout(() => {
            handleSendMessage({ preventDefault: () => {} });
          }, 500);
        }
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
  }, []);

  const handleSendMessage = async (e) => {
    e?.preventDefault();
    if (!input.trim()) return;

    const userMessage = input;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:5000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: userMessage,
          topics: topics,
          recalls: recalls,
          memory_connected: isMemoryConnected
        }),
      });

      const data = await response.json();
      const aiResponseText = data.text || '';

      setMessages((prev) => [...prev, { role: 'assistant', content: aiResponseText }]);

      // Extract topics from response if any
      if (data.topics) {
        setTopics(prev => [...prev, ...data.topics]);
      }

      // Extract recalls from response if any
      if (data.recalls) {
        setRecalls(prev => [...prev, ...data.recalls]);
      }

      const detectedMood = analyzeAIResponse(aiResponseText);
      setExpression(detectedMood);

      setIsTalking(true);
      const speechDuration = Math.max(2000, aiResponseText.length * 65);
      setTimeout(() => {
        setIsTalking(false);
        setExpression('neutral');
      }, speechDuration);

    } catch (error) {
      console.error(error);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'JARVIS: Memory core connection interrupted. Reconnecting...' }
      ]);
      setExpression('neutral');
      setIsTalking(false);
    } finally {
      setLoading(false);
    }
  };

  const toggleVoiceInput = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      if (recognitionRef.current) {
        recognitionRef.current.start();
        setIsListening(true);
        setInput('');
      } else {
        alert('Speech recognition is not supported in this browser.');
      }
    }
  };

  const toggleMemoryCore = () => {
    setIsMemoryConnected(!isMemoryConnected);
    setMessages(prev => [...prev, { 
      role: 'assistant', 
      content: isMemoryConnected ? 'Memory core disconnected. JARVIS operating in offline mode.' : 'Memory core connected. JARVIS is fully operational.' 
    }]);
  };

  const toggleScreenShare = async () => {
    if (isScreenSharing) {
      setIsScreenSharing(false);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Screen sharing terminated.' 
      }]);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: false,
      });
      
      setIsScreenSharing(true);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Screen sharing activated. JARVIS is now analyzing your display.' 
      }]);

      stream.getVideoTracks()[0].onended = () => {
        setIsScreenSharing(false);
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: 'Screen sharing session ended.' 
        }]);
      };
    } catch (error) {
      console.error('Screen sharing error:', error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Screen sharing failed. Please ensure you grant permission.' 
      }]);
    }
  };

  return (
    <div style={{ 
      display: 'flex', 
      width: '100vw', 
      height: '100vh', 
      backgroundColor: '#0a0a0f', 
      color: '#fff', 
      fontFamily: 'monospace', 
      padding: '20px', 
      boxSizing: 'border-box',
      background: 'radial-gradient(ellipse at center, #141420 0%, #0a0a0f 100%)'
    }}>
      
      {/* LEFT WINDOW: 3D AVATAR CANVAS */}
      <div style={{ 
        width: '40%', 
        height: '100%', 
        position: 'relative', 
        backgroundColor: '#0d0d14', 
        borderRadius: '16px', 
        marginRight: '20px', 
        overflow: 'hidden',
        border: '1px solid #1a1a2e',
        boxShadow: '0 0 60px rgba(100, 50, 255, 0.05)'
      }}>
        {/* JARVIS Logo Overlay */}
        <div style={{
          position: 'absolute',
          top: '20px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 10,
          textAlign: 'center',
          pointerEvents: 'none'
        }}>
          <h1 style={{
            color: '#00e676',
            fontFamily: 'monospace',
            fontSize: '28px',
            letterSpacing: '8px',
            fontWeight: 300,
            textShadow: '0 0 40px rgba(0, 230, 118, 0.2)',
            margin: 0
          }}>JARVIS</h1>
          <div style={{
            fontSize: '10px',
            color: '#4a4a6a',
            letterSpacing: '4px',
            marginTop: '2px',
            fontFamily: 'monospace'
          }}>✦ MEMORY CORE v2.0 ✦</div>
        </div>

        {/* Status indicators */}
        <div style={{
          position: 'absolute',
          bottom: '20px',
          left: '20px',
          zIndex: 10,
          display: 'flex',
          gap: '12px',
          alignItems: 'center'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '10px',
            color: isMemoryConnected ? '#4ade80' : '#ef4444',
            fontFamily: 'monospace'
          }}>
            <span style={{
              display: 'inline-block',
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: isMemoryConnected ? '#4ade80' : '#ef4444',
              animation: isMemoryConnected ? 'pulse 2s infinite' : 'none'
            }}></span>
            {isMemoryConnected ? 'MEMORY CORE ONLINE' : 'MEMORY CORE OFFLINE'}
          </div>
          {isScreenSharing && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '10px',
              color: '#f59e0b',
              fontFamily: 'monospace'
            }}>
              <span style={{
                display: 'inline-block',
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: '#f59e0b',
                animation: 'pulse 1s infinite'
              }}></span>
              SCREEN SHARING
            </div>
          )}
        </div>

        <Canvas camera={{ position: [0, 0, 4.5], fov: 40 }}>
          <ambientLight intensity={1.2} />
          <directionalLight position={[2, 2, 2]} intensity={1.2} />
          <spotLight position={[-2, 4, 2]} intensity={0.8} color="#00e676" />
          <Avatar expression={expression} isTalking={isTalking} />
          <OrbitControls enableZoom={true} target={[0, 0, 0]} />
        </Canvas>

        {/* CSS Pulse Animation */}
        <style>{`
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
          }
        `}</style>
      </div>

      {/* RIGHT WINDOW: INTERFACE */}
      <div style={{ 
        width: '60%', 
        padding: '20px', 
        display: 'flex', 
        flexDirection: 'column', 
        backgroundColor: '#0d0d14', 
        borderRadius: '16px', 
        boxSizing: 'border-box',
        border: '1px solid #1a1a2e',
        boxShadow: '0 0 60px rgba(100, 50, 255, 0.05)'
      }}>
        {/* Header with controls */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #1a1a2e',
          paddingBottom: '12px',
          marginBottom: '15px'
        }}>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <h2 style={{ 
              color: '#00e676', 
              fontFamily: 'monospace', 
              fontSize: '14px', 
              letterSpacing: '3px',
              fontWeight: 300,
              margin: 0
            }}>CONSOLE</h2>
            <span style={{ fontSize: '10px', color: '#4a4a6a', fontFamily: 'monospace' }}>
              {new Date().toLocaleTimeString()}
            </span>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={toggleMemoryCore}
              style={{
                padding: '6px 12px',
                backgroundColor: isMemoryConnected ? 'rgba(74, 222, 128, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                border: `1px solid ${isMemoryConnected ? 'rgba(74, 222, 128, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                color: isMemoryConnected ? '#4ade80' : '#ef4444',
                borderRadius: '4px',
                fontSize: '10px',
                fontFamily: 'monospace',
                cursor: 'pointer',
                transition: 'all 0.3s'
              }}
            >
              {isMemoryConnected ? '● MEMORY CORE' : '○ MEMORY CORE'}
            </button>
          </div>
        </div>

        {/* Topics, Recalls & Share Screen Bar */}
        <div style={{
          display: 'flex',
          gap: '10px',
          marginBottom: '12px',
          flexWrap: 'wrap'
        }}>
          <button
            onClick={() => setShowTopics(!showTopics)}
            style={{
              padding: '4px 14px',
              backgroundColor: showTopics ? 'rgba(0, 230, 118, 0.15)' : 'transparent',
              border: '1px solid rgba(0, 230, 118, 0.2)',
              color: '#00e676',
              borderRadius: '20px',
              fontSize: '10px',
              fontFamily: 'monospace',
              cursor: 'pointer',
              transition: 'all 0.3s'
            }}
          >
            📋 TOPICS {topics.length > 0 && `(${topics.length})`}
          </button>
          <button
            onClick={() => setShowRecalls(!showRecalls)}
            style={{
              padding: '4px 14px',
              backgroundColor: showRecalls ? 'rgba(0, 230, 118, 0.15)' : 'transparent',
              border: '1px solid rgba(0, 230, 118, 0.2)',
              color: '#00e676',
              borderRadius: '20px',
              fontSize: '10px',
              fontFamily: 'monospace',
              cursor: 'pointer',
              transition: 'all 0.3s'
            }}
          >
            🔄 RECALLS {recalls.length > 0 && `(${recalls.length})`}
          </button>
          <button
            onClick={toggleScreenShare}
            style={{
              padding: '4px 14px',
              backgroundColor: isScreenSharing ? 'rgba(245, 158, 11, 0.2)' : 'transparent',
              border: '1px solid rgba(245, 158, 11, 0.2)',
              color: isScreenSharing ? '#f59e0b' : '#00e676',
              borderRadius: '20px',
              fontSize: '10px',
              fontFamily: 'monospace',
              cursor: 'pointer',
              transition: 'all 0.3s'
            }}
          >
            {isScreenSharing ? '🟡 SHARING' : '🖥️ SHARE SCREEN'}
          </button>
        </div>

        {/* Topics Panel */}
        {showTopics && topics.length > 0 && (
          <div style={{
            marginBottom: '12px',
            padding: '12px 14px',
            backgroundColor: 'rgba(0, 230, 118, 0.03)',
            borderRadius: '8px',
            border: '1px solid rgba(0, 230, 118, 0.08)',
            maxHeight: '100px',
            overflowY: 'auto'
          }}>
            <div style={{ fontSize: '9px', color: '#4a4a6a', marginBottom: '6px', letterSpacing: '2px' }}>▸ TOPICS</div>
            {topics.map((topic, i) => (
              <span key={i} style={{
                display: 'inline-block',
                padding: '2px 12px',
                margin: '2px 4px 2px 0',
                backgroundColor: 'rgba(0, 230, 118, 0.1)',
                borderRadius: '12px',
                fontSize: '11px',
                color: '#4ade80'
              }}>
                #{topic}
              </span>
            ))}
          </div>
        )}

        {/* Recalls Panel */}
        {showRecalls && recalls.length > 0 && (
          <div style={{
            marginBottom: '12px',
            padding: '12px 14px',
            backgroundColor: 'rgba(0, 230, 118, 0.03)',
            borderRadius: '8px',
            border: '1px solid rgba(0, 230, 118, 0.08)',
            maxHeight: '100px',
            overflowY: 'auto'
          }}>
            <div style={{ fontSize: '9px', color: '#4a4a6a', marginBottom: '6px', letterSpacing: '2px' }}>▸ RECALLS</div>
            {recalls.map((recall, i) => (
              <div key={i} style={{
                fontSize: '12px',
                color: '#a0a0c0',
                padding: '2px 0',
                borderBottom: i < recalls.length - 1 ? '1px solid rgba(0, 230, 118, 0.05)' : 'none'
              }}>
                ↳ {recall}
              </div>
            ))}
          </div>
        )}

        {/* Messages */}
        <div style={{ 
          flex: 1, 
          overflowY: 'auto', 
          paddingRight: '6px',
          marginBottom: '12px',
          backgroundColor: 'rgba(0,0,0,0.2)',
          borderRadius: '8px',
          padding: '12px 14px'
        }}>
          {messages.map((msg, i) => (
            <div key={i} style={{ 
              marginBottom: '10px', 
              lineHeight: '1.6',
              padding: '8px 12px',
              borderRadius: '6px',
              backgroundColor: msg.role === 'user' ? 'rgba(59, 130, 246, 0.05)' : 'rgba(0, 230, 118, 0.04)',
              borderLeft: `3px solid ${msg.role === 'user' ? '#3b82f6' : '#00e676'}`
            }}>
              <strong style={{ 
                color: msg.role === 'user' ? '#60a5fa' : '#4ade80',
                fontSize: '11px',
                fontFamily: 'monospace'
              }}>
                {msg.role === 'user' ? '▸ USER' : '◈ JARVIS'}
              </strong>
              <span style={{ 
                display: 'block',
                marginTop: '2px',
                fontSize: '14px',
                color: '#d0d0e0'
              }}>{msg.content}</span>
            </div>
          ))}
          {loading && (
            <div style={{ 
              color: '#4a4a6a', 
              fontStyle: 'italic', 
              fontSize: '12px',
              padding: '8px 12px',
              fontFamily: 'monospace'
            }}>
              ⚡ Processing memory core...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <form onSubmit={handleSendMessage} style={{ 
          display: 'flex', 
          gap: '10px',
          borderTop: '1px solid #1a1a2e',
          paddingTop: '12px'
        }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isListening ? "🎤 Listening..." : "Type or speak to JARVIS..."}
            style={{ 
              flex: 1, 
              padding: '12px 16px', 
              backgroundColor: '#0a0a12', 
              border: isListening ? '1px solid #00e676' : '1px solid #1a1a2e',
              color: '#fff', 
              borderRadius: '8px', 
              fontFamily: 'monospace', 
              outline: 'none',
              fontSize: '13px',
              transition: 'all 0.3s'
            }}
          />
          <button
            type="button"
            onClick={toggleVoiceInput}
            style={{
              padding: '12px 16px',
              backgroundColor: isListening ? 'rgba(0, 230, 118, 0.2)' : 'rgba(0, 230, 118, 0.05)',
              border: `1px solid ${isListening ? '#00e676' : 'rgba(0, 230, 118, 0.15)'}`,
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '16px',
              transition: 'all 0.3s'
            }}
          >
            {isListening ? '🔴' : '🎤'}
          </button>
          <button
            type="submit"
            style={{
              padding: '12px 28px',
              backgroundColor: '#00e676',
              color: '#000',
              border: 'none',
              borderRadius: '8px',
              fontWeight: 'bold',
              cursor: 'pointer',
              fontFamily: 'monospace',
              fontSize: '12px',
              letterSpacing: '1px',
              transition: 'all 0.3s'
            }}
          >
            SEND
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;