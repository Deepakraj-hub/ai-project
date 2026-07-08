import React, { useState, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { Avatar } from './Avatar';
import './App.css';

function App() {
  const [expression, setExpression] = useState('neutral');
  const [isTalking, setIsTalking] = useState(false);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Expose methods to global window object for PySide6 integration
  useEffect(() => {
    window.setAvatarExpression = (expr) => {
      setExpression(expr);
    };
    
    window.setAvatarTalking = (talking) => {
      setIsTalking(talking);
    };
    
    console.log("Avatar ready for PySide6 control.");
    
    return () => {
      delete window.setAvatarExpression;
      delete window.setAvatarTalking;
    };
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

  return (
    <div className="avatar-viewport-fullscreen">
      <div className="avatar-glow" />

      <Canvas camera={{ position: [0, 0, 4.5], fov: 40 }}>
        <ambientLight intensity={1.2} />
        <directionalLight position={[2, 2, 2]} intensity={1.1} />
        <spotLight position={[-2, 4, 2]} intensity={0.6} color="#a855f7" />
        <spotLight position={[3, 1, 3]} intensity={0.3} color="#22d3ee" />
        <Avatar expression={expression} isTalking={isTalking} mousePos={mousePos} />
        <OrbitControls enableZoom={true} enablePan={false} target={[0, 0, 0]} />
      </Canvas>
    </div>
  );
}

export default App;