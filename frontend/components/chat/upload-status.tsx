"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { XIcon, Loader2Icon, CheckCircle2Icon, AlertCircleIcon } from "lucide-react";
import type { JobStatus } from "@/hooks/use-ingestion";

interface UploadStatusProps {
  jobId: string | null;
  jobStatus: JobStatus | null;
  isUploading: boolean;
  error: string | null;
  onDismiss: () => void;
}

export function UploadStatus({
  jobId,
  jobStatus,
  isUploading,
  error,
  onDismiss,
}: UploadStatusProps) {
  const [visible, setVisible] = useState(true);

  // Auto-dismiss after completion
  useEffect(() => {
    if (jobStatus?.status === "completed") {
      const timer = setTimeout(() => {
        setVisible(false);
        onDismiss();
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [jobStatus?.status, onDismiss]);

  if (!visible || (!isUploading && !jobId && !error)) {
    return null;
  }

  const status = jobStatus?.status ?? (isUploading ? "uploading" : "unknown");
  const progress = jobStatus?.progress ?? 0;

  return (
    <Card size="sm" className="border-primary/20">
      <CardContent className="flex items-center gap-3">
        {/* Status icon */}
        <div className="flex h-8 w-8 shrink-0 items-center justify-center">
          {(status === "uploading" || status === "queued" || status === "running") && (
            <Loader2Icon className="h-4 w-4 animate-spin text-primary" />
          )}
          {status === "completed" && (
            <CheckCircle2Icon className="h-4 w-4 text-emerald-500" />
          )}
          {(status === "failed" || error) && (
            <AlertCircleIcon className="h-4 w-4 text-destructive" />
          )}
        </div>

        {/* Info */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="text-xs font-medium text-foreground">
              {status === "uploading" && "Uploading files..."}
              {status === "queued" && "Queued for processing"}
              {status === "running" && "Processing documents..."}
              {status === "completed" && "Ingestion complete"}
              {status === "failed" && "Ingestion failed"}
              {status === "unknown" && error && "Upload error"}
            </p>
            {jobId && (
              <span className="text-[10px] text-muted-foreground">
                {jobId.slice(0, 8)}
              </span>
            )}
          </div>

          {/* Progress bar */}
          {(status === "running" || status === "queued") && (
            <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all duration-500"
                style={{ width: `${Math.max(progress * 100, status === "running" ? 10 : 2)}%` }}
              />
            </div>
          )}

          {error && (
            <p className="mt-0.5 text-[11px] text-destructive">{error}</p>
          )}
        </div>

        {/* Dismiss */}
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={() => {
            setVisible(false);
            onDismiss();
          }}
          aria-label="Dismiss"
        >
          <XIcon className="h-3 w-3" />
        </Button>
      </CardContent>
    </Card>
  );
}
