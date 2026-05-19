import { Canvas } from '@react-three/fiber'
import { Suspense } from 'react'
import AmbientNetField from '../r3f/AmbientNetField'
import { useDarkMode } from '../../hooks/useDarkMode'

/**
 * Subtle Three.js layer behind app content (matches landing aesthetic, lower density).
 */
export default function WorkspaceAmbient() {
  const { dark } = useDarkMode()

  return (
    <div className="workspace-ambient" aria-hidden>
      <Canvas
        key={dark ? 'd' : 'l'}
        camera={{ position: [0, 0, 9.5], fov: 50 }}
        dpr={[1, 1.35]}
        gl={{ alpha: true, antialias: true, powerPreference: 'low-power' }}
        style={{ width: '100%', height: '100%', display: 'block' }}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={dark ? 0.5 : 0.8} />
          <AmbientNetField
            dark={dark}
            count={110}
            maxDist={2.45}
            maxLineFloats={540}
            seed={0x51d15c00}
            rotationY={0.042}
            wobbleAmp={0.055}
            wobbleFreq={0.09}
            pointSize={dark ? 0.075 : 0.07}
            pointOpacity={dark ? 0.55 : 0.45}
            lineOpacity={dark ? 0.14 : 0.18}
            spread={13}
          />
        </Suspense>
      </Canvas>
    </div>
  )
}
