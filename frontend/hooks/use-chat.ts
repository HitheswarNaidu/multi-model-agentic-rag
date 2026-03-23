"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  metadata?: Record<string, unknown>;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(
    async (
      question: string,
      filters?: Record<string, unknown>,
      mode?: string
    ) => {
      setMessages((prev) => [...prev, { role: "user", content: question }]);
      setIsLoading(true);

      try {
        const res = await api.query(question, filters, mode);

        if (!res.ok) {
          throw new Error(`Query failed: ${res.status}`);
        }

        const reader = res.body?.getReader();
        const decoder = new TextDecoder();
        let fullData = "";

        // Read SSE stream
        if (reader) {
          let done = false;
          while (!done) {
            const result = await reader.read();
            done = result.done;
            if (result.value) {
              fullData += decoder.decode(result.value, { stream: true });
            }
          }
        }

        // Parse the JSON from SSE data lines
        const dataLines = fullData
          .split("\n")
          .filter(
            (line) => line.startsWith("data: ") && !line.includes("[DONE]")
          )
          .map((line) => line.slice(6));

        const jsonStr = dataLines.join("");
        const data = jsonStr ? JSON.parse(jsonStr) : null;

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data?.llm?.answer || "No answer received.",
            metadata: data,
          },
        ]);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Error: " + (err as Error).message,
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const clearMessages = useCallback(() => setMessages([]), []);

  return { messages, isLoading, sendMessage, clearMessages };
}
