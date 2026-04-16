"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, Float } from "@react-three/drei";
import { useRef } from "react";
import type { Mesh } from "three";

function OrbMesh() {
  const ref = useRef<Mesh>(null);

  useFrame((state) => {
    if (!ref.current) return;
    ref.current.rotation.y = state.clock.elapsedTime * 0.24;
    ref.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.3) * 0.18;
  });

  return (
    <Float speed={1.2} rotationIntensity={0.45} floatIntensity={0.8}>
      <mesh ref={ref} scale={1.35}>
        <icosahedronGeometry args={[1, 8]} />
        <meshPhysicalMaterial
          color="#ffffff"
          metalness={0.15}
          roughness={0.08}
          transmission={0.98}
          thickness={1.1}
          ior={1.18}
          transparent
          opacity={0.92}
          reflectivity={0.7}
        />
      </mesh>
    </Float>
  );
}

export function OrbSceneCanvas() {
  return (
    <div className="h-[320px] w-full" aria-hidden="true">
      <Canvas
        dpr={[1, 1.5]}
        camera={{ position: [0, 0, 4.8], fov: 34 }}
        gl={{ alpha: true, antialias: false, powerPreference: "low-power" }}
      >
        <color attach="background" args={["#000000"]} />
        <ambientLight intensity={0.7} />
        <directionalLight position={[5, 6, 8]} intensity={2.1} color="#ffe7d6" />
        <directionalLight position={[-4, -2, -6]} intensity={1.2} color="#83ffe0" />
        <OrbMesh />
        <Environment preset="studio" />
      </Canvas>
    </div>
  );
}
