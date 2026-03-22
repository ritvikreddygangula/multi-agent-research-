/**
 * AgentGraphView — live React Flow visualization of the LangGraph pipeline.
 *
 * Node status is driven by `nodeStatuses` prop (the `node_statuses` dict
 * streamed from the backend on every node_update SSE event).
 *
 * Status → colour mapping:
 *   pending  → #3a3a4a  (dark neutral)
 *   running  → #b45309  (amber, pulsing ring)
 *   done     → #166534  (green)
 *   failed   → #991b1b  (red)
 *   retry    → #7c3aed  (purple)
 */
import React, { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  Handle,
  Position,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import './AgentGraphView.css';

// ── Status helpers ────────────────────────────────────────────────────────────

const STATUS_COLOR = {
  pending: { bg: '#1e1e2e', border: '#3a3a5a', text: '#888' },
  running: { bg: '#2a1f00', border: '#b45309', text: '#fbbf24' },
  done:    { bg: '#052e16', border: '#166534', text: '#4ade80' },
  failed:  { bg: '#2d0a0a', border: '#991b1b', text: '#f87171' },
  retry:   { bg: '#2e1a4a', border: '#7c3aed', text: '#a78bfa' },
};

const STATUS_ICON = {
  pending: '○',
  running: '◎',
  done:    '✓',
  failed:  '✗',
  retry:   '↺',
};

const STATUS_LABEL = {
  pending: 'Waiting',
  running: 'Running',
  done:    'Done',
  failed:  'Failed',
  retry:   'Retry',
};

// ── Custom node component ─────────────────────────────────────────────────────

function AgentNode({ data }) {
  const { label, sublabel, status = 'pending', hasSource = true, hasTarget = true } = data;
  const colors = STATUS_COLOR[status] || STATUS_COLOR.pending;
  const isRunning = status === 'running';

  return (
    <div
      className={`agent-node ${isRunning ? 'agent-node--running' : ''}`}
      style={{ background: colors.bg, borderColor: colors.border }}
    >
      {hasTarget && <Handle type="target" position={Position.Top} />}
      <div className="agent-node__icon" style={{ color: colors.text }}>
        {STATUS_ICON[status] || '○'}
      </div>
      <div className="agent-node__body">
        <div className="agent-node__label" style={{ color: colors.text }}>{label}</div>
        {sublabel && <div className="agent-node__sub">{sublabel}</div>}
        <div className="agent-node__status" style={{ color: colors.border }}>
          {STATUS_LABEL[status] || 'Waiting'}
        </div>
      </div>
      {hasSource && <Handle type="source" position={Position.Bottom} />}
    </div>
  );
}

const nodeTypes = { agentNode: AgentNode };

// ── Static layout ─────────────────────────────────────────────────────────────
//
//  Topology (mirrors graph_builder.py):
//  START → planner → rag_retrieval → [branch_0..4] → aggregator → critic → synthesizer → END
//
//  X positions for 5 branches spread across 600 px, centred at x=400.
//  Y increases downward.

const COL   = 400;   // centre column x
const W_GAP = 130;   // horizontal gap between branch nodes
const Y = {
  planner:      80,
  rag:         200,
  branches:    340,
  aggregator:  480,
  critic:      600,
  synthesizer: 720,
};

function makeNodes(nodeStatuses) {
  const s = (id) => nodeStatuses[id] || 'pending';

  const branchXs = [-2, -1, 0, 1, 2].map((i) => COL + i * W_GAP);

  return [
    {
      id: 'planner',
      type: 'agentNode',
      position: { x: COL - 70, y: Y.planner },
      data: { label: 'Planner', sublabel: 'Decompose topic', status: s('planner'), hasTarget: false },
    },
    {
      id: 'rag_retrieval',
      type: 'agentNode',
      position: { x: COL - 70, y: Y.rag },
      data: { label: 'RAG Retrieval', sublabel: 'Pinecone memory', status: s('rag_retrieval') },
    },
    ...branchXs.map((x, i) => ({
      id: `branch_${i}`,
      type: 'agentNode',
      position: { x: x - 55, y: Y.branches },
      data: { label: `Branch ${i}`, sublabel: 'Sub-question', status: s(`branch_${i}`) },
    })),
    {
      id: 'aggregator',
      type: 'agentNode',
      position: { x: COL - 70, y: Y.aggregator },
      data: { label: 'Aggregator', sublabel: 'Fan-in & merge', status: s('aggregator') },
    },
    {
      id: 'critic',
      type: 'agentNode',
      position: { x: COL - 70, y: Y.critic },
      data: { label: 'Critic', sublabel: 'Quality gate', status: s('critic') },
    },
    {
      id: 'synthesizer',
      type: 'agentNode',
      position: { x: COL - 70, y: Y.synthesizer },
      data: { label: 'Synthesizer', sublabel: 'Final report', status: s('synthesizer'), hasSource: false },
    },
  ];
}

const EDGE_STYLE = { stroke: '#3a3a5a', strokeWidth: 1.5 };
const ANIMATED_STYLE = { stroke: '#b45309', strokeWidth: 2 };
const MARKER = { type: MarkerType.ArrowClosed, color: '#3a3a5a', width: 10, height: 10 };
const MARKER_ACTIVE = { type: MarkerType.ArrowClosed, color: '#b45309', width: 10, height: 10 };

function makeEdges(nodeStatuses) {
  const active = (id) => nodeStatuses[id] === 'running';

  const edgeBase = (id, source, target) => ({
    id,
    source,
    target,
    animated: active(target),
    style: active(target) ? ANIMATED_STYLE : EDGE_STYLE,
    markerEnd: active(target) ? MARKER_ACTIVE : MARKER,
  });

  return [
    edgeBase('e-p-r', 'planner', 'rag_retrieval'),
    ...Array.from({ length: 5 }, (_, i) =>
      edgeBase(`e-r-b${i}`, 'rag_retrieval', `branch_${i}`)
    ),
    ...Array.from({ length: 5 }, (_, i) =>
      edgeBase(`e-b${i}-a`, `branch_${i}`, 'aggregator')
    ),
    edgeBase('e-a-c', 'aggregator', 'critic'),
    edgeBase('e-c-s', 'critic', 'synthesizer'),
    // critic retry loop back to aggregator
    {
      id: 'e-c-retry',
      source: 'critic',
      target: 'aggregator',
      label: 'retry',
      labelStyle: { fill: '#a78bfa', fontSize: 10 },
      style: { stroke: '#7c3aed', strokeWidth: 1, strokeDasharray: '4 3' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#7c3aed', width: 8, height: 8 },
    },
  ];
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AgentGraphView({ nodeStatuses = {}, progress = 0, currentMessage = '' }) {
  const nodes = useMemo(() => makeNodes(nodeStatuses), [nodeStatuses]);
  const edges = useMemo(() => makeEdges(nodeStatuses), [nodeStatuses]);

  return (
    <div className="agent-graph-wrap">
      <div className="agent-graph-header">
        <span className="agent-graph-title">Live Agent Graph</span>
        <span className="agent-graph-progress">{progress}%</span>
      </div>

      {currentMessage && (
        <div className="agent-graph-message">{currentMessage}</div>
      )}

      <div className="agent-graph-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          panOnDrag={false}
          zoomOnScroll={false}
          zoomOnPinch={false}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#2a2a3a" gap={20} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>

      <div className="agent-graph-legend">
        {Object.entries(STATUS_COLOR).map(([s, c]) => (
          <span key={s} className="legend-item">
            <span className="legend-dot" style={{ background: c.border }} />
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}
