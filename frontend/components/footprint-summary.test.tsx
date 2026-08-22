import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FootprintSummary } from "./footprint-summary";
import { renderWithQueryClient } from "@/lib/test-utils";
import * as api from "@/lib/api";

describe("FootprintSummary", () => {
  it("renders exposure map stats once loaded", async () => {
    vi.spyOn(api, "fetchFootprint").mockResolvedValue({
      exposure_map: {
        total_data_points: 7,
        unique_streets: 2,
        known_locations: 1,
        unique_businesses: 3,
        tracked_activities: 4,
        day_patterns: 1,
      },
      entries: [],
    });

    renderWithQueryClient(<FootprintSummary />);

    await waitFor(() => expect(screen.getByText("7")).toBeInTheDocument());
    expect(screen.getByText(/unique streets/i)).toBeInTheDocument();
  });

  it("shows a nothing-ingested hint when the footprint is empty", async () => {
    vi.spyOn(api, "fetchFootprint").mockResolvedValue({
      exposure_map: {
        total_data_points: 0, unique_streets: 0, known_locations: 0,
        unique_businesses: 0, tracked_activities: 0, day_patterns: 0,
      },
      entries: [],
    });

    renderWithQueryClient(<FootprintSummary />);

    await waitFor(() =>
      expect(screen.getByText(/nothing ingested yet/i)).toBeInTheDocument(),
    );
  });

  it("shows an error message if the query fails", async () => {
    vi.spyOn(api, "fetchFootprint").mockRejectedValue(new Error("network down"));

    renderWithQueryClient(<FootprintSummary />);

    await waitFor(() =>
      expect(screen.getByText(/couldn't load footprint/i)).toBeInTheDocument(),
    );
  });
});
