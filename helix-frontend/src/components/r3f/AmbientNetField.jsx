import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

function mulberry32(seed) {
  return function rand() {
    let t = (seed += 0x6d2b79f5)
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/**
 * Shared point + proximity-line field (landing hero + workspace ambient).
 */
export default function AmbientNetField({
  dark = false,
  count = 160,
  maxDist = 2.35,
  maxLineFloats = 900,
  seed = 0xcafebabe,
  rotationY = 0.052,
  wobbleAmp = 0.07,
  wobbleFreq = 0.1,
  pointSize,
  pointOpacity,
  lineOpacity,
  spread = 14,
}) {
  const group = useRef()
  const { pointsGeo, linesGeo } = useMemo(() => {
    const rand = mulberry32(seed)
    const positions = new Float32Array(count * 3)
    const rnd = () => (rand() - 0.5) * spread
    for (let i = 0; i < count; i++) {
      positions[i * 3] = rnd()
      positions[i * 3 + 1] = rnd()
      positions[i * 3 + 2] = rnd()
    }
    const lineVerts = []
    for (let i = 0; i < count; i++) {
      const ix = i * 3
      for (let j = i + 1; j < count; j++) {
        const jx = j * 3
        const d = Math.hypot(
          positions[ix] - positions[jx],
          positions[ix + 1] - positions[jx + 1],
          positions[ix + 2] - positions[jx + 2],
        )
        if (d < maxDist && lineVerts.length < maxLineFloats) {
          lineVerts.push(
            positions[ix],
            positions[ix + 1],
            positions[ix + 2],
            positions[jx],
            positions[jx + 1],
            positions[jx + 2],
          )
        }
      }
    }
    const pg = new THREE.BufferGeometry()
    pg.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const lg = new THREE.BufferGeometry()
    lg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(lineVerts), 3))
    return { pointsGeo: pg, linesGeo: lg }
  }, [count, maxDist, maxLineFloats, seed, spread])

  useFrame((state) => {
    const g = group.current
    if (!g) return
    g.rotation.y = state.clock.elapsedTime * rotationY
    g.rotation.x = Math.sin(state.clock.elapsedTime * wobbleFreq) * wobbleAmp
  })

  const pSize = pointSize ?? (dark ? 0.09 : 0.085)
  const pOp = pointOpacity ?? (dark ? 0.9 : 0.75)
  const lOp = lineOpacity ?? (dark ? 0.2 : 0.28)
  const pointColor = dark ? '#7dd3fc' : '#0284c7'
  const lineColor = dark ? '#38bdf8' : '#0ea5e9'

  return (
    <group ref={group}>
      <points geometry={pointsGeo}>
        <pointsMaterial
          color={pointColor}
          size={pSize}
          sizeAttenuation
          transparent
          opacity={pOp}
          depthWrite={false}
        />
      </points>
      <lineSegments geometry={linesGeo}>
        <lineBasicMaterial color={lineColor} transparent opacity={lOp} depthWrite={false} />
      </lineSegments>
    </group>
  )
}
