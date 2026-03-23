"use client";

import { useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { SendHorizontalIcon, PaperclipIcon } from "lucide-react";

type QueryMode = "fast" | "deep";

interface DocumentOption {
  id: string;
  name: string;
}

interface ChatInputProps {
  onSend: (
    message: string,
    filters?: Record<string, unknown>,
    mode?: string
  ) => void;
  onFilesSelected: (files: FileList) => void;
  isLoading: boolean;
  documents: DocumentOption[];
}

export function ChatInput({
  onSend,
  onFilesSelected,
  isLoading,
  documents,
}: ChatInputProps) {
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<QueryMode>("fast");
  const [selectedDoc, setSelectedDoc] = useState<string>("all");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const filters: Record<string, unknown> =
      selectedDoc !== "all" ? { document: selectedDoc } : {};

    onSend(trimmed, filters, mode);
    setInput("");
  }, [input, isLoading, mode, selectedDoc, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleFileClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        onFilesSelected(e.target.files);
        // Reset so the same file can be re-selected
        e.target.value = "";
      }
    },
    [onFilesSelected]
  );

  return (
    <div className="space-y-2">
      {/* Controls row: mode toggle + document filter */}
      <div className="flex items-center gap-3">
        {/* Mode toggle */}
        <div className="inline-flex h-7 items-center rounded-lg bg-muted p-0.5">
          <button
            type="button"
            onClick={() => setMode("fast")}
            className={cn(
              "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
              mode === "fast"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            Fast
          </button>
          <button
            type="button"
            onClick={() => setMode("deep")}
            className={cn(
              "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
              mode === "deep"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            Deep
          </button>
        </div>

        {/* Document filter */}
        {documents.length > 0 && (
          <select
            value={selectedDoc}
            onChange={(e) => setSelectedDoc(e.target.value)}
            className="h-7 rounded-lg border border-input bg-transparent px-2 text-xs text-foreground outline-none focus:border-ring focus:ring-1 focus:ring-ring/50"
          >
            <option value="all">All documents</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Input row */}
      <div className="flex items-center gap-2">
        {/* File attach button */}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={handleFileClick}
          aria-label="Attach files"
          className="shrink-0 text-muted-foreground hover:text-foreground"
        >
          <PaperclipIcon className="h-4 w-4" />
        </Button>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.md,.docx,.csv,.json"
          onChange={handleFileChange}
          className="hidden"
        />

        {/* Text input */}
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about your documents..."
          disabled={isLoading}
          className="flex-1"
        />

        {/* Send button */}
        <Button
          onClick={handleSubmit}
          disabled={!input.trim() || isLoading}
          size="icon"
          aria-label="Send message"
        >
          <SendHorizontalIcon className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
