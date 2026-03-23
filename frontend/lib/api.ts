const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchAPI<T = unknown>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // Health / status
  getStatus: () => fetchAPI("/api/status"),

  // Query (returns raw Response for SSE streaming)
  query: (question: string, filters?: Record<string, unknown>, mode?: string) =>
    fetch(`${API_BASE}/api/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, filters, mode }),
    }),

  // File upload (multipart/form-data)
  uploadFiles: (files: File[], options?: Record<string, unknown>) => {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    if (options) {
      formData.append("options", JSON.stringify(options));
    }
    return fetch(`${API_BASE}/api/upload`, {
      method: "POST",
      body: formData,
    });
  },

  // Jobs
  getJobs: () => fetchAPI("/api/jobs"),
  getJob: (id: string) => fetchAPI(`/api/jobs/${id}`),

  // Data
  getChunks: () => fetchAPI("/api/chunks"),
  getDocuments: () => fetchAPI("/api/documents"),
  deleteDocument: (docId: string) =>
    fetchAPI(`/api/documents/${encodeURIComponent(docId)}`, { method: "DELETE" }),
  getGraph: () => fetchAPI("/api/graph"),
  getAnswers: () => fetchAPI("/api/answers"),

  // Admin
  getSettings: () => fetchAPI("/api/admin/settings"),
  updateSettings: (settings: Record<string, unknown>) =>
    fetchAPI("/api/admin/settings", {
      method: "POST",
      body: JSON.stringify(settings),
    }),
  getIndex: () => fetchAPI("/api/admin/index"),
  switchIndex: () =>
    fetchAPI("/api/admin/index/switch", { method: "POST" }),
  updateTuning: (tuning: Record<string, unknown>) =>
    fetchAPI("/api/admin/tuning", {
      method: "POST",
      body: JSON.stringify(tuning),
    }),
  resetTuning: () =>
    fetchAPI("/api/admin/tuning/reset", { method: "POST" }),
};
