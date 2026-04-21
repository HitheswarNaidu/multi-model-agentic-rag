"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface SavedAnswer {
  id: string;
  question: string;
  answer: string;
  citations: string[];
  timestamp: string;
  metadata?: Record<string, unknown>;
}

interface SavedAnswersProps {
  answers: SavedAnswer[];
}

export function SavedAnswers({ answers }: SavedAnswersProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (answers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-700 bg-zinc-900 py-16">
        <div className="mb-3 text-4xl opacity-40">&#128196;</div>
        <p className="text-sm font-medium text-zinc-400">No saved answers yet.</p>
        <p className="mt-1 text-xs text-zinc-600">Answers will appear here after you query from the Chat page.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {answers.map((answer) => {
        const isExpanded = expandedId === answer.id;
        const formattedDate = formatTimestamp(answer.timestamp);

        return (
          <Card key={answer.id} className="border-zinc-700 bg-zinc-800/50 transition-colors hover:bg-zinc-800">
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-4">
                <CardTitle className="text-sm font-medium leading-snug text-zinc-200">
                  {answer.question}
                </CardTitle>
                <span className="shrink-0 text-[10px] text-zinc-500">{formattedDate}</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Answer text */}
              <div className="text-sm leading-relaxed text-zinc-300">
                {isExpanded ? answer.answer : truncate(answer.answer, 200)}
                {answer.answer.length > 200 && (
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : answer.id)}
                    className="ml-1 text-xs font-medium text-orange-400 hover:underline"
                  >
                    {isExpanded ? "Show less" : "Show more"}
                  </button>
                )}
              </div>

              {/* Citations */}
              {answer.citations.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {answer.citations.map((citation, idx) => (
                    <Badge key={idx} className="bg-orange-500/20 text-orange-400 border-orange-500/30">
                      {citation}
                    </Badge>
                  ))}
                </div>
              )}

              {/* Expanded metadata */}
              {isExpanded && answer.metadata && (
                <div className="rounded-lg bg-zinc-900 p-3 border border-zinc-700">
                  <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-zinc-500">
                    Metadata
                  </p>
                  <pre className="text-xs leading-relaxed text-zinc-400">
                    {JSON.stringify(answer.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen) + "\u2026";
}

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return ts;
  }
}
