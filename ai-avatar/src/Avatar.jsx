import React, { useRef, useEffect } from 'react';
import { useGLTF } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

/**
 * Avatar component — lifelike 3D character with:
 *   • Full-window cursor tracking (eyes, head, spine follow pointer)
 *   • Breathing + micro-sway idle animation
 *   • Wind-based hair physics
 *   • Procedural blink with randomised double-blinks
 *   • VRoid-optimised expression + lip-sync morphs
 */
export function Avatar({ expression, isTalking, mousePos }) {
  const { scene } = useGLTF('/avatar.glb');
  const groupRef = useRef();

  const hairRegistry = useRef([]);
  const morphMeshes = useRef([]);
  const lookBones = useRef({ head: null, neck: null, spine: null, leftEye: null, rightEye: null });
  const basePoseRef = useRef({ y: -0.85, rotY: 0 });

  // Smoothed look target so head movement feels organic, not jittery
  const smoothTarget = useRef(new THREE.Vector3(0, 0, 5));

  // Blink timing
  const blinkTimer = useRef(0);
  const nextBlinkTime = useRef(2.5);
  const blinkDuration = 0.14;
  const doDoubleBlink = useRef(false);
  const doubleBlinkGap = 0.22;

  useEffect(() => {
    hairRegistry.current = [];
    morphMeshes.current = [];
    lookBones.current = { head: null, neck: null, spine: null, leftEye: null, rightEye: null };

    scene.traverse((child) => {
      if (child.isBone) {
        const n = child.name.toLowerCase();

        if (!lookBones.current.head && n.includes('head')) lookBones.current.head = child;
        if (!lookBones.current.neck && n.includes('neck')) lookBones.current.neck = child;
        if (!lookBones.current.spine && (n.includes('spine') || n.includes('chest')))
          lookBones.current.spine = child;
        if (!lookBones.current.leftEye && (n.includes('lefteye') || n.includes('eye_l') || n.includes('eye.l')))
          lookBones.current.leftEye = child;
        if (!lookBones.current.rightEye && (n.includes('righteye') || n.includes('eye_r') || n.includes('eye.r')))
          lookBones.current.rightEye = child;

        // Drop arms naturally
        if (n.includes('upperarm') && (n.includes('_l_') || n.includes('left')))
          child.rotation.set(0, 0, -1.3);
        if (n.includes('upperarm') && (n.includes('_r_') || n.includes('right')))
          child.rotation.set(0, 0, 1.3);

        // Hair physics bones
        if (n.includes('hair') || n.includes('sec_') || n.includes('secondary')) {
          hairRegistry.current.push({
            bone: child,
            initialX: child.rotation.x,
            initialZ: child.rotation.z,
          });
        }
      }

      if (child.isMesh && child.morphTargetDictionary && child.morphTargetInfluences)
        morphMeshes.current.push(child);
    });

    scene.position.set(0, 0, 0);
    scene.scale.set(0.9, 0.9, 0.9);
    scene.rotation.set(0, 0, 0);
    basePoseRef.current = { y: -0.85, rotY: 0 };
  }, [scene]);

  useFrame((state, delta) => {
    const time = state.clock.getElapsedTime();
    const currentExp = expression || 'neutral';

    /* ── 0. Breathing + micro-sway ─────────────────────── */
    if (groupRef.current) {
      const breath = Math.sin(time * 1.25) * 0.012;
      const sway = Math.sin(time * 0.6) * 0.015;
      groupRef.current.position.y = basePoseRef.current.y + breath;
      groupRef.current.rotation.y = basePoseRef.current.rotY + sway;
    }

    /* ── 1. Cursor-aware look-at (full window) ────────── */
    if (mousePos) {
      // mousePos is { x: -1..1, y: -1..1 } relative to full viewport
      const mx = mousePos.x ?? 0;
      const my = mousePos.y ?? 0;

      // Desired world-space target that the character looks toward
      const desired = new THREE.Vector3(mx * 2.5, my * 1.5 + 0.3, 3);
      // Smooth interpolation so the gaze feels natural
      smoothTarget.current.lerp(desired, 0.08);
      const target = smoothTarget.current;

      const applyLook = (bone, strength) => {
        if (!bone) return;
        const saved = bone.quaternion.clone();
        bone.lookAt(target);
        bone.quaternion.slerp(saved, 1 - strength);
      };

      applyLook(lookBones.current.spine, 0.06);
      applyLook(lookBones.current.neck, 0.14);
      applyLook(lookBones.current.head, 0.22);

      // Eye bones get extra weight so the gaze feels direct
      applyLook(lookBones.current.leftEye, 0.35);
      applyLook(lookBones.current.rightEye, 0.35);
    }

    /* ── 2. Hair wind simulation ──────────────────────── */
    const waveX = Math.sin(time * 2.0) * 0.04;
    const waveZ = Math.cos(time * 1.5) * 0.03;
    hairRegistry.current.forEach(({ bone, initialX, initialZ }) => {
      bone.rotation.x = initialX + waveX;
      bone.rotation.z = initialZ + waveZ;
    });

    /* ── 3. Blink (with occasional double-blinks) ────── */
    blinkTimer.current += delta;
    let blinkValue = 0;

    if (blinkTimer.current >= nextBlinkTime.current) {
      const elapsed = blinkTimer.current - nextBlinkTime.current;

      // First blink
      if (elapsed <= blinkDuration) {
        blinkValue = Math.sin((elapsed / blinkDuration) * Math.PI);
      }
      // Optional double-blink
      else if (doDoubleBlink.current && elapsed > blinkDuration + doubleBlinkGap && elapsed <= blinkDuration * 2 + doubleBlinkGap) {
        const p2 = elapsed - blinkDuration - doubleBlinkGap;
        blinkValue = Math.sin((p2 / blinkDuration) * Math.PI);
      }
      // Reset
      else if (elapsed > blinkDuration * 2 + doubleBlinkGap + 0.05) {
        blinkTimer.current = 0;
        nextBlinkTime.current = 2.0 + Math.random() * 4.0;
        doDoubleBlink.current = Math.random() < 0.25; // 25% chance of double-blink
      }
    }

    /* ── 4. Expression + lip-sync morph mixer ─────────── */
    morphMeshes.current.forEach((mesh) => {
      const dict = mesh.morphTargetDictionary;
      const influences = mesh.morphTargetInfluences;

      Object.keys(dict).forEach((key) => {
        const idx = dict[key];
        const k = key.toLowerCase();
        let target = 0;

        // Blink
        if (k.includes('blink') || k.includes('eye_close') || k.includes('eyesclosed')) {
          influences[idx] = blinkValue;
          return;
        }

        // Smiling
        if (currentExp === 'smiling' || currentExp === 'happy') {
          if (k.includes('joy') || k.includes('fun') || k.includes('smile') || k.includes('happy') || k.includes('mth_up'))
            target = 0.85;
        }

        // Sad
        if (currentExp === 'sad') {
          if (k.includes('sorrow') || k.includes('sad') || k.includes('frown') || k.includes('mth_down'))
            target = 0.75;
        }

        // Angry
        if (currentExp === 'angry') {
          if (k.includes('angry') || k.includes('rage') || k.includes('irate'))
            target = 0.8;
        }

        // Shy
        if (currentExp === 'shy') {
          if (k.includes('shy') || k.includes('sorrow') || k.includes('sad'))
            target = 0.45;
          if (k.includes('smile') || k.includes('joy'))
            target = 0.3; // shy smile
        }

        // Lip-sync
        if (isTalking) {
          if (k.includes('mth_a') || k === 'a' || k === 'aa' || k.includes('mouth_a') || k.includes('jaw_open') || k.includes('viseme_aa')) {
            const lipAnim = Math.abs(Math.sin(time * 14.0)) * 0.5 + Math.abs(Math.cos(time * 9.0)) * 0.15;
            target = Math.max(target, lipAnim);
          }
          // Add subtle 'O' and 'E' mouth shapes for more natural speech
          if (k.includes('mth_o') || k.includes('mouth_o') || k.includes('viseme_oh')) {
            target = Math.max(target, Math.abs(Math.cos(time * 11.0)) * 0.3);
          }
          if (k.includes('mth_e') || k.includes('mouth_e') || k.includes('viseme_ee')) {
            target = Math.max(target, Math.abs(Math.sin(time * 7.5)) * 0.2);
          }
        }

        influences[idx] = THREE.MathUtils.lerp(influences[idx], target, 0.18);
      });
    });
  });

  return <primitive ref={groupRef} object={scene} />;
}

useGLTF.preload('/avatar.glb');