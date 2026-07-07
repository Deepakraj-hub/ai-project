import React, { useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { Avatar } from '../Avatar';

export default function AvatarCanvas({ expression, isTalking }) {
  const pointerRef = useRef({ x: 0, y: 0, active: false, lastMoveAt: 0 });

  return (
    <Canvas
      camera={{ position: [0, 0, 1.6], fov: 45 }}
      onPointerMove={(e) => {
        pointerRef.current = {
          x: e.pointer.x ?? 0,
          y: e.pointer.y ?? 0,
          active: true,
          lastMoveAt: performance.now(),
        };
      }}
      onPointerLeave={() => {
        pointerRef.current = { x: 0, y: 0, active: false, lastMoveAt: performance.now() };
      }}
    >
      <ambientLight intensity={1.5} />
      <directionalLight position={[1, 2, 3]} intensity={1.5} />
      <pointLight position={[-1, 1, 2]} intensity={0.5} />
      
      <Avatar expression={expression} isTalking={isTalking} pointerRef={pointerRef} />
      
      <OrbitControls 
        enableZoom={false} 
        enablePan={false}
        target={[0, -0.1, 0]}
        maxPolarAngle={Math.PI / 2} 
        minPolarAngle={Math.PI / 3}
      />
    </Canvas>
  );
}