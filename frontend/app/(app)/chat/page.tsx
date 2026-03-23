"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useChat } from "@/hooks/use-chat";
import { useIngestion } from "@/hooks/use-ingestion";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble, LoadingBubble } from "@/components/chat/message-bubble";
import { ChatInput } from "@/components/chat/chat-input";
import { StatsBar } from "@/components/chat/stats-bar";
import { UploadStatus } from "@/components/chat/upload-status";
import { UploadIcon, MessageSquareIcon } from "lucide-react";

interface DocumentItem {
  id: string;
  name: string;
  filename?: string;
}

interface StatusResponse {
  chunk_count?: number;
  document_count?: number;
  citation_rate?: number;
  avg_latency_ms?: number;
  [key: string]: unknown;
}

export default function ChatPage() {
  const { messages, isLoading, sendMessage, clearMessages } = useChat();
  const {
    jobId,
    jobStatus,
    isUploading,
    error: ingestionError,
    uploadFiles,
    reset: resetIngestion,
  } = useIngestion();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [stats, setStats] = useState({
    chunks: 0,
    documents: 0,
    citationRate: 0,
    avgLatency: 0,
  });

  const scrollEndRef = useRef<HTMLDivElement>(null);
  const topFileInputRef = useRef<HTMLInputElement>(null);

  // Fetch documents and stats on mount and after ingestion completes
  const fetchData = useCallback(async () => {
    try {
      const [statusData, docsData] = await Promise.allSettled([
        api.getStatus() as Promise<StatusResponse>,
        api.getDocuments() as Promise<DocumentItem[]>,
      ]);

      if (statusData.status === "fulfilled" && statusData.value) {
        const s = statusData.value;
        setStats({
          chunks: s.chunk_count ?? 0,
          documents: s.document_count ?? 0,
          citationRate: s.citation_rate ?? 0,
          avgLatency: s.avg_latency_ms ?? 0,
        });
      }

      if (docsData.status === "fulfilled" && Array.isArray(docsData.value)) {
        setDocuments(
          docsData.value.map((d: string | DocumentItem) => {
            if (typeof d === "string") return { id: d, name: d };
            return {
              id: d.id ?? d.filename ?? d.name ?? String(d),
              name: d.name ?? d.filename ?? d.id ?? String(d),
            };
          })
        );
      }
    } catch {
      // Silently ignore -- stats will show zeros
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Refresh data when ingestion completes
  useEffect(() => {
    if (jobStatus?.status === "completed") {
      fetchData();
    }
  }, [jobStatus?.status, fetchData]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleFilesSelected = useCallback(
    (files: FileList) => {
      uploadFiles(files);
    },
    [uploadFiles]
  );

  const handleTopUpload = useCallback(() => {
    topFileInputRef.current?.click();
  }, []);

  const handleTopFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        uploadFiles(e.target.files);
        e.target.value = "";
      }
    },
    [uploadFiles]
  );

  const showUploadStatus = isUploading || jobId !== null || ingestionError !== null;

  return (
    <div className="flex h-full flex-col">
      {/* Top bar */}
      <div className="flex shrink-0 items-center justify-between border-b border-border px-6 py-4">
        <h1 className="text-lg font-semibold text-foreground">Chat</h1>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">
            {stats.documents} doc{stats.documents !== 1 ? "s" : ""}
          </span>
          <Button variant="outline" size="sm" onClick={handleTopUpload}>
            <UploadIcon className="mr-1.5 h-3.5 w-3.5" />
            Upload
          </Button>
          <input
            ref={topFileInputRef}
            type="file"
            multiple
            accept=".pdf,.txt,.md,.docx,.csv,.json"
            onChange={handleTopFileChange}
            className="hidden"
          />
        </div>
      </div>

      {/* Stats row */}
      <div className="shrink-0 px-6 pt-4">
        <StatsBar stats={stats} />
      </div>

      {/* Upload status */}
      {showUploadStatus && (
        <div className="shrink-0 px-6 pt-3">
          <UploadStatus
            jobId={jobId}
            jobStatus={jobStatus}
            isUploading={isUploading}
            error={ingestionError}
            onDismiss={resetIngestion}
          />
        </div>
      )}

      {/* Chat area */}
      <div className="min-h-0 flex-1 px-6 pt-4">
        <ScrollArea className="h-full">
          {messages.length === 0 && !isLoading ? (
            /* Empty state */
            <div className="flex h-full min-h-[300px] flex-col items-center justify-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
                <MessageSquareIcon className="h-6 w-6 text-muted-foreground" />
              </div>
              <p className="text-sm text-muted-foreground">
                Ask anything about your documents
              </p>
              {stats.documents === 0 && (
                <p className="text-xs text-muted-foreground/60">
                  Upload documents to get started
                </p>
              )}
            </div>
          ) : (
            <div className="space-y-4 pb-4">
              {messages.map((msg, i) => (
                <MessageBubble key={i} message={msg} />
              ))}
              {isLoading && <LoadingBubble />}
              <div ref={scrollEndRef} />
            </div>
          )}
        </ScrollArea>
      </div>

      {/* Input area - fixed at bottom */}
      <div className="shrink-0 border-t border-border px-6 py-4">
        <ChatInput
          onSend={sendMessage}
          onFilesSelected={handleFilesSelected}
          isLoading={isLoading}
          documents={documents.map((d) => ({ id: d.id, name: d.name }))}
        />
      </div>
    </div>
  );
}
