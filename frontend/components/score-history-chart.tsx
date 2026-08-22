"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useScoreHistory } from "@/lib/hooks/use-score-history";
import type { ScoreHistoryEntryDict } from "@/lib/api-types";

export function formatHistoryForChart(history: ScoreHistoryEntryDict[]) {
  return history.map((entry, i) => ({
    index: i + 1,
    timestamp: new Date(entry.timestamp).toLocaleString(),
    breach_probability: entry.breach_probability,
  }));
}

export function ScoreHistoryChart() {
  const { data, isPending, isError } = useScoreHistory();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Breach probability over time
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isPending && <Skeleton className="h-40 w-full" />}
        {isError && <p className="text-sm text-destructive">Couldn&apos;t load score history.</p>}
        {data && data.history.length === 0 && (
          <p className="text-sm text-muted-foreground">No analyses yet.</p>
        )}
        {data && data.history.length > 0 && (
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={formatHistoryForChart(data.history)}>
              <XAxis dataKey="index" tick={false} />
              <YAxis domain={[0, 100]} width={30} tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(value: number) => [`${value}%`, "Breach probability"]}
                labelFormatter={(_, payload) => payload?.[0]?.payload?.timestamp ?? ""}
              />
              <Line type="monotone" dataKey="breach_probability" stroke="currentColor" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
