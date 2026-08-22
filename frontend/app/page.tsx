"use client";

import { useState } from "react";
import { AnalysisForm } from "@/components/analysis-form";
import { BreachGauge } from "@/components/breach-gauge";
import { ConclusionNarrative } from "@/components/conclusion-narrative";
import { EmptyState } from "@/components/empty-state";
import { EntityGraph } from "@/components/entity-graph";
import { FindingsList } from "@/components/findings-list";
import { FootprintSummary } from "@/components/footprint-summary";
import { IngestionPanel } from "@/components/ingestion-panel";
import { ScoreHistoryChart } from "@/components/score-history-chart";
import type { AnalyzeThreatResult } from "@/lib/api-types";

export default function Home() {
  const [result, setResult] = useState<AnalyzeThreatResult | null>(null);

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 p-6">
      <header className="flex items-baseline justify-between border-b border-border pb-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Aegis</h1>
          <p className="text-xs text-muted-foreground">Personal Privacy Intelligence Engine</p>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[360px_1fr]">
        <div className="flex flex-col gap-6">
          <FootprintSummary />
          <IngestionPanel />
          <ScoreHistoryChart />
        </div>

        <div className="flex flex-col gap-6">
          <AnalysisForm onResult={setResult} />

          {!result && <EmptyState />}

          {result && result.status !== "analyzed" && (
            <p className="text-sm text-muted-foreground">{result.message}</p>
          )}

          {result && result.status === "analyzed" && (
            <>
              <div className="flex items-center gap-6">
                <BreachGauge score={result.breach_probability} />
                <ConclusionNarrative text={result.final_conclusion} />
              </div>
              <FindingsList findings={result.vulnerability_map} />
              <EntityGraph nodes={result.web.nodes} edges={result.web.edges} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
