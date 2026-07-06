import React from 'react';
import ChatBox from '../components/ChatBox';
// Import your new Avatar module here
import AvatarCanvas from '../components/AvatarCanvas';

export default function Dashboard() {
  return (
    <div style={{ 
      padding: '24px', 
      border: '1px solid #334155', 
      borderRadius: '16px', 
      backgroundColor: '#111827',
      marginTop: '20px',
      width: '100%',
      maxWidth: '900px', // Widened to fit both cards side-by-side smoothly
      boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.3)',
      display: 'flex',
      flexDirection: 'column',
      gap: '20px'
    }}>
      
      {/* Title Header */}
      <div style={{ textAlign: 'center', width: '100%' }}>
        <h3 style={{ color: '#a5b4fc', margin: '0 0 6px 0', fontSize: '1.4rem', fontWeight: '700' }}>
          AI Workspace Panel
        </h3>
        <p style={{ color: '#64748b', margin: 0, fontSize: '0.95rem' }}>
          Live interactive viewport control desk
        </p>
      </div>

      {/* Grid Container holding Avatar on Left, Chat on Right */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '20px',
        justifyContent: 'center',
        width: '100%'
      }}>
        
        {/* Render Avatar Section */}
        <AvatarCanvas />

        {/* Render Chat Section */}
        <ChatBox />

      </div>
    </div>
  );
}