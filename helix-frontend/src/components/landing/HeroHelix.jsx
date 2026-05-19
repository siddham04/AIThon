import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

function createHelixPoints(turns = 5, segments = 200, radius = 1.4, height = 3.2, offset = 0) {
  const positions = []
  for (let i = 0; i < segments; i += 1) {
    const t = (i / (segments - 1)) * Math.PI * 2 * turns
    const x = Math.cos(t + offset) * radius
    const y = (i / (segments - 1) - 0.5) * height
    const z = Math.sin(t + offset) * radius
    positions.push(new THREE.Vector3(x, y, z))
  }
  return positions
}

function createNodes(points, count = 18) {
  const positions = new Float32Array(count * 3)
  const step = Math.max(1, Math.floor(points.length / count))
  let index = 0
  for (let i = 0; i < points.length; i += step) {
    positions[index++] = points[i].x
    positions[index++] = points[i].y
    positions[index++] = points[i].z
  }
  return positions
}

export default function HeroHelix({ dark = false }) {
  const group = useRef()
  const helixA = useMemo(() => createHelixPoints(5, 240, 1.35, 4.8, 0), [])
  const helixB = useMemo(() => createHelixPoints(5, 240, 1.35, 4.8, Math.PI), [])
  const nodes = useMemo(() => createNodes(helixA, 26), [helixA])

  const lineGeometryA = useMemo(() => new THREE.BufferGeometry().setFromPoints(helixA), [helixA])
  const lineGeometryB = useMemo(() => new THREE.BufferGeometry().setFromPoints(helixB), [helixB])
  const nodeGeometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(nodes, 3))
    return geo
  }, [nodes])

  useFrame((state) => {
    const elapsed = state.clock.elapsedTime
    const g = group.current
    if (!g) return
    g.rotation.y = elapsed * 0.16
    g.rotation.x = Math.sin(elapsed * 0.28) * 0.08
    g.rotation.z = Math.sin(elapsed * 0.14) * 0.06
  })

  const lineColor = dark ? '#7dd3fc' : '#0ea5e9'
  const nodeColor = dark ? '#bef264' : '#60a5fa'

  return (
    <group ref={group}>
      <line geometry={lineGeometryA}>
        <lineBasicMaterial color={lineColor} linewidth={2} transparent opacity={0.8} />
      </line>
      <line geometry={lineGeometryB}>
        <lineBasicMaterial color={lineColor} linewidth={2} transparent opacity={0.55} />
      </line>
      <points geometry={nodeGeometry}>
        <pointsMaterial color={nodeColor} size={0.08} sizeAttenuation transparent opacity={0.92} />
      </points>
      <mesh position={[0, 0, 0]}>
        <sphereGeometry args={[0.26, 28, 28]} />
        <meshStandardMaterial color={lineColor} emissive={lineColor} emissiveIntensity={0.65} roughness={0.15} metalness={0.5} />
      </mesh>
    </group>
  )
}
