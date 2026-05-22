import { useCallback, useMemo } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { LOGIN_DEPENDENCY_GRAPH } from '../../lib/dependencyGraph'

function RootNode({ data }) {
  return (
    <div className="hx-dep-node hx-dep-node--root">
      <strong>{data.label}</strong>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}

function ServiceNode({ data }) {
  return (
    <div className="hx-dep-node hx-dep-node--service">
      <Handle type="target" position={Position.Top} />
      <span>{data.label}</span>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}

function DataNode({ data }) {
  return (
    <div className="hx-dep-node hx-dep-node--data">
      <Handle type="target" position={Position.Top} />
      <span>{data.label}</span>
    </div>
  )
}

const nodeTypes = {
  root: RootNode,
  service: ServiceNode,
  data: DataNode,
}

export default function DependencyGraphFlow({
  graph = LOGIN_DEPENDENCY_GRAPH,
  height = 280,
}) {
  const nodes = useMemo(() => graph.nodes || [], [graph.nodes])
  const edges = useMemo(() => graph.edges || [], [graph.edges])

  const onInit = useCallback((instance) => {
    window.setTimeout(() => instance.fitView({ padding: 0.35 }), 80)
  }, [])

  return (
    <div className="hx-dep-flow glass-panel" style={{ height }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onInit={onInit}
        fitView
        proOptions={{ hideAttribution: true }}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        panOnScroll
        zoomOnScroll
      >
        <Background gap={20} size={1} color="rgba(148, 163, 184, 0.15)" />
        <Controls showInteractive={false} className="hx-dep-controls" />
        <MiniMap
          className="hx-dep-minimap"
          nodeColor={(n) =>
            n.type === 'root' ? '#6366f1' : n.type === 'data' ? '#22c55e' : '#0ea5e9'
          }
          maskColor="rgba(2, 6, 23, 0.75)"
        />
      </ReactFlow>
      <pre className="hx-dep-ascii muted small" aria-hidden>
        {`Login\n ├── Auth API\n ├── User DB\n └── JWT Service`}
      </pre>
    </div>
  )
}
