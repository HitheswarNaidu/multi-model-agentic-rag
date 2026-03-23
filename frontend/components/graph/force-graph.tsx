"use client";

import { useRef, useEffect, useCallback, useState } from "react";
import type { GraphNode, GraphEdge } from "./node-inspector";

interface SimNode extends GraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface ForceGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  nodeCap: number;
  selectedNodeId: string | null;
  onSelectNode: (node: GraphNode | null) => void;
}

const DOC_COLOR = "#6c9bd2";
const CHUNK_COLOR = "#f4a261";
const SELECTED_COLOR = "#E8590C";
const EDGE_COLOR = "rgba(255,255,255,0.06)";
const BG_COLOR = "#1A1A1A";

export function ForceGraph({
  nodes,
  edges,
  nodeCap,
  selectedNodeId,
  onSelectNode,
}: ForceGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const simNodesRef = useRef<SimNode[]>([]);
  const edgesRef = useRef<GraphEdge[]>([]);
  const animFrameRef = useRef<number>(0);
  const iterationRef = useRef(0);
  const selectedRef = useRef<string | null>(selectedNodeId);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Keep selectedRef in sync
  useEffect(() => {
    selectedRef.current = selectedNodeId;
  }, [selectedNodeId]);

  // Observe container resize
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          setDimensions({ width: Math.floor(width), height: Math.floor(height) });
        }
      }
    });
    ro.observe(container);
    return () => ro.disconnect();
  }, []);

  // Initialize simulation nodes when data or cap changes
  useEffect(() => {
    const cappedNodes = nodes.slice(0, nodeCap);
    const nodeIds = new Set(cappedNodes.map((n) => n.id));
    const cappedEdges = edges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
    );

    const cx = dimensions.width / 2;
    const cy = dimensions.height / 2;
    const spread = Math.min(dimensions.width, dimensions.height) * 0.35;

    const simNodes: SimNode[] = cappedNodes.map((n) => ({
      ...n,
      x: cx + (Math.random() - 0.5) * spread,
      y: cy + (Math.random() - 0.5) * spread,
      vx: 0,
      vy: 0,
    }));

    simNodesRef.current = simNodes;
    edgesRef.current = cappedEdges;
    iterationRef.current = 0;
  }, [nodes, edges, nodeCap, dimensions.width, dimensions.height]);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let running = true;

    function tick() {
      if (!running || !ctx) return;

      const simNodes = simNodesRef.current;
      const simEdges = edgesRef.current;
      const iteration = iterationRef.current;

      // Only run physics for first ~300 iterations (then just render)
      if (iteration < 300) {
        runPhysics(simNodes, simEdges, dimensions.width, dimensions.height, iteration);
        iterationRef.current++;
      }

      // Draw
      draw(ctx, simNodes, simEdges, dimensions.width, dimensions.height, selectedRef.current);

      animFrameRef.current = requestAnimationFrame(tick);
    }

    tick();

    return () => {
      running = false;
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [dimensions.width, dimensions.height]);

  // Click handler
  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      const mx = (e.clientX - rect.left) * scaleX;
      const my = (e.clientY - rect.top) * scaleY;

      const simNodes = simNodesRef.current;
      let closest: SimNode | null = null;
      let closestDist = Infinity;

      for (const node of simNodes) {
        const r = node.type === "document" ? 8 : 5;
        const dx = node.x - mx;
        const dy = node.y - my;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < r + 4 && dist < closestDist) {
          closest = node;
          closestDist = dist;
        }
      }

      if (closest) {
        onSelectNode(closest);
      } else {
        onSelectNode(null);
      }
    },
    [onSelectNode]
  );

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full overflow-hidden rounded-xl border border-border bg-[#1A1A1A]"
    >
      <canvas
        ref={canvasRef}
        width={dimensions.width}
        height={dimensions.height}
        onClick={handleClick}
        className="h-full w-full cursor-crosshair"
        style={{ display: "block" }}
      />
      {simNodesRef.current.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="text-sm text-muted-foreground">No graph data</p>
        </div>
      )}
    </div>
  );
}

function runPhysics(
  nodes: SimNode[],
  edges: GraphEdge[],
  width: number,
  height: number,
  iteration: number
) {
  if (!nodes || !edges) return;
  const n = nodes.length;
  if (n === 0) return;

  // Cooling factor
  const alpha = Math.max(0.001, 1 - iteration / 300);
  const repulsionStrength = 800 * alpha;
  const attractionStrength = 0.005 * alpha;
  const centerPull = 0.01 * alpha;
  const damping = 0.85;
  const maxVelocity = 8;

  const cx = width / 2;
  const cy = height / 2;

  // Build node index for edge lookups
  const nodeIndex = new Map<string, number>();
  for (let i = 0; i < n; i++) {
    nodeIndex.set(nodes[i].id, i);
  }

  // Repulsion (Barnes-Hut-like approximation for large graphs: only check nearby)
  for (let i = 0; i < n; i++) {
    const ni = nodes[i];

    // Center gravity
    ni.vx += (cx - ni.x) * centerPull;
    ni.vy += (cy - ni.y) * centerPull;

    // Repulsion from other nodes (skip distant for perf when n > 200)
    const checkLimit = n > 200 ? Math.min(n, 100) : n;
    const step = Math.max(1, Math.floor(n / checkLimit));

    for (let j = 0; j < n; j += step) {
      if (i === j) continue;
      const nj = nodes[j];
      let dx = ni.x - nj.x;
      let dy = ni.y - nj.y;
      let distSq = dx * dx + dy * dy;
      if (distSq < 1) distSq = 1;
      if (distSq > 40000) continue; // skip very distant nodes

      const force = repulsionStrength / distSq;
      const dist = Math.sqrt(distSq);
      ni.vx += (dx / dist) * force;
      ni.vy += (dy / dist) * force;
    }
  }

  // Attraction along edges
  for (const edge of edges) {
    const si = nodeIndex.get(edge.source);
    const ti = nodeIndex.get(edge.target);
    if (si === undefined || ti === undefined) continue;

    const s = nodes[si];
    const t = nodes[ti];
    const dx = t.x - s.x;
    const dy = t.y - s.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 1) continue;

    const force = dist * attractionStrength;
    const fx = (dx / dist) * force;
    const fy = (dy / dist) * force;

    s.vx += fx;
    s.vy += fy;
    t.vx -= fx;
    t.vy -= fy;
  }

  // Apply velocities
  const padding = 20;
  for (let i = 0; i < n; i++) {
    const node = nodes[i];

    // Dampen
    node.vx *= damping;
    node.vy *= damping;

    // Clamp velocity
    const speed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
    if (speed > maxVelocity) {
      node.vx = (node.vx / speed) * maxVelocity;
      node.vy = (node.vy / speed) * maxVelocity;
    }

    // Move
    node.x += node.vx;
    node.y += node.vy;

    // Bounds
    node.x = Math.max(padding, Math.min(width - padding, node.x));
    node.y = Math.max(padding, Math.min(height - padding, node.y));
  }
}

function draw(
  ctx: CanvasRenderingContext2D,
  nodes: SimNode[],
  edges: GraphEdge[],
  width: number,
  height: number,
  selectedId: string | null
) {
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = BG_COLOR;
  ctx.fillRect(0, 0, width, height);

  if (!nodes || nodes.length === 0) return;
  if (!edges) edges = [];

  // Build lookup for drawing edges
  const nodeMap = new Map<string, SimNode>();
  for (const node of nodes) {
    nodeMap.set(node.id, node);
  }

  // Draw edges
  ctx.strokeStyle = EDGE_COLOR;
  ctx.lineWidth = 0.5;
  ctx.beginPath();
  for (const edge of edges) {
    const s = nodeMap.get(edge.source);
    const t = nodeMap.get(edge.target);
    if (!s || !t) continue;
    ctx.moveTo(s.x, s.y);
    ctx.lineTo(t.x, t.y);
  }
  ctx.stroke();

  // Highlight edges for selected node
  if (selectedId) {
    ctx.strokeStyle = "rgba(232, 89, 12, 0.3)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (const edge of edges) {
      if (edge.source === selectedId || edge.target === selectedId) {
        const s = nodeMap.get(edge.source);
        const t = nodeMap.get(edge.target);
        if (!s || !t) continue;
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(t.x, t.y);
      }
    }
    ctx.stroke();
  }

  // Draw nodes
  for (const node of nodes) {
    const isSelected = node.id === selectedId;
    const isDoc = node.type === "document";
    const radius = isDoc ? 6 : 4;
    const color = isSelected ? SELECTED_COLOR : isDoc ? DOC_COLOR : CHUNK_COLOR;

    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();

    if (isSelected) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius + 3, 0, Math.PI * 2);
      ctx.strokeStyle = SELECTED_COLOR;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }

  // Draw labels for document nodes (and selected)
  ctx.font = "10px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (const node of nodes) {
    const isDoc = node.type === "document";
    const isSelected = node.id === selectedId;
    if (!isDoc && !isSelected) continue;

    const rawLabel = node.label ?? node.id ?? "";
    const label =
      rawLabel.length > 20 ? rawLabel.slice(0, 18) + "\u2026" : rawLabel;
    const radius = isDoc ? 6 : 4;

    ctx.fillStyle = isSelected
      ? "rgba(232, 89, 12, 0.9)"
      : "rgba(255,255,255,0.5)";
    ctx.fillText(label, node.x, node.y + radius + 4);
  }
}
