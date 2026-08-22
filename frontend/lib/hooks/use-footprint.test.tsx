import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { useFootprint } from "./use-footprint";
import * as api from "@/lib/api";

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe("useFootprint", () => {
  it("returns footprint data on success", async () => {
    vi.spyOn(api, "fetchFootprint").mockResolvedValue({
      exposure_map: {
        total_data_points: 3,
        unique_streets: 1,
        known_locations: 0,
        unique_businesses: 0,
        tracked_activities: 0,
        day_patterns: 0,
      },
      entries: [],
    });

    const { result } = renderHook(() => useFootprint(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.exposure_map.total_data_points).toBe(3);
  });
});
