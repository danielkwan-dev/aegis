import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { useAnalyze } from "./use-analyze";
import * as api from "@/lib/api";

describe("useAnalyze", () => {
  it("invalidates score-history on success", async () => {
    vi.spyOn(api, "analyzeThreat").mockResolvedValue({
      status: "empty",
      message: "No text or image data to analyze.",
      web: { nodes: [], edges: [] },
      exposure_map: {
        total_data_points: 0, unique_streets: 0, known_locations: 0,
        unique_businesses: 0, tracked_activities: 0, day_patterns: 0,
      },
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    const invalidateSpy = vi.spyOn(client, "invalidateQueries");
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useAnalyze(), { wrapper });
    act(() => { result.current.mutate(new FormData()); });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["score-history"] });
  });
});
