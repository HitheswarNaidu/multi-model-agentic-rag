"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Trash2Icon } from "lucide-react";
import { ChunkTable, type Chunk } from "@/components/data-store/chunk-table";
import {
  SavedAnswers,
  type SavedAnswer,
} from "@/components/data-store/saved-answers";

interface DocumentInfo {
  id: string;
  filename: string;
  chunk_count: number;
}

export default function DataStorePage() {
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [answers, setAnswers] = useState<SavedAnswer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [chunksData, docsData, answersData] = await Promise.allSettled([
        api.getChunks() as Promise<Chunk[]>,
        api.getDocuments() as Promise<DocumentInfo[]>,
        api.getAnswers() as Promise<SavedAnswer[]>,
      ]);

      if (chunksData.status === "fulfilled") {
        setChunks(Array.isArray(chunksData.value) ? chunksData.value : []);
      }
      if (docsData.status === "fulfilled") {
        setDocuments(Array.isArray(docsData.value) ? docsData.value : []);
      }
      if (answersData.status === "fulfilled") {
        setAnswers(Array.isArray(answersData.value) ? answersData.value : []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleDelete = useCallback(
    async (docId: string) => {
      if (!confirm(`Delete "${docId}" and all its chunks?`)) return;
      setDeleting(docId);
      try {
        await api.deleteDocument(docId);
        await loadData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Delete failed");
      } finally {
        setDeleting(null);
      }
    },
    [loadData]
  );

  const uniqueDocIds = useMemo(
    () => Array.from(new Set(chunks.map((c) => c.doc_id))).sort(),
    [chunks]
  );

  const stats = useMemo(() => {
    const chunkTypes = new Set(chunks.map((c) => c.chunk_type));
    return {
      documents: uniqueDocIds.length || documents.length,
      chunks: chunks.length,
      chunkTypes: chunkTypes.size,
    };
  }, [chunks, documents, uniqueDocIds]);

  if (loading) {
    return (
      <div className="p-8">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-foreground">Data Store</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Browse indexed chunks and saved answers.
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
            Loading data store...
          </div>
        </div>
      </div>
    );
  }

  if (error && chunks.length === 0) {
    return (
      <div className="p-8">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-foreground">Data Store</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Browse indexed chunks and saved answers.
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

  const hasData = chunks.length > 0;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-foreground">Data Store</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Browse indexed chunks and saved answers.
        </p>
      </div>

      {/* Stats row */}
      <div className="mb-6 grid grid-cols-3 gap-4">
        <StatCard label="Documents" value={stats.documents} />
        <StatCard label="Chunks" value={stats.chunks} />
        <StatCard label="Chunk Types" value={stats.chunkTypes} />
      </div>

      {/* Document list with delete */}
      {uniqueDocIds.length > 0 && (
        <div className="mb-6 space-y-1.5">
          <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Documents
          </p>
          <div className="flex flex-wrap gap-2">
            {uniqueDocIds.map((docId) => (
              <div
                key={docId}
                className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5"
              >
                <span className="text-xs text-foreground">{docId}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 w-5 p-0 text-muted-foreground hover:text-destructive"
                  onClick={() => handleDelete(docId)}
                  disabled={deleting === docId}
                >
                  {deleting === docId ? (
                    <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  ) : (
                    <Trash2Icon className="h-3 w-3" />
                  )}
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      <Separator className="mb-6" />

      {/* Tabs */}
      {hasData ? (
        <Tabs defaultValue="chunks">
          <TabsList>
            <TabsTrigger value="chunks">Chunks</TabsTrigger>
            <TabsTrigger value="answers">Saved Answers</TabsTrigger>
          </TabsList>

          <TabsContent value="chunks" className="mt-4">
            <ChunkTable data={chunks} />
          </TabsContent>

          <TabsContent value="answers" className="mt-4">
            <SavedAnswers answers={answers} />
          </TabsContent>
        </Tabs>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-16">
          <div className="mb-3 text-3xl opacity-40">&#128451;</div>
          <p className="text-sm font-medium text-muted-foreground">
            No indexed chunks yet.
          </p>
          <p className="mt-1 text-xs text-muted-foreground/60">
            Upload files from the Chat page to get started.
          </p>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <Card size="sm">
      <CardContent className="flex flex-col gap-1">
        <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <span className="text-2xl font-bold tabular-nums text-foreground">
          {value.toLocaleString()}
        </span>
      </CardContent>
    </Card>
  );
}
