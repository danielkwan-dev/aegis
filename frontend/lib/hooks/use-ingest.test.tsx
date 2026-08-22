import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { useIngestExport, useIngestManual } from "./use-ingest";
import * as api from "@/lib/api";

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const invalidateSpy = vi.spyOn(client, "invalidateQueries");
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { wrapper, invalidateSpy };
}

describe("useIngestManual", () => {
  it("invalidates the footprint query on success", async () => {
    vi.spyOn(api, "ingestManual").mockResolvedValue({
      status: "secured",
      message: "Data Point Secured",
      entry: {} as never,
      detected_entities: { streets: [], places: [], businesses: [], times: [], coordinates: [] },
      exposure_map: {
        total_data_points: 1, unique_streets: 0, known_locations: 0,
        unique_businesses: 0, tracked_activities: 0, day_patterns: 0,
      },
      final_conclusion: "",
    });
    const { wrapper, invalidateSpy } = makeWrapper();

    const { result } = renderHook(() => useIngestManual(), { wrapper });
    act(() => { result.current.mutate(new FormData()); });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["footprint"] });
  });
});

describe("useIngestExport", () => {
  it("invalidates the footprint query on success", async () => {
    vi.spyOn(api, "ingestExport").mockResolvedValue({
      status: "synced",
      posts_available: 5,
      posts_ingested: 5,
      posts_skipped: 0,
      exposure_map: {
        total_data_points: 5, unique_streets: 0, known_locations: 0,
        unique_businesses: 0, tracked_activities: 0, day_patterns: 0,
      },
    });
    const { wrapper, invalidateSpy } = makeWrapper();

    const { result } = renderHook(() => useIngestExport(), { wrapper });
    act(() => { result.current.mutate(new FormData()); });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["footprint"] });
  });
});
