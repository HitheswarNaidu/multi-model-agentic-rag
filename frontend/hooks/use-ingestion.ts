"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";

export interface JobStatus {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  progress?: number;
  error?: string;
  created_at?: string;
  completed_at?: string;
}

export function useIngestion() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (id: string) => {
      stopPolling();
      intervalRef.current = setInterval(async () => {
        try {
          const status = (await api.getJob(id)) as JobStatus;
          setJobStatus(status);

          if (status.status === "completed" || status.status === "failed") {
            stopPolling();
            if (status.status === "failed") {
              setError(status.error || "Ingestion failed");
            }
          }
        } catch (err) {
          setError((err as Error).message);
          stopPolling();
        }
      }, 2000);
    },
    [stopPolling]
  );

  const uploadFiles = useCallback(
    async (files: FileList | File[]) => {
      setIsUploading(true);
      setError(null);
      setJobStatus(null);

      try {
        const fileArray = Array.from(files);
        const res = await api.uploadFiles(fileArray);

        if (!res.ok) {
          throw new Error(`Upload failed: ${res.status}`);
        }

        const data = await res.json();
        const id = data.job_id as string;
        setJobId(id);
        setJobStatus({
          job_id: id,
          status: "queued",
        });

        startPolling(id);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setIsUploading(false);
      }
    },
    [startPolling]
  );

  const reset = useCallback(() => {
    stopPolling();
    setJobId(null);
    setJobStatus(null);
    setError(null);
  }, [stopPolling]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  return {
    jobId,
    jobStatus,
    isUploading,
    error,
    uploadFiles,
    reset,
  };
}
