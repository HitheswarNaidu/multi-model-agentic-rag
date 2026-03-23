"use client";

import { useEffect, useState, useMemo, useCallback, lazy, Suspense } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Slider } from "@/components/ui/slider";
import {
  NodeInspector,
  type GraphNode,
  type GraphEdge,
} from "@/components/graph/node-inspector";

// Dynamic import to avoid SSR issues with canvas
const ForceGraph = lazy(() =>
  import("@/components/graph/force-graph").then((mod) => ({
    default: mod.ForceGraph,
  }))
);

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export default function KnowledgeGraphPage() {
  const [graphData, setGraphData] = useState<GraphData>({
    nodes: [],
    edges: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nodeCap, setNodeCap] = useState(300);
  const [docFilter, setDocFilter] = useState("__all__");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadGraph() {
      setLoading(true);
      setError(null);
      try {
        const raw = (await api.getGraph()) as Record<string, unknown[]>;
        // Transform backend shape to frontend GraphNode/GraphEdge
        const rawNodes = Array.isArray(raw?.nodes) ? raw.nodes : [];
        const rawEdges = Array.isArray(raw?.edges) ? raw.edges : [];

        const nodes: GraphNode[] = rawNodes.map((n: Record<string, unknown>) => {
          const nodeType = String(n.node_type ?? n.type ?? "chunk");
          const mappedType = nodeType === "doc" ? "document" : nodeType;
          const docId = String(n.doc_id ?? "");
          const chunkId = String(n.chunk_id ?? "");
          const label =
            mappedType === "document"
              ? docId || String(n.id)
              : chunkId || String(n.id);
          return {
            id: String(n.id),
            label,
            type: mappedType,
            doc_id: docId || undefined,
            page: n.page != null ? Number(n.page) : undefined,
            section: n.section ? String(n.section) : undefined,
            content: n.content_preview
              ? String(n.content_preview)
              : n.content
                ? String(n.content)
                : undefined,
          } as GraphNode;
        });

        const edges: GraphEdge[] = rawEdges.map((e: Record<string, unknown>) => ({
          source: String(e.source),
          target: String(e.target),
          weight: e.weight != null ? Number(e.weight) : undefined,
        }));

        if (!cancelled) {
          setGraphData({ nodes, edges });
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load graph"
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadGraph();
    return () => {
      cancelled = true;
    };
  }, []);

  const uniqueDocs = useMemo(() => {
    const docs = new Set<string>();
    for (const node of graphData.nodes) {
      if (node.doc_id) docs.add(node.doc_id);
      if (node.type === "document") docs.add(node.id);
    }
    return Array.from(docs).sort();
  }, [graphData.nodes]);

  const filteredData = useMemo(() => {
    if (docFilter === "__all__") return graphData;

    const filteredNodes = graphData.nodes.filter(
      (n) =>
        n.doc_id === docFilter ||
        (n.type === "document" && n.id === docFilter)
    );
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    const filteredEdges = graphData.edges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
    );

    return { nodes: filteredNodes, edges: filteredEdges };
  }, [graphData, docFilter]);

  const displayedNodeCount = Math.min(filteredData.nodes.length, nodeCap);
  const displayedEdges = useMemo(() => {
    const cappedIds = new Set(
      filteredData.nodes.slice(0, nodeCap).map((n) => n.id)
    );
    return filteredData.edges.filter(
      (e) => cappedIds.has(e.source) && cappedIds.has(e.target)
    );
  }, [filteredData, nodeCap]);

  const handleSelectNode = useCallback((node: GraphNode | null) => {
    setSelectedNode(node);
  }, []);

  if (loading) {
    return (
      <div className="p-8">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-foreground">
            Knowledge Graph
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Interactive graph investigation.
          </p>
        </div>
        <div className="flex items-center justify-center py-24">
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <svg
              className="h-4 w-4 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Loading graph data...
          </div>
        </div>
      </div>
    );
  }

  if (error && graphData.nodes.length === 0) {
    return (
      <div className="p-8">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-foreground">
            Knowledge Graph
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Interactive graph investigation.
          </p>
        </div>
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-16">
          <div className="mb-3 text-3xl opacity-40">&#9888;</div>
          <p className="text-sm font-medium text-destructive">{error}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Make sure the backend API is running.
          </p>
        </div>
      </div>
    );
  }

  const hasData = graphData.nodes.length > 0;

  return (
    <div className="flex h-full flex-col p-8">
      {/* Header */}
      <div className="mb-6 shrink-0">
        <h1 className="text-xl font-bold text-foreground">Knowledge Graph</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Interactive graph investigation.
        </p>
      </div>

      {hasData ? (
        <div className="flex min-h-0 flex-1 gap-4">
          {/* Graph area (left, 3/4) */}
          <div className="flex min-h-0 flex-[3] flex-col gap-3">
            {/* Controls bar */}
            <div className="flex flex-wrap items-end gap-4">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  Document
                </label>
                <select
                  value={docFilter}
                  onChange={(e) => {
                    setDocFilter(e.target.value);
                    setSelectedNode(null);
                  }}
                  className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground outline-none focus:border-ring focus:ring-3 focus:ring-ring/50 dark:bg-input/30"
                >
                  <option value="__all__">All documents</option>
                  {uniqueDocs.map((doc) => (
                    <option key={doc} value={doc}>
                      {doc}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  Node Cap: {nodeCap}
                </label>
                <div className="w-[180px]">
                  <Slider
                    min={50}
                    max={800}
                    value={[nodeCap]}
                    onValueChange={(val) => {
                      const v = Array.isArray(val) ? val[0] : val;
                      setNodeCap(v);
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Canvas */}
            <div className="min-h-0 flex-1">
              <Suspense
                fallback={
                  <div className="flex h-full items-center justify-center rounded-xl border border-border bg-[#1A1A1A]">
                    <p className="text-sm text-muted-foreground">
                      Loading graph renderer...
                    </p>
                  </div>
                }
              >
                <ForceGraph
                  nodes={filteredData.nodes}
                  edges={filteredData.edges}
                  nodeCap={nodeCap}
                  selectedNodeId={selectedNode?.id ?? null}
                  onSelectNode={handleSelectNode}
                />
              </Suspense>
            </div>

            {/* Stats */}
            <div className="flex shrink-0 items-center gap-4">
              <StatPill
                label="Nodes"
                value={displayedNodeCount}
                total={filteredData.nodes.length}
              />
              <StatPill
                label="Edges"
                value={displayedEdges.length}
              />
              <div className="flex items-center gap-3 ml-auto">
                <LegendDot color={DOC_COLOR} label="Document" />
                <LegendDot color={CHUNK_COLOR} label="Chunk" />
              </div>
            </div>
          </div>

          {/* Inspector (right, 1/4) */}
          <div className="w-[280px] shrink-0">
            <NodeInspector
              node={selectedNode}
              edges={graphData.edges}
              nodes={graphData.nodes}
            />
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-16">
          <div className="mb-3 text-3xl opacity-40">&#128280;</div>
          <p className="text-sm font-medium text-muted-foreground">
            No graph data available.
          </p>
          <p className="mt-1 text-xs text-muted-foreground/60">
            Upload and index documents from the Chat page to build the knowledge
            graph.
          </p>
        </div>
      )}
    </div>
  );
}

const DOC_COLOR = "#6c9bd2";
const CHUNK_COLOR = "#f4a261";

function StatPill({
  label,
  value,
  total,
}: {
  label: string;
  value: number;
  total?: number;
}) {
  return (
    <Card size="sm" className="inline-flex">
      <CardContent className="flex items-center gap-2 !py-1.5">
        <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <span className="text-sm font-bold tabular-nums text-foreground">
          {value.toLocaleString()}
          {total !== undefined && total > value && (
            <span className="font-normal text-muted-foreground">
              /{total.toLocaleString()}
            </span>
          )}
        </span>
      </CardContent>
    </Card>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span
        className="inline-block h-2 w-2 rounded-full"
        style={{ backgroundColor: color }}
      />
      <span className="text-[10px] text-muted-foreground">{label}</span>
    </div>
  );
}
