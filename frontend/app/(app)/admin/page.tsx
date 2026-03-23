"use client";

import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
// Native range input used instead of shadcn Slider to avoid script-tag render crash
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

/* ---------- types ---------- */

interface FeatureToggles {
  vector_enabled: boolean;
  reranker_enabled: boolean;
  hyde_enabled: boolean;
  deep_rewrite_enabled: boolean;
  query_decomposition_enabled: boolean;
}

interface RetrievalWeights {
  bm25_weight: number;
  vector_weight: number;
}

interface ProviderStatus {
  parser: string;
  embeddings: string;
  llm: string;
}

interface IndexInfo {
  active_index_id: string;
  integrity: string;
  row_count: number;
}

interface TuningValues {
  parse_workers: number;
  parse_queue: number;
  embedding_batch: number;
  vector_upsert_batch: number;
  bm25_commit_batch: number;
  chunking_mode: string;
}

interface Settings {
  vector_enabled?: boolean;
  reranker_enabled?: boolean;
  hyde_enabled?: boolean;
  deep_rewrite_enabled?: boolean;
  query_decomposition_enabled?: boolean;
  bm25_weight?: number;
  vector_weight?: number;
  providers?: ProviderStatus;
}

/* ---------- skeleton placeholder ---------- */

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-md bg-muted ${className ?? ""}`}
    />
  );
}

/* ---------- main page ---------- */

export default function AdminPage() {
  const [loading, setLoading] = useState(true);

  /* feature toggles */
  const [toggles, setToggles] = useState<FeatureToggles>({
    vector_enabled: true,
    reranker_enabled: true,
    hyde_enabled: true,
    deep_rewrite_enabled: true,
    query_decomposition_enabled: true,
  });

  /* retrieval weights */
  const [weights, setWeights] = useState<RetrievalWeights>({
    bm25_weight: 0.5,
    vector_weight: 0.5,
  });

  /* provider status */
  const [providers, setProviders] = useState<ProviderStatus>({
    parser: "",
    embeddings: "",
    llm: "",
  });

  /* index diagnostics */
  const [indexInfo, setIndexInfo] = useState<IndexInfo>({
    active_index_id: "",
    integrity: "",
    row_count: 0,
  });
  const [switchingIndex, setSwitchingIndex] = useState(false);

  /* ingestion tuning */
  const [tuning, setTuning] = useState<TuningValues>({
    parse_workers: 2,
    parse_queue: 8,
    embedding_batch: 64,
    vector_upsert_batch: 100,
    bm25_commit_batch: 500,
    chunking_mode: "window",
  });

  /* danger zone */
  const [resetting, setResetting] = useState(false);

  /* ---------- fetch on mount ---------- */

  const fetchAll = useCallback(async () => {
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const [settingsData, indexRaw] = await Promise.all([
        api.getSettings() as Promise<Settings>,
        api.getIndex() as Promise<any>,
      ]);
      const indexData = indexRaw;

      setToggles({
        vector_enabled: settingsData.vector_enabled ?? true,
        reranker_enabled: settingsData.reranker_enabled ?? true,
        hyde_enabled: settingsData.hyde_enabled ?? true,
        deep_rewrite_enabled: settingsData.deep_rewrite_enabled ?? true,
        query_decomposition_enabled:
          settingsData.query_decomposition_enabled ?? true,
      });

      setWeights({
        bm25_weight: settingsData.bm25_weight ?? 0.5,
        vector_weight: settingsData.vector_weight ?? 0.5,
      });

      if (settingsData.providers) {
        setProviders(settingsData.providers);
      }

      setIndexInfo({
        active_index_id: indexData.active?.index_id ?? indexData.runtime_active_index_id ?? "",
        integrity: indexData.integrity?.suspicious === true ? "suspicious" : indexData.integrity?.suspicious === false ? "clean" : "unknown",
        row_count: indexData.integrity?.rows ?? 0,
      });
    } catch {
      toast.error("Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  /* ---------- toggle handler ---------- */

  async function handleToggle(key: keyof FeatureToggles, value: boolean) {
    const prev = toggles[key];
    setToggles((t) => ({ ...t, [key]: value }));
    try {
      await api.updateSettings({ [key]: value });
      toast.success(`${formatToggleLabel(key)} ${value ? "enabled" : "disabled"}`);
    } catch {
      setToggles((t) => ({ ...t, [key]: prev }));
      toast.error(`Failed to update ${formatToggleLabel(key)}`);
    }
  }

  /* ---------- weights handler ---------- */

  async function handleApplyWeights() {
    try {
      await api.updateSettings({
        bm25_weight: weights.bm25_weight,
        vector_weight: weights.vector_weight,
      });
      toast.success("Retrieval weights updated");
    } catch {
      toast.error("Failed to update weights");
    }
  }

  /* ---------- index switch ---------- */

  async function handleSwitchIndex() {
    setSwitchingIndex(true);
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const result = (await api.switchIndex()) as any;
      setIndexInfo({
        active_index_id: result.active_index_id ?? indexInfo.active_index_id,
        integrity: result.switched ? "clean" : indexInfo.integrity,
        row_count: indexInfo.row_count,
      });
      toast.success("Switched to latest clean index");
    } catch {
      toast.error("Failed to switch index");
    } finally {
      setSwitchingIndex(false);
    }
  }

  /* ---------- tuning handlers ---------- */

  async function handleApplyTuning() {
    try {
      await api.updateTuning(tuning as unknown as Record<string, unknown>);
      toast.success("Ingestion tuning applied");
    } catch {
      toast.error("Failed to apply tuning");
    }
  }

  async function handleResetTuning() {
    try {
      await api.resetTuning();
      setTuning({
        parse_workers: 2,
        parse_queue: 8,
        embedding_batch: 64,
        vector_upsert_batch: 100,
        bm25_commit_batch: 500,
        chunking_mode: "window",
      });
      toast.success("Tuning reset to defaults");
    } catch {
      toast.error("Failed to reset tuning");
    }
  }

  /* ---------- hard reset ---------- */

  async function handleHardReset() {
    const confirmed = window.confirm(
      "This will wipe all indices, uploads, and cached data. This action cannot be undone. Are you sure?"
    );
    if (!confirmed) return;

    setResetting(true);
    try {
      await api.updateSettings({ hard_reset: true });
      toast.success("Hard reset complete");
      await fetchAll();
    } catch {
      toast.error("Hard reset failed");
    } finally {
      setResetting(false);
    }
  }

  /* ---------- loading skeleton ---------- */

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl space-y-6 p-8">
        <div className="space-y-2">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-4 w-72" />
        </div>
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-48 w-full" />
        ))}
      </div>
    );
  }

  /* ---------- render ---------- */

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Admin</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Runtime controls, retrieval tuning, and maintenance.
        </p>
      </div>

      {/* ── Feature Toggles ── */}
      <Card>
        <CardHeader>
          <CardTitle>Feature Toggles</CardTitle>
          <CardDescription>
            Enable or disable retrieval pipeline features at runtime.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4">
            {TOGGLE_ROWS.map((row) => (
              <div
                key={row.key}
                className="flex items-center justify-between gap-4"
              >
                <div className="space-y-0.5">
                  <p className="text-sm font-medium leading-none">
                    {row.label}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {row.description}
                  </p>
                </div>
                <Switch
                  checked={toggles[row.key]}
                  onCheckedChange={(checked) => handleToggle(row.key, checked)}
                />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* ── Retrieval Weights ── */}
      <Card>
        <CardHeader>
          <CardTitle>Retrieval Weights</CardTitle>
          <CardDescription>
            Balance between BM25 keyword search and vector similarity.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <WeightSlider
            label="BM25 Weight"
            value={weights.bm25_weight}
            onChange={(v) => setWeights((w) => ({ ...w, bm25_weight: v }))}
          />
          <WeightSlider
            label="Vector Weight"
            value={weights.vector_weight}
            onChange={(v) => setWeights((w) => ({ ...w, vector_weight: v }))}
          />
        </CardContent>
        <CardFooter>
          <Button onClick={handleApplyWeights}>Apply</Button>
        </CardFooter>
      </Card>

      {/* ── Provider Status ── */}
      <Card>
        <CardHeader>
          <CardTitle>Provider Status</CardTitle>
          <CardDescription>
            Current provider configuration and health.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3">
            <ProviderRow
              label="Parser"
              value={providers.parser || "not configured"}
              ok={!!providers.parser && providers.parser !== "not configured"}
            />
            <Separator />
            <ProviderRow
              label="Embeddings"
              value={providers.embeddings || "not configured"}
              ok={
                !!providers.embeddings && providers.embeddings !== "not configured"
              }
            />
            <Separator />
            <ProviderRow
              label="LLM"
              value={providers.llm || "not configured"}
              ok={!!providers.llm && providers.llm !== "not configured"}
            />
          </div>
        </CardContent>
      </Card>

      {/* ── Index Diagnostics ── */}
      <Card>
        <CardHeader>
          <CardTitle>Index Diagnostics</CardTitle>
          <CardDescription>
            Active index details and integrity checks.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Active Index ID</span>
              <span className="font-mono text-xs">
                {indexInfo.active_index_id || "none"}
              </span>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Integrity</span>
              <Badge
                variant={
                  indexInfo.integrity === "clean" ? "default" : "destructive"
                }
              >
                {indexInfo.integrity || "unknown"}
              </Badge>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Row Count</span>
              <span className="font-mono text-xs">
                {indexInfo.row_count.toLocaleString()}
              </span>
            </div>
          </div>
        </CardContent>
        <CardFooter>
          <Button
            variant="outline"
            onClick={handleSwitchIndex}
            disabled={switchingIndex}
          >
            {switchingIndex ? "Switching..." : "Switch to Latest Clean Index"}
          </Button>
        </CardFooter>
      </Card>

      {/* ── Ingestion Tuning ── */}
      <Card>
        <CardHeader>
          <CardTitle>Ingestion Tuning</CardTitle>
          <CardDescription>
            Adjust batch sizes, concurrency, and chunking strategy.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <TuningInput
              label="Parse Workers"
              value={tuning.parse_workers}
              onChange={(v) =>
                setTuning((t) => ({ ...t, parse_workers: v }))
              }
            />
            <TuningInput
              label="Parse Queue"
              value={tuning.parse_queue}
              onChange={(v) =>
                setTuning((t) => ({ ...t, parse_queue: v }))
              }
            />
            <TuningInput
              label="Embedding Batch"
              value={tuning.embedding_batch}
              onChange={(v) =>
                setTuning((t) => ({ ...t, embedding_batch: v }))
              }
            />
            <TuningInput
              label="Vector Upsert Batch"
              value={tuning.vector_upsert_batch}
              onChange={(v) =>
                setTuning((t) => ({ ...t, vector_upsert_batch: v }))
              }
            />
            <TuningInput
              label="BM25 Commit Batch"
              value={tuning.bm25_commit_batch}
              onChange={(v) =>
                setTuning((t) => ({ ...t, bm25_commit_batch: v }))
              }
            />
            <div className="space-y-2">
              <label className="text-sm font-medium leading-none">
                Chunking Mode
              </label>
              <select
                value={tuning.chunking_mode}
                onChange={(e) =>
                  setTuning((t) => ({ ...t, chunking_mode: e.target.value }))
                }
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <option value="window">window</option>
                <option value="semantic_hybrid">semantic_hybrid</option>
              </select>
            </div>
          </div>
        </CardContent>
        <CardFooter className="gap-2">
          <Button onClick={handleApplyTuning}>Apply</Button>
          <Button variant="outline" onClick={handleResetTuning}>
            Reset to Defaults
          </Button>
        </CardFooter>
      </Card>

      {/* ── Danger Zone ── */}
      <Card className="border-destructive/40">
        <CardHeader>
          <CardTitle className="text-destructive">Danger Zone</CardTitle>
          <CardDescription>
            Irreversible operations. Proceed with caution.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            Hard reset will permanently delete all indices, uploaded files, and
            cached data. This action cannot be undone.
          </p>
        </CardContent>
        <CardFooter>
          <Button
            variant="destructive"
            onClick={handleHardReset}
            disabled={resetting}
          >
            {resetting ? "Resetting..." : "Hard Reset"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}

/* ================================================================
   Sub-components
   ================================================================ */

/* ---------- toggle row config ---------- */

const TOGGLE_ROWS: {
  key: keyof FeatureToggles;
  label: string;
  description: string;
}[] = [
  {
    key: "vector_enabled",
    label: "Vector Retrieval",
    description: "Enable NVIDIA embedding-based vector search.",
  },
  {
    key: "reranker_enabled",
    label: "Reranker",
    description: "Re-rank retrieved chunks for better relevance.",
  },
  {
    key: "hyde_enabled",
    label: "HyDE",
    description: "Hypothetical document embeddings (deep mode).",
  },
  {
    key: "deep_rewrite_enabled",
    label: "Deep Rewrite",
    description: "LLM-powered query rewriting (deep mode).",
  },
  {
    key: "query_decomposition_enabled",
    label: "Query Decomposition",
    description: "Break complex queries into sub-questions (deep mode).",
  },
];

function formatToggleLabel(key: keyof FeatureToggles): string {
  const row = TOGGLE_ROWS.find((r) => r.key === key);
  return row?.label ?? key;
}

/* ---------- weight slider ---------- */

function WeightSlider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium leading-none">{label}</label>
        <span className="text-sm tabular-nums text-muted-foreground">
          {value.toFixed(2)}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-secondary accent-primary"
      />
    </div>
  );
}

/* ---------- provider row ---------- */

function ProviderRow({
  label,
  value,
  ok,
}: {
  label: string;
  value: string;
  ok: boolean;
}) {
  const display = value.length > 40 ? value.slice(0, 37) + "..." : value;
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-sm text-muted-foreground shrink-0">{label}</span>
      <Badge
        variant={ok ? "default" : "destructive"}
        className="max-w-[280px] truncate"
        title={value}
      >
        {display}
      </Badge>
    </div>
  );
}

/* ---------- tuning number input ---------- */

function TuningInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium leading-none">{label}</label>
      <Input
        type="number"
        min={1}
        value={value}
        onChange={(e) => {
          const n = parseInt(e.target.value, 10);
          if (!isNaN(n) && n > 0) onChange(n);
        }}
      />
    </div>
  );
}
