"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";

export interface GraphNode {
  id: string;
  label: string;
  type: "document" | "chunk" | string;
  doc_id?: string;
  page?: number | null;
  section?: string;
  content?: string;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight?: number;
}

interface NodeInspectorProps {
  node: GraphNode | null;
  edges: GraphEdge[];
  nodes: GraphNode[];
}

export function NodeInspector({ node, edges, nodes }: NodeInspectorProps) {
  if (!node) {
    return (
      <Card className="h-full">
        <CardContent className="flex h-full flex-col items-center justify-center py-16">
          <div className="mb-3 text-2xl opacity-30">&#128270;</div>
          <p className="text-sm text-muted-foreground">
            Select a node to inspect
          </p>
          <p className="mt-1 text-center text-xs text-muted-foreground/60">
            Click on any node in the graph to view its details and connections.
          </p>
        </CardContent>
      </Card>
    );
  }

  const neighbors = getNeighbors(node.id, edges, nodes);

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{
              backgroundColor:
                node.type === "document" ? "#6c9bd2" : "#f4a261",
            }}
          />
          <CardTitle className="text-sm">{node.label}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="space-y-4 pr-2">
            {/* Properties */}
            <div className="space-y-2">
              <InfoRow label="ID" value={node.id} mono />
              <InfoRow
                label="Type"
                value={
                  <Badge variant="secondary">{node.type}</Badge>
                }
              />
              {node.doc_id && (
                <InfoRow label="Document" value={node.doc_id} mono />
              )}
              {node.page != null && (
                <InfoRow label="Page" value={String(node.page)} />
              )}
              {node.section && (
                <InfoRow label="Section" value={node.section} />
              )}
            </div>

            {/* Content preview */}
            {node.content && (
              <>
                <Separator />
                <div>
                  <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    Content Preview
                  </p>
                  <p className="rounded-lg bg-muted/50 p-3 text-xs leading-relaxed text-foreground/80">
                    {node.content.length > 300
                      ? node.content.slice(0, 300) + "\u2026"
                      : node.content}
                  </p>
                </div>
              </>
            )}

            {/* Connected neighbors */}
            {neighbors.length > 0 && (
              <>
                <Separator />
                <div>
                  <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    Connected Nodes ({neighbors.length})
                  </p>
                  <div className="space-y-1">
                    {neighbors.slice(0, 20).map((neighbor) => (
                      <div
                        key={neighbor.id}
                        className="flex items-center gap-2 rounded-md px-2 py-1 text-xs"
                      >
                        <span
                          className="inline-block h-1.5 w-1.5 rounded-full"
                          style={{
                            backgroundColor:
                              neighbor.type === "document"
                                ? "#6c9bd2"
                                : "#f4a261",
                          }}
                        />
                        <span className="truncate text-foreground/70">
                          {neighbor.label}
                        </span>
                      </div>
                    ))}
                    {neighbors.length > 20 && (
                      <p className="px-2 text-[10px] text-muted-foreground">
                        + {neighbors.length - 20} more
                      </p>
                    )}
                  </div>
                </div>
              </>
            )}

            {/* Action */}
            <Separator />
            <div>
              <Link
                href={`/chat?q=${encodeURIComponent(node.label)}`}
              >
                <Button variant="outline" size="sm" className="w-full">
                  Ask in Chat
                </Button>
              </Link>
            </div>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function InfoRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-2">
      <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span
        className={`text-right text-xs text-foreground/80 ${
          mono ? "font-mono" : ""
        }`}
      >
        {value}
      </span>
    </div>
  );
}

function getNeighbors(
  nodeId: string,
  edges: GraphEdge[],
  nodes: GraphNode[]
): GraphNode[] {
  const neighborIds = new Set<string>();
  for (const edge of edges) {
    if (edge.source === nodeId) neighborIds.add(edge.target);
    if (edge.target === nodeId) neighborIds.add(edge.source);
  }
  return nodes.filter((n) => neighborIds.has(n.id));
}
