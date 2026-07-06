import React, { useRef, useEffect } from 'react';
import { useGLTF } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

export function Avatar({ expression, isTalking }) {
  const { scene } = useGLTF('/avatar.glb');
  const groupRef = useRef();
  
  const hairRegistry = useRef([]);
  const morphMeshes = useRef([]);

  // Blinking Timing Parameters
  const blinkTimer = useRef(0);
  const nextBlinkTime = useRef(2.0);
  const blinkDuration = 0.15;

  useEffect(() => {
    hairRegistry.current = [];
    morphMeshes.current = [];

    scene.traverse((child) => {
      if (child.isBone) {
        const lowerName = child.name.toLowerCase();

        // ─── FIXED ARM ROTATION TARGETING ───
        if (lowerName.includes('upperarm') && (lowerName.includes('_l_') || lowerName.includes('left'))) {
          child.rotation.set(0, 0, -1.3); // Explicitly drops Left Arm down
        }
        
        if (lowerName.includes('upperarm') && (lowerName.includes('_r_') || lowerName.includes('right'))) {
          child.rotation.set(0, 0, 1.3);  // Explicitly drops Right Arm down
        }

        // Gather hair physics objects
        if (lowerName.includes('hair') || lowerName.includes('sec_') || lowerName.includes('secondary')) {
          hairRegistry.current.push({
            bone: child,
            initialX: child.rotation.x,
            initialZ: child.rotation.z
          });
        }
      }

      // Extract facial meshes containing morph shapes
      if (child.isMesh && child.morphTargetDictionary && child.morphTargetInfluences) {
        morphMeshes.current.push(child);
      }
    });

    // Framing setup
    scene.position.set(0, -0.85, 0);
    scene.scale.set(0.9, 0.9, 0.9);
    scene.rotation.set(0, 0, 0);
  }, [scene]);

  useFrame((state, delta) => {
    const time = state.clock.getElapsedTime();
    const currentExp = expression || 'neutral';

    // 1. Subtle hair wind simulation
    const waveX = Math.sin(time * 2.0) * 0.04;
    const waveZ = Math.cos(time * 1.5) * 0.03;
    hairRegistry.current.forEach(({ bone, initialX, initialZ }) => {
      bone.rotation.x = initialX + waveX;
      bone.rotation.z = initialZ + waveZ;
    });

    // 2. Procedural automatic blink timeline tracker
    blinkTimer.current += delta;
    let blinkValue = 0;

    if (blinkTimer.current >= nextBlinkTime.current) {
      const progress = (blinkTimer.current - nextBlinkTime.current) / blinkDuration;
      if (progress <= 1) {
        blinkValue = Math.sin(progress * Math.PI);
      } else {
        blinkTimer.current = 0;
        nextBlinkTime.current = 2.0 + Math.random() * 3.0;
      }
    }

    // 3. VRoid-Optimized Expression Mixer
    morphMeshes.current.forEach((mesh) => {
      const dict = mesh.morphTargetDictionary;
      const influences = mesh.morphTargetInfluences;

      Object.keys(dict).forEach((key) => {
        const idx = dict[key];
        const lowerKey = key.toLowerCase();

        let targetWeight = 0;

        // Blinking
        if (lowerKey.includes('blink') || lowerKey.includes('eye_close') || lowerKey.includes('eyesclosed')) {
          influences[idx] = blinkValue;
          return; 
        }

        // Happy / Smile
        if (currentExp === 'happy') {
          if (
            lowerKey.includes('joy') || 
            lowerKey.includes('fun') || 
            lowerKey.includes('smile') || 
            lowerKey.includes('happy') ||
            lowerKey.includes('mth_up')
          ) {
            targetWeight = 0.85;
          }
        }

        // Sad / Frown
        if (currentExp === 'sad') {
          if (
            lowerKey.includes('sorrow') || 
            lowerKey.includes('sad') || 
            lowerKey.includes('frown') || 
            lowerKey.includes('mth_down')
          ) {
            targetWeight = 0.75;
          }
        }

        // Angry
        if (currentExp === 'angry') {
          if (lowerKey.includes('angry') || lowerKey.includes('rage') || lowerKey.includes('irate')) {
            targetWeight = 0.8;
          }
        }

        // Speech Lip Sync
        if (isTalking) {
          if (
            lowerKey.includes('mth_a') || 
            lowerKey === 'a' || 
            lowerKey === 'aa' || 
            lowerKey.includes('mouth_a') || 
            lowerKey.includes('jaw_open') ||
            lowerKey.includes('viseme_aa')
          ) {
            targetWeight = Math.max(targetWeight, Math.abs(Math.sin(time * 13.0)) * 0.55);
          }
        }

        // Smoothly blend values
        influences[idx] = THREE.MathUtils.lerp(influences[idx], targetWeight, 0.2);
      });
    });
  });

  return <primitive ref={groupRef} object={scene} />;
}

useGLTF.preload('/avatar.glb');