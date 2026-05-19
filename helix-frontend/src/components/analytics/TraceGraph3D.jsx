import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'

/** Node kinds shown in the 3D scene and sidebar legend */
const TRACE_NODE_SPECS = [
  { kind: 'req', label: 'Requirement', hint: 'Root — all artifacts trace here.' },
  { kind: 'story', label: 'Story', hint: 'User story derived from the requirement.' },
  { kind: 'task', label: 'Task', hint: 'Implementation work item.' },
  { kind: 'test', label: 'Test case', hint: 'Verification linked to scope.' },
]

const NODE_COLORS = {
  req: '#38bdf8',
  story: '#f472b6',
  task: '#a78bfa',
  test: '#34d399',
}

/** Edge kinds — line colors match legend */
const EDGE_SPECS = [
  {
    kind: 'req_story',
    label: 'Requirement → story',
    hint: 'Direct trace from source to story.',
  },
  {
    kind: 'req_task',
    label: 'Requirement → task',
    hint: 'Task anchored to requirement (includes orphan tasks).',
  },
  {
    kind: 'req_test',
    label: 'Requirement → test',
    hint: 'Test coverage tied to the requirement root.',
  },
  {
    kind: 'story_task',
    label: 'Story → task',
    hint: 'Decomposition: work under a story.',
  },
  {
    kind: 'task_test',
    label: 'Task → test',
    hint: 'Verification of a specific task.',
  },
]

function edgePalette(dark) {
  if (dark) {
    return {
      req_story: '#38bdf8',
      req_task: '#475569',
      req_test: '#64748b',
      story_task: '#c4b5fd',
      task_test: '#4ade80',
    }
  }
  return {
    req_story: '#0284c7',
    req_task: '#94a3b8',
    req_test: '#64748b',
    story_task: '#7c3aed',
    task_test: '#059669',
  }
}

function mulberry32(seed) {
  return function rand() {
    let t = (seed += 0x6d2b79f5)
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function useForceLayout(nodes, edgePairs) {
  const steps = 52
  return useMemo(() => {
    const n = nodes.length
    if (n === 0) return []
    const rand = mulberry32(0x9e3779b9 ^ (n * 9973) ^ edgePairs.length)
    const pos = nodes.map((_, i) => {
      const a = (i / n) * Math.PI * 2
      return new THREE.Vector3(Math.cos(a) * 4, Math.sin(a) * 2.2, Math.sin(a) * 1.5)
    })
    const jitter = () => (rand() - 0.5) * 0.018
    for (let s = 0; s < steps; s++) {
      for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
          if (i === j) continue
          const d = pos[i].clone().sub(pos[j])
          const len = d.length() + 0.1
          const rep = 0.36 / (len * len)
          d.normalize().multiplyScalar(rep)
          pos[i].add(d)
        }
      }
      for (const [a, b] of edgePairs) {
        if (a >= n || b >= n) continue
        const pa = pos[a]
        const pb = pos[b]
        const d = pb.clone().sub(pa)
        const len = d.length() + 0.01
        d.multiplyScalar(0.021 * (len - 2.15))
        pa.add(d)
        pb.sub(d)
      }
      for (const p of pos) {
        p.x += jitter()
        p.y += jitter()
        p.z += jitter()
      }
    }
    return pos
  }, [nodes, edgePairs])
}

function edgeOpacity(kind) {
  switch (kind) {
    case 'req_task':
      return 0.38
    case 'req_test':
      return 0.42
    case 'req_story':
      return 0.72
    case 'story_task':
      return 0.78
    case 'task_test':
      return 0.88
    default:
      return 0.5
  }
}

function EdgeLines({ positions, edgesOfKind, color, kind }) {
  const geom = useMemo(() => {
    if (!edgesOfKind.length) return null
    const lp = []
    for (const e of edgesOfKind) {
      const pa = positions[e.a]
      const pb = positions[e.b]
      if (!pa || !pb) continue
      lp.push(pa.x, pa.y, pa.z, pb.x, pb.y, pb.z)
    }
    if (lp.length === 0) return null
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(lp), 3))
    return g
  }, [positions, edgesOfKind])

  useEffect(() => () => geom?.dispose(), [geom])

  if (!edgesOfKind.length || !geom) return null

  return (
    <lineSegments geometry={geom}>
      <lineBasicMaterial
        color={color}
        transparent
        opacity={edgeOpacity(kind)}
        depthWrite={false}
      />
    </lineSegments>
  )
}

function GroundGrid({ dark }) {
  const major = dark ? '#334155' : '#cbd5e1'
  const minor = dark ? '#1e293b' : '#e2e8f0'
  const obj = useMemo(
    () => new THREE.GridHelper(26, 13, new THREE.Color(major), new THREE.Color(minor)),
    [major, minor],
  )
  return <primitive object={obj} position={[0, -2.85, 0]} />
}

function Scene({
  nodes,
  typedEdges,
  dark,
  hoveredId,
  selectedId,
  onHoverNode,
  onPickNode,
  gentleSpin,
}) {
  const group = useRef()
  const edgePairs = useMemo(() => typedEdges.map((e) => [e.a, e.b]), [typedEdges])
  const positions = useForceLayout(nodes, edgePairs)
  const colors = NODE_COLORS
  const emissive = dark ? '#0f172a' : '#e2e8f0'
  const epal = edgePalette(dark)

  const edgesByKind = useMemo(() => {
    const m = {}
    for (const k of EDGE_SPECS) m[k.kind] = []
    for (const e of typedEdges) {
      if (m[e.kind]) m[e.kind].push(e)
    }
    return m
  }, [typedEdges])

  useFrame((st) => {
    if (group.current && gentleSpin) {
      group.current.rotation.y = st.clock.elapsedTime * 0.12
    }
  })

  const sphereData = useMemo(
    () => nodes.map((n, i) => ({ ...n, p: positions[i] })),
    [nodes, positions],
  )

  return (
    <group ref={group}>
      <GroundGrid dark={dark} />
      {EDGE_SPECS.map(({ kind }) => (
        <EdgeLines
          key={kind}
          kind={kind}
          positions={positions}
          edgesOfKind={edgesByKind[kind] || []}
          color={epal[kind] || '#94a3b8'}
        />
      ))}
      {sphereData.map((n) => {
        const selected = n.id === selectedId
        const hover = n.id === hoveredId
        const scale = selected ? 1.28 : hover ? 1.12 : 1
        const radius = n.kind === 'req' ? 0.34 : 0.2
        return (
          <mesh
            key={n.id}
            position={n.p}
            scale={scale}
            userData={{ nodeId: n.id }}
            onPointerOver={(e) => {
              e.stopPropagation()
              onHoverNode(n)
            }}
            onPointerOut={(e) => {
              e.stopPropagation()
              onHoverNode(null)
            }}
            onClick={(e) => {
              e.stopPropagation()
              onPickNode(n)
            }}
          >
            <sphereGeometry args={[radius, 22, 22]} />
            <meshStandardMaterial
              color={colors[n.kind] || '#94a3b8'}
              emissive={emissive}
              emissiveIntensity={selected ? 0.45 : hover ? 0.22 : 0.08}
              metalness={0.15}
              roughness={0.55}
            />
          </mesh>
        )
      })}
      <ambientLight intensity={0.62} />
      <directionalLight position={[8, 10, 6]} intensity={0.85} castShadow={false} />
      <directionalLight position={[-6, 4, -8]} intensity={0.35} color="#a5b4fc" />
      <pointLight position={[0, 6, 0]} intensity={0.25} />
    </group>
  )
}

function buildGraph(stories, tasks, testcases) {
  const nodes = [{ id: 'req', label: 'Requirement', kind: 'req' }]
  const idToIndex = { req: 0 }
  for (const s of stories || []) {
    idToIndex[s.id] = nodes.length
    nodes.push({ id: s.id, label: s.title || s.id, kind: 'story' })
  }
  for (const t of tasks || []) {
    idToIndex[t.id] = nodes.length
    nodes.push({ id: t.id, label: t.title || t.id, kind: 'task' })
  }
  for (const tc of testcases || []) {
    idToIndex[tc.id] = nodes.length
    nodes.push({ id: tc.id, label: tc.title || tc.id, kind: 'test' })
  }

  const typedEdges = []
  for (const s of stories || []) {
    const si = idToIndex[s.id]
    if (si != null) typedEdges.push({ a: 0, b: si, kind: 'req_story' })
  }
  for (const t of tasks || []) {
    const ti = idToIndex[t.id]
    if (ti == null) continue
    typedEdges.push({ a: 0, b: ti, kind: 'req_task' })
    if (t.story_id && idToIndex[t.story_id] != null) {
      typedEdges.push({ a: idToIndex[t.story_id], b: ti, kind: 'story_task' })
    }
  }
  for (const tc of testcases || []) {
    const ti = idToIndex[tc.id]
    if (ti == null) continue
    typedEdges.push({ a: 0, b: ti, kind: 'req_test' })
    const tid = tc.extra?.task_id ?? tc.task_id
    if (tid && idToIndex[tid] != null) {
      typedEdges.push({ a: idToIndex[tid], b: ti, kind: 'task_test' })
    }
  }

  return { nodes, typedEdges }
}

function NodeInspector({ node, tasks, testcases, stories }) {
  if (!node) {
    return (
      <p className="muted small graph-inspector-empty">
        Hover a node for a quick summary, or click to pin details. Drag to orbit, scroll to zoom.
      </p>
    )
  }
  const rows = []
  if (node.kind === 'task') {
    const t = (tasks || []).find((x) => x.id === node.id)
    if (t) {
      if (t.priority) rows.push(['Priority', String(t.priority)])
      if (t.type) rows.push(['Type', String(t.type)])
      if (t.estimate_points != null) rows.push(['Points', String(t.estimate_points)])
      if (t.confidence != null && t.confidence !== '')
        rows.push(['Confidence', `${Math.round(Number(t.confidence) * 100)}%`])
      if (t.story_id) rows.push(['Story id', t.story_id])
    }
  }
  if (node.kind === 'story') {
    const s = (stories || []).find((x) => x.id === node.id)
    if (s?.approved_for_export != null)
      rows.push(['Export approved', s.approved_for_export ? 'yes' : 'no'])
  }
  if (node.kind === 'test') {
    const tc = (testcases || []).find((x) => x.id === node.id)
    if (tc) {
      const tid = tc.extra?.task_id ?? tc.task_id
      if (tid) rows.push(['Linked task', tid])
    }
  }

  const spec = TRACE_NODE_SPECS.find((s) => s.kind === node.kind)

  return (
    <div className="graph-inspector">
      <div className={`graph-inspector-kind kind-${node.kind}`}>{spec?.label || node.kind}</div>
      <div className="graph-inspector-title">{node.label}</div>
      {rows.length > 0 && (
        <dl className="graph-inspector-dl">
          {rows.map(([k, v]) => (
            <div key={k} className="graph-inspector-row">
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  )
}

export default function TraceGraph3D({ stories, tasks, testcases, dark = false }) {
  const [hovered, setHovered] = useState(null)
  const [selected, setSelected] = useState(null)
  const [gentleSpin, setGentleSpin] = useState(false)
  const [resetKey, setResetKey] = useState(0)

  const { nodes, typedEdges } = useMemo(
    () => buildGraph(stories, tasks, testcases),
    [stories, tasks, testcases],
  )

  const stats = useMemo(() => {
    const byKind = { req: 0, story: 0, task: 0, test: 0 }
    for (const n of nodes) byKind[n.kind] += 1
    const byEdgeKind = {}
    for (const k of EDGE_SPECS) byEdgeKind[k.kind] = 0
    for (const e of typedEdges) byEdgeKind[e.kind] = (byEdgeKind[e.kind] || 0) + 1
    return { byKind, byEdgeKind, edgeCount: typedEdges.length }
  }, [nodes, typedEdges])

  const activeNode = selected || hovered

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') setSelected(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const onHoverNode = useCallback((n) => {
    setHovered(n)
  }, [])

  const onPickNode = useCallback((n) => {
    setSelected((prev) => (prev?.id === n.id ? null : n))
  }, [])

  if (nodes.length < 2) {
    return (
      <div className="graph-placeholder muted">
        Add stories, tasks, and tests to see the traceability graph.
      </div>
    )
  }

  const bg = dark ? '#0f172a' : '#f1f5f9'
  const large = nodes.length > 120

  return (
    <div className="trace-graph-shell">
      <div className="trace-graph-toolbar">
        <div className="trace-graph-stats" aria-label="Graph statistics">
          <span>
            <strong>{stats.byKind.story}</strong> stories
          </span>
          <span className="dot" aria-hidden>
            ·
          </span>
          <span>
            <strong>{stats.byKind.task}</strong> tasks
          </span>
          <span className="dot" aria-hidden>
            ·
          </span>
          <span>
            <strong>{stats.byKind.test}</strong> tests
          </span>
          <span className="dot" aria-hidden>
            ·
          </span>
          <span>
            <strong>{stats.edgeCount}</strong> edges
          </span>
        </div>
        <div className="trace-graph-actions">
          <label className="trace-graph-toggle">
            <input
              type="checkbox"
              checked={gentleSpin}
              onChange={(e) => setGentleSpin(e.target.checked)}
            />
            Gentle spin
          </label>
          <button
            type="button"
            className="btn ghost small"
            onClick={() => {
              setResetKey((k) => k + 1)
              setSelected(null)
            }}
          >
            Reset camera
          </button>
        </div>
      </div>

      {large && (
        <p className="trace-graph-warning muted small">
          Large graph ({nodes.length} nodes) — use zoom and hide spin for smoother interaction.
        </p>
      )}

      <div className="trace-graph-body">
        <div
          className="graph-canvas trace-graph-canvas"
          role="img"
          aria-label="Interactive three dimensional traceability graph. Use mouse to rotate and zoom."
        >
          <Suspense fallback={<div className="graph-canvas-loading muted">Loading WebGL scene…</div>}>
            <Canvas
              key={`${dark ? 'd' : 'l'}-${resetKey}`}
              camera={{ position: [0, 1.2, 9.2], fov: 48 }}
              dpr={[1, 2]}
              gl={{ antialias: true, alpha: false, powerPreference: 'high-performance' }}
            >
              <color attach="background" args={[bg]} />
              <OrbitControls
                makeDefault
                enablePan
                enableZoom
                minDistance={3.5}
                maxDistance={22}
                maxPolarAngle={Math.PI * 0.92}
                enableDamping
                dampingFactor={0.08}
                rotateSpeed={0.65}
                zoomSpeed={0.85}
              />
              <Scene
                nodes={nodes}
                typedEdges={typedEdges}
                dark={dark}
                hoveredId={hovered?.id}
                selectedId={selected?.id}
                onHoverNode={onHoverNode}
                onPickNode={onPickNode}
                gentleSpin={gentleSpin}
              />
            </Canvas>
          </Suspense>
        </div>

        <aside className="trace-graph-sidebar" aria-label="Graph legend and inspector">
          <section className="trace-legend-block">
            <h4 className="trace-legend-heading">Nodes</h4>
            <ul className="trace-legend-list">
              {TRACE_NODE_SPECS.map((s) => (
                <li key={s.kind} className="trace-legend-item">
                  <span className="trace-legend-swatch" style={{ background: NODE_COLORS[s.kind] }} />
                  <span className="trace-legend-label">{s.label}</span>
                  <span className="trace-legend-count">{stats.byKind[s.kind] ?? 0}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="trace-legend-block">
            <h4 className="trace-legend-heading">Edges</h4>
            <ul className="trace-legend-list trace-legend-edges">
              {EDGE_SPECS.map((s) => {
                const c = edgePalette(dark)[s.kind]
                return (
                  <li key={s.kind} className="trace-legend-item trace-legend-edge-row">
                    <span className="trace-legend-line" style={{ background: c }} />
                    <span className="trace-legend-text">
                      <span className="trace-legend-label">{s.label}</span>
                      <span className="muted trace-legend-hint">{s.hint}</span>
                    </span>
                    <span className="trace-legend-count">{stats.byEdgeKind[s.kind] ?? 0}</span>
                  </li>
                )
              })}
            </ul>
          </section>

          <section className="trace-legend-block trace-inspector-section">
            <h4 className="trace-legend-heading">{selected ? 'Pinned node' : 'Inspector'}</h4>
            <NodeInspector
              node={activeNode}
              tasks={tasks}
              testcases={testcases}
              stories={stories}
            />
            {selected && (
              <button type="button" className="linkish" onClick={() => setSelected(null)}>
                Clear selection (Esc)
              </button>
            )}
          </section>
        </aside>
      </div>
    </div>
  )
}
