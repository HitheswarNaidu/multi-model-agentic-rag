"use client";

import { Card, CardContent } from "@/components/ui/card";
import { DatabaseIcon, FileTextIcon, TargetIcon, ClockIcon } from "lucide-react";

interface Stats {
  chunks: number;
  documents: number;
  citationRate: number;
  avgLatency: number;
}

export function StatsBar({ stats }: { stats: Stats }) {
  const items = [
    {
      label: "Chunks indexed",
      value: stats.chunks.toLocaleString(),
      icon: DatabaseIcon,
    },
    {
      label: "Documents",
      value: stats.documents.toLocaleString(),
      icon: FileTextIcon,
    },
    {
      label: "Citation rate",
      value: `${stats.citationRate}%`,
      icon: TargetIcon,
    },
    {
      label: "Avg latency",
      value: `${stats.avgLatency}ms`,
      icon: ClockIcon,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {items.map((item) => (
        <Card key={item.label} size="sm">
          <CardContent className="flex items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10">
              <item.icon className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-xs text-muted-foreground">
                {item.label}
              </p>
              <p className="text-lg font-semibold leading-tight text-foreground">
                {item.value}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
