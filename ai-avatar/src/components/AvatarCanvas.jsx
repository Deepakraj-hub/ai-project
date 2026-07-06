import React from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { Avatar } from '../Avatar';

export default function AvatarCanvas({ expression, isTalking }) {
  return (
    <Canvas camera={{ position: [0, 0, 1.6], fov: 45 }}>
      <ambientLight intensity={1.5} />
      <directionalLight position={[1, 2, 3]} intensity={1.5} />
      <pointLight position={[-1, 1, 2]} intensity={0.5} />
      
      <Avatar expression={expression} isTalking={isTalking} />
      
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