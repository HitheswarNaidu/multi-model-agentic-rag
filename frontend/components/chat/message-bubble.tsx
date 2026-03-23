"use client";

import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/hooks/use-chat";

interface Citation {
  document: string;
  page?: number;
  chunk_id?: string;
}

interface TimingInfo {
  retrieval_ms?: number;
  llm_ms?: number;
  total_ms?: number;
}

function extractCitations(metadata?: Record<string, unknown>): Citation[] {
  if (!metadata) return [];

  const citations: Citation[] = [];
  const seen = new Set<string>();

  // Pipeline returns retrieval as an array of chunk objects
  const retrieval = metadata.retrieval as Array<Record<string, unknown>> | undefined;
  if (Array.isArray(retrieval)) {
    for (const chunk of retrieval) {
      const doc = (chunk.doc_id ?? chunk.source ?? chunk.document ?? "unknown") as string;
      const page = (chunk.page ?? (chunk.metadata as Record<string, unknown> | undefined)?.page) as number | undefined;
      const key = `${doc}:${page ?? ""}`;
      if (!seen.has(key)) {
        seen.add(key);
        citations.push({ document: doc, page, chunk_id: chunk.chunk_id as string | undefined });
      }
    }
  }

  // Also check llm.provenance for cited chunk IDs
  const llm = metadata.llm as Record<string, unknown> | undefined;
  if (llm && Array.isArray(llm.provenance) && citations.length === 0) {
    for (const id of llm.provenance as string[]) {
      citations.push({ document: id });
    }
  }

  return citations;
}

function extractTiming(metadata?: Record<string, unknown>): TimingInfo | null {
  if (!metadata) return null;

  // Check timing_ms first (pipeline returns this as an object)
  const timingMs = metadata.timing_ms as Record<string, unknown> | number | undefined;
  if (timingMs && typeof timingMs === "object") {
    return {
      retrieval_ms: timingMs.retrieval_ms as number | undefined,
      llm_ms: timingMs.llm_ms as number | undefined,
      total_ms: timingMs.total_ms as number | undefined,
    };
  }

  const timing = metadata.timing as Record<string, unknown> | undefined;
  if (timing && typeof timing === "object") {
    return {
      retrieval_ms: timing.retrieval_ms as number | undefined,
      llm_ms: timing.llm_ms as number | undefined,
      total_ms: timing.total_ms as number | undefined,
    };
  }

  // Fallback: top-level timing as number
  if (typeof timingMs === "number") {
    return { total_ms: timingMs };
  }
  if (typeof metadata.latency_ms === "number") {
    return { total_ms: metadata.latency_ms as number };
  }

  return null;
}

function formatDocName(doc: string): string {
  const parts = doc.split("/");
  const name = parts[parts.length - 1];
  if (name.length > 20) {
    return name.slice(0, 17) + "...";
  }
  return name;
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const citations = extractCitations(message.metadata);
  const timing = extractTiming(message.metadata);

  return (
    <div
      className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}
    >
      <div className={cn("max-w-[80%] space-y-2", isUser ? "items-end" : "items-start")}>
        {/* Message bubble */}
        <div
          className={cn(
            "rounded-lg px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-card text-card-foreground ring-1 ring-foreground/10"
          )}
        >
          {message.content}
        </div>

        {/* Citations */}
        {!isUser && citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {citations.map((c, i) => (
              <span
                key={`${c.document}-${c.page ?? i}`}
                className="inline-flex items-center gap-1 rounded-full bg-[#2A1A0F] px-2.5 py-0.5 text-xs text-amber-400"
              >
                <span className="text-[10px]">{"\uD83D\uDCC4"}</span>
                {formatDocName(c.document)}
                {c.page != null && ` p.${c.page}`}
              </span>
            ))}
          </div>
        )}

        {/* Timing info */}
        {!isUser && timing && (
          <div className="px-1 text-[11px] text-muted-foreground">
            {timing.retrieval_ms != null && (
              <span>retrieval: {timing.retrieval_ms}ms</span>
            )}
            {timing.retrieval_ms != null && timing.llm_ms != null && (
              <span> {"\u00B7"} </span>
            )}
            {timing.llm_ms != null && <span>llm: {timing.llm_ms}ms</span>}
            {(timing.retrieval_ms != null || timing.llm_ms != null) &&
              timing.total_ms != null && <span> {"\u00B7"} </span>}
            {timing.total_ms != null && <span>total: {timing.total_ms}ms</span>}
          </div>
        )}
      </div>
    </div>
  );
}

export function LoadingBubble() {
  return (
    <div className="flex w-full justify-start">
      <div className="rounded-lg bg-card px-4 py-3 ring-1 ring-foreground/10">
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
          <span
            className="h-2 w-2 animate-pulse rounded-full bg-primary"
            style={{ animationDelay: "150ms" }}
          />
          <span
            className="h-2 w-2 animate-pulse rounded-full bg-primary"
            style={{ animationDelay: "300ms" }}
          />
        </div>
      </div>
    </div>
  );
}
