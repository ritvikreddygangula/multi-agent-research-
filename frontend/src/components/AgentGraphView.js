import React, { useMemo, useCallback } from 'react';
import ReactFlow, {
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import './AgentGraphView.css';

// ── Status colours ─────────────────────────────────────────────────────────

const STATUS_STYLE = {
  pending: { border: '#2a1818', bg: '#100a0a', text: '#5a4040', glow: 'none' },
  running: { border: '#f87171', bg: '#1f0d0d', text: '#fca5a5', glow: '0 0 14px rgba(248,113,113,0.3)' },
  done:    { border: '#4ade80', bg: '#0a1a0e', text: '#4ade80', glow: '0 0 10px rgba(74,222,128,0.25)' },
  failed:  { border: '#f87171', bg: '#1a0808', text: '#f87171', glow: '0 0 10px rgba(248,113,113,0.3)' },
  retry:   { border: '#fb923c', bg: '#1a0f08', text: '#fb923c', glow: '0 0 10px rgba(251,146,60,0.25)' },
};

// ── Custom node ────────────────────────────────────────────────────────────

function AgentNode({ data }) {
  const s = STATUS_STYLE[data.status] || STATUS_STYLE.pending;
  const isRunning = data.status === 'running';

  return (
    <div
      className={`ag-node${isRunning ? ' ag-node--running' : ''}`}
      style={{ borderColor: s.border, background: s.bg, boxShadow: s.glow }}
    >
      <Handle type="target" position={Position.Top} className="ag-handle" />
      <span className="ag-node__label" style={{ color: s.text }}>{data.label}</span>
      {isRunning && <span className="ag-node__pulse" />}
      <Handle type="source" position={Position.Bottom} className="ag-handle" />
    </div>
  );
}

const NODE_TYPES = { agentNode: AgentNode };

// ── Layout constants ───────────────────────────────────────────────────────

const NODE_DEFS = [
  { id: 'planner',       label: 'Planner',      x: 340, y: 0   },
  { id: 'rag_retrieval', label: 'RAG Memory',   x: 340, y: 100 },
  { id: 'branch_0',      label: 'Branch 1',     x: 0,   y: 220 },
  { id: 'branch_1',      label: 'Branch 2',     x: 170, y: 220 },
  { id: 'branch_2',      label: 'Branch 3',     x: 340, y: 220 },
  { id: 'branch_3',      label: 'Branch 4',     x: 510, y: 220 },
  { id: 'branch_4',      label: 'Branch 5',     x: 680, y: 220 },
  { id: 'aggregator',    label: 'Aggregator',   x: 340, y: 340 },
  { id: 'critic',        label: 'Critic',       x: 340, y: 440 },
  { id: 'synthesizer',   label: 'Synthesizer',  x: 340, y: 540 },
];

const EDGES = [
  { id: 'e-pl-rag',  source: 'planner',      target: 'rag_retrieval' },
  { id: 'e-rag-b0',  source: 'rag_retrieval', target: 'branch_0' },
  { id: 'e-rag-b1',  source: 'rag_retrieval', target: 'branch_1' },
  { id: 'e-rag-b2',  source: 'rag_retrieval', target: 'branch_2' },
  { id: 'e-rag-b3',  source: 'rag_retrieval', target: 'branch_3' },
  { id: 'e-rag-b4',  source: 'rag_retrieval', target: 'branch_4' },
  { id: 'e-b0-agg',  source: 'branch_0',      target: 'aggregator' },
  { id: 'e-b1-agg',  source: 'branch_1',      target: 'aggregator' },
  { id: 'e-b2-agg',  source: 'branch_2',      target: 'aggregator' },
  { id: 'e-b3-agg',  source: 'branch_3',      target: 'aggregator' },
  { id: 'e-b4-agg',  source: 'branch_4',      target: 'aggregator' },
  { id: 'e-agg-cri', source: 'aggregator',    target: 'critic' },
  { id: 'e-cri-syn', source: 'critic',        target: 'synthesizer' },
  {
    id: 'e-cri-agg-retry',
    source: 'critic', target: 'aggregator',
    style: { stroke: '#fb923c', strokeDasharray: '5 4' },
    label: 'retry', labelStyle: { fill: '#fb923c', fontSize: 10 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#fb923c' },
  },
];

// ── Main component ─────────────────────────────────────────────────────────

function makeNodes(nodeStatuses) {
  return NODE_DEFS.map(def => ({
    id: def.id,
    type: 'agentNode',
    position: { x: def.x, y: def.y },
    data: {
      label: def.label,
      status: nodeStatuses[def.id] || 'pending',
    },
  }));
}

function makeEdges(nodeStatuses) {
  return EDGES.map(e => {
    const srcDone = nodeStatuses[e.source] === 'done';
    const defaultColor = srcDone ? '#4a2a2a' : '#2a1818';
    return {
      ...e,
      style: e.style || { stroke: defaultColor, strokeWidth: 1.5 },
      markerEnd: e.markerEnd || { type: MarkerType.ArrowClosed, color: defaultColor },
      animated: nodeStatuses[e.source] === 'running',
    };
  });
}

const AgentGraphView = ({ nodeStatuses = {}, progress = 0, currentMessage = '' }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState(makeNodes(nodeStatuses));
  const [edges, setEdges, onEdgesChange] = useEdgesState(makeEdges(nodeStatuses));

  // Sync node/edge state whenever nodeStatuses changes
  React.useEffect(() => {
    setNodes(makeNodes(nodeStatuses));
    setEdges(makeEdges(nodeStatuses));
  }, [nodeStatuses, setNodes, setEdges]);

  const onInit = useCallback(instance => instance.fitView({ padding: 0.15 }), []);

  return (
    <div className="ag-wrap">
      <div className="ag-header">
        <div className="ag-progress-bar">
          <div className="ag-progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <span className="ag-message">{currentMessage}</span>
      </div>

      <div className="ag-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={NODE_TYPES}
          onInit={onInit}
          fitView
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          zoomOnScroll={false}
          panOnDrag={false}
        >
          <Background color="#1e1e2e" gap={20} size={1} />
        </ReactFlow>
      </div>

      <div className="ag-legend">
        {[['pending','#555','Waiting'],['running','#fbbf24','Running'],['done','#4ade80','Done'],['failed','#f87171','Failed']].map(([s,c,l]) => (
          <span key={s} className="ag-legend__item">
            <span className="ag-legend__dot" style={{ background: c }} />
            {l}
          </span>
        ))}
      </div>
    </div>
  );
};

export default AgentGraphView;
