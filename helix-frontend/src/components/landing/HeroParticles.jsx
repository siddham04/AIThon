import { Canvas } from '@react-three/fiber'
import { Suspense } from 'react'
import AmbientNetField from '../r3f/AmbientNetField'
import HeroHelix from './HeroHelix'

export default function HeroParticles({ dark = false }) {
  const bg = dark ? '#020617' : '#f8fbff'
  const fogColor = dark ? '#020617' : '#e0f2fe'
  return (
    <div className="hero-canvas">
      <Canvas camera={{ position: [0, 0, 10], fov: 52 }} key={dark ? 'd' : 'l'}>
        <color attach="background" args={[bg]} />
        <fog attach="fog" args={[fogColor, 8, 22]} />
        <ambientLight intensity={dark ? 0.45 : 0.75} />
        <pointLight position={[5, 5, 8]} intensity={1.1} color={dark ? '#7dd3fc' : '#3b82f6'} />
        <pointLight position={[-6, -4, 3]} intensity={0.7} color={dark ? '#84cc16' : '#38bdf8'} />
        <Suspense fallback={null}>
          <HeroHelix dark={dark} />
          <AmbientNetField
            dark={dark}
            count={220}
            maxDist={2.2}
            maxLineFloats={1100}
            seed={0xcafebabe}
            rotationY={0.045}
            wobbleAmp={0.08}
            wobbleFreq={0.12}
            spread={15}
          />
        </Suspense>
      </Canvas>
    </div>
  )
}
