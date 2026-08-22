"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useFootprint } from "@/lib/hooks/use-footprint";
import type { ExposureMap } from "@/lib/api-types";

const STATS: { key: keyof ExposureMap; label: string }[] = [
  { key: "total_data_points", label: "Posts ingested" },
  { key: "unique_streets", label: "Unique streets" },
  { key: "known_locations", label: "Known locations" },
  { key: "unique_businesses", label: "Businesses" },
  { key: "tracked_activities", label: "Activities" },
  { key: "day_patterns", label: "Day patterns" },
];

export function FootprintSummary() {
  const { data, isPending, isError } = useFootprint();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Baseline footprint
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isPending && (
          <div className="grid grid-cols-2 gap-3">
            {STATS.map((s) => (
              <Skeleton key={s.key} className="h-12 w-full" />
            ))}
          </div>
        )}
        {isError && (
          <p className="text-sm text-destructive">Couldn&apos;t load footprint stats.</p>
        )}
        {data && (
          <div className="grid grid-cols-2 gap-3">
            {STATS.map((s) => (
              <div key={s.key}>
                <div className="text-2xl font-semibold">{data.exposure_map[s.key]}</div>
                <div className="text-xs text-muted-foreground">{s.label}</div>
              </div>
            ))}
          </div>
        )}
        {data && data.exposure_map.total_data_points === 0 && (
          <p className="mt-3 text-sm text-muted-foreground">
            Nothing ingested yet — add a post below to build a baseline.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
