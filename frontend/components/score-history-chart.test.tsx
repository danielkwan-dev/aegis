import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ScoreHistoryChart, formatHistoryForChart } from "./score-history-chart";
import { renderWithQueryClient } from "@/lib/test-utils";
import * as api from "@/lib/api";

describe("formatHistoryForChart", () => {
  it("assigns a 1-based index to each entry, preserving order", () => {
    const formatted = formatHistoryForChart([
      { timestamp: "2026-01-01T00:00:00Z", breach_probability: 10, severity_counts: { critical: 0, high: 0, medium: 0, low: 0 }, entity_counts: {} },
      { timestamp: "2026-01-02T00:00:00Z", breach_probability: 30, severity_counts: { critical: 0, high: 0, medium: 0, low: 0 }, entity_counts: {} },
    ]);

    expect(formatted.map((f) => f.index)).toEqual([1, 2]);
    expect(formatted.map((f) => f.breach_probability)).toEqual([10, 30]);
  });
});

describe("ScoreHistoryChart", () => {
  it("shows a no-analyses message when history is empty", async () => {
    vi.spyOn(api, "fetchScoreHistory").mockResolvedValue({ history: [] });

    renderWithQueryClient(<ScoreHistoryChart />);

    await waitFor(() => expect(screen.getByText(/no analyses yet/i)).toBeInTheDocument());
  });

  it("shows an error message if the query fails", async () => {
    vi.spyOn(api, "fetchScoreHistory").mockRejectedValue(new Error("down"));

    renderWithQueryClient(<ScoreHistoryChart />);

    await waitFor(() =>
      expect(screen.getByText(/couldn't load score history/i)).toBeInTheDocument(),
    );
  });
});
