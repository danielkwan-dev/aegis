import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { useScoreHistory } from "./use-score-history";
import * as api from "@/lib/api";

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe("useScoreHistory", () => {
  it("returns score history data on success", async () => {
    vi.spyOn(api, "fetchScoreHistory").mockResolvedValue({
      history: [
        {
          timestamp: "2026-08-21T00:00:00Z",
          breach_probability: 42,
          severity_counts: { critical: 0, high: 1, medium: 0, low: 0 },
          entity_counts: {},
        },
      ],
    });

    const { result } = renderHook(() => useScoreHistory(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.history).toHaveLength(1);
  });
});
