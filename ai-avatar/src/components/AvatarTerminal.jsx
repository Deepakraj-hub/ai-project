// src/components/AvatarTerminal.jsx
import { useEffect, useRef } from 'react';
import './AvatarTerminal.css'; // we'll create this

const AvatarTerminal = () => {
  const inputRef = useRef(null);

  const handleSend = () => {
    const msg = inputRef.current?.value.trim();
    if (!msg) return;
    
    // Add user message to chat
    const chatArea = document.querySelector('.chat-area');
    const userLine = document.createElement('div');
    userLine.className = 'chat-line';
    userLine.innerHTML = `<span class="prompt">⏺</span><span class="user-msg">${msg}</span>`;
    
    const firstLine = chatArea?.querySelector('.chat-line');
    if (firstLine) {
      chatArea.insertBefore(userLine, firstLine.nextSibling);
    }
    
    // Update AI response
    const aiLine = chatArea?.querySelector('.chat-line .ai-msg')?.closest('.chat-line');
    if (aiLine) {
      const aiMsg = aiLine.querySelector('.ai-msg');
      const responses = [
        'Processing your request... 🤖',
        'Context loaded. How can I assist?',
        'Acknowledged. Streaming response...',
        'AI avatar online. Ready for next command.'
      ];
      aiMsg.textContent = responses[Math.floor(Math.random() * responses.length)];
    }
    
    inputRef.current.value = '';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="console">
      {/* Header */}
      <div className="console-header">
        <span className="title">⚡ JARVIS CONSOLE</span>
        <span className="badge">v2.0_SYS · AI TERMINAL</span>
      </div>

      {/* Avatar Section */}
      <div className="avatar-section">
        <div className="avatar-container">
          <svg className="avatar-svg" viewBox="0 0 100 100" fill="none">
            <circle cx="50" cy="48" r="28" fill="#1f3348" stroke="#3c6a8f" strokeWidth="1.5" />
            <circle cx="50" cy="48" r="24" fill="#1d3145" />
            <circle cx="41" cy="44" r="3.5" fill="#b7e6ff" />
            <circle cx="59" cy="44" r="3.5" fill="#b7e6ff" />
            <circle cx="41" cy="44" r="1.8" fill="#0b1a2a" />
            <circle cx="59" cy="44" r="1.8" fill="#0b1a2a" />
            <path d="M43 56 Q50 62, 57 56" stroke="#86b9e0" strokeWidth="2" strokeLinecap="round" fill="none" />
            
            <g className="hair-group">
              <path d="M28 35 Q22 26, 28 15 Q32 8, 38 14 Q34 22, 30 32" fill="#182635" stroke="#2f4f6b" strokeWidth="0.6" />
              <path d="M34 28 Q30 18, 36 10 Q42 5, 44 14 Q40 20, 36 28" fill="#182635" stroke="#2f4f6b" strokeWidth="0.6" />
              <path d="M40 15 Q50 6, 60 15 Q56 10, 50 8 Q44 10, 40 15" fill="#1c3145" stroke="#315570" strokeWidth="0.7" />
              <path d="M48 12 Q55 6, 64 14 Q58 10, 50 12" fill="#1a2d40" stroke="#2c4d68" strokeWidth="0.6" />
              <path d="M70 36 Q76 26, 72 16 Q68 8, 62 14 Q66 22, 68 32" fill="#182635" stroke="#2f4f6b" strokeWidth="0.6" />
              <path d="M64 28 Q68 18, 62 10 Q56 5, 56 14 Q60 20, 64 28" fill="#182635" stroke="#2f4f6b" strokeWidth="0.6" />
              <path d="M32 40 Q26 36, 30 28 Q34 24, 36 32 Q34 36, 32 40" fill="#1a2d40" stroke="#2c4d68" strokeWidth="0.5" />
              <path d="M68 40 Q74 36, 70 28 Q66 24, 64 32 Q66 36, 68 40" fill="#1a2d40" stroke="#2c4d68" strokeWidth="0.5" />
            </g>
            <circle cx="27" cy="48" r="5" fill="#1f3348" stroke="#2f5270" strokeWidth="0.7" />
            <circle cx="73" cy="48" r="5" fill="#1f3348" stroke="#2f5270" strokeWidth="0.7" />
          </svg>
        </div>
        <div className="avatar-text">
          <div className="greeting">👋 Hello! I am your AI Avatar</div>
          <div>
            <span className="highlight">assistant</span>
            <span style={{ color: '#a0bedb', marginLeft: '6px' }}>· How can I help you today?</span>
          </div>
        </div>
      </div>

      {/* Chat Area */}
      <div className="chat-area">
        <div className="chat-line">
          <span className="prompt">⏺</span>
          <span className="user-msg">hi!</span>
        </div>
        <div className="chat-line">
          <span className="prompt">🤖</span>
          <span className="ai-msg">Streaming your text context processing request...</span>
        </div>
        <div className="status-line">
          <span className="dot"></span>
          <span>AI ready · context sync</span>
          <span style={{ marginLeft: 'auto', opacity: 0.7 }}>SYS_CORE_ONLINE // LOC_JP_SERVER_M2</span>
        </div>
      </div>

      {/* Input Row */}
      <div className="input-row">
        <input 
          ref={inputRef}
          type="text" 
          placeholder="Type an AI instruction..." 
          onKeyDown={handleKeyDown}
        />
        <button onClick={handleSend}>Send</button>
      </div>

      {/* Footer */}
      <div className="sys-footer">
        <span>⚙️ v2.0_SYS · AI TERMINAL · 2026</span>
      </div>
    </div>
  );
};

export default AvatarTerminal;