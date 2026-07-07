import React, { useState } from 'react';

export default function ChatBox({ setExpression, setIsTalking }) {
  const [text, setText] = useState('');
  const [messages, setMessages] = useState([
    { id: 1, sender: 'lily', text: "Hello! I’m Lily, your AI avatar assistant. How can I help you today?" }
  ]);

  const handleSend = () => {
    if (!text.trim()) return;

    // Add user message
    const userMsg = { id: Date.now(), sender: 'user', text: text };
    setMessages(prev => [...prev, userMsg]);
    setText('');

    // Trigger talking/expression mock loops
    setIsTalking(true);
    setExpression('happy');

    setTimeout(() => {
      const jarvisMsg = { id: Date.now() + 1, sender: 'lily', text: "Processing your request..." };
      setMessages(prev => [...prev, jarvisMsg]);
      
      setTimeout(() => {
        setIsTalking(false);
        setExpression('neutral');
      }, 3000);
    }, 1200);
  };

  return (
    <>
      <div className="hud-terminal-output">
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            className={`message-bubble message-${msg.sender}`}
          >
            {msg.text}
          </div>
        ))}
      </div>

      <div className="hud-input-row">
        <input 
          type="text" 
          className="hud-text-field"
          placeholder="Type an AI instruction..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        />
        <button className="hud-send-btn" onClick={handleSend}>
          SEND
        </button>
      </div>
    </>
  );
}