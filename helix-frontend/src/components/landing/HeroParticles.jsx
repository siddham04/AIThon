import { Canvas } from '@react-three/fiber'
import { Suspense } from 'react'
import AmbientNetField from '../r3f/AmbientNetField'

export default function HeroParticles({ dark = false }) {
  const bg = dark ? '#020617' : '#f0f9ff'
  const fogColor = dark ? '#020617' : '#e0f2fe'
  return (
    <div className="hero-canvas">
      <Canvas camera={{ position: [0, 0, 10], fov: 50 }} key={dark ? 'd' : 'l'}>
        <color attach="background" args={[bg]} />
        <ambientLight intensity={dark ? 0.55 : 0.85} />
        <Suspense fallback={null}>
          <AmbientNetField
            dark={dark}
            count={200}
            maxDist={2.3}
            maxLineFloats={900}
            seed={0xcafebabe}
            rotationY={0.055}
            wobbleAmp={0.07}
            wobbleFreq={0.1}
          />
        </Suspense>
        <fog attach="fog" args={[fogColor, 8, 22]} />
      </Canvas>
    </div>
  )
}
