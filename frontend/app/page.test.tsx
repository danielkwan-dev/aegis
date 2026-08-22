import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Home from "./page";
import { renderWithQueryClient } from "@/lib/test-utils";
import * as api from "@/lib/api";

vi.mock("react-force-graph-2d", () => ({
  default: () => <div data-testid="force-graph-stub" />,
}));

const EMPTY_EXPOSURE_MAP = {
  total_data_points: 0,
  unique_streets: 0,
  known_locations: 0,
  unique_businesses: 0,
  tracked_activities: 0,
  day_patterns: 0,
};

describe("Home (composed page)", () => {
  it("drives a manual ingest then a draft analysis end-to-end and renders the real results", async () => {
    vi.spyOn(api, "fetchFootprint").mockResolvedValue({
      exposure_map: EMPTY_EXPOSURE_MAP,
      entries: [],
    });
    vi.spyOn(api, "fetchScoreHistory").mockResolvedValue({ history: [] });

    vi.spyOn(api, "ingestManual").mockResolvedValue({
      status: "secured",
      message: "Data Point Secured",
      entry: {} as never,
      detected_entities: { streets: [], places: [], businesses: [], times: [], coordinates: [] },
      exposure_map: { ...EMPTY_EXPOSURE_MAP, total_data_points: 1 },
      final_conclusion: "",
    });

    vi.spyOn(api, "analyzeThreat").mockResolvedValue({
      status: "analyzed",
      detected_entities: { streets: [], places: [], businesses: [], times: [], coordinates: [] },
      category_similarity: {},
      breach_probability: 63,
      vulnerability_map: [
        {
          category: "Location Pattern",
          severity: "critical",
          finding: "Recurring posts near Market Street reveal a predictable morning routine.",
          evidence_count: 3,
        },
      ],
      static_landmarks: [],
      entity_triplets: [],
      final_conclusion: "This draft would expose a recognizable daily pattern.",
      signals: {
        draft_text_length: 20,
        ocr_text: null,
        ocr_high_value: null,
        exif_metadata: null,
        time_context: null,
        merged_length: 20,
      },
      web: { nodes: [], edges: [] },
      exposure_map: { ...EMPTY_EXPOSURE_MAP, total_data_points: 1 },
    });

    renderWithQueryClient(<Home />);

    // Baseline footprint loads first.
    await waitFor(() => expect(api.fetchFootprint).toHaveBeenCalled());

    // Submit a manual ingest entry to build the baseline.
    fireEvent.change(screen.getByPlaceholderText(/grabbing my usual/i), {
      target: { value: "Coffee on Market Street" },
    });
    fireEvent.click(screen.getByRole("button", { name: /add to baseline/i }));

    await waitFor(() => expect(screen.getByText("Data Point Secured")).toBeInTheDocument());
    expect(api.ingestManual).toHaveBeenCalled();

    // Submit a draft post for analysis.
    fireEvent.change(screen.getByPlaceholderText(/draft the post/i), {
      target: { value: "Heading to my usual coffee spot on Market Street" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^analyze$/i }));

    await waitFor(() => expect(api.analyzeThreat).toHaveBeenCalled());

    // The composed page must actually render the analyzed result through its children,
    // not just avoid crashing: breach probability (BreachGauge), a vulnerability-map
    // finding (FindingsList), and the conclusion narrative (ConclusionNarrative).
    await waitFor(() => expect(screen.getByText("63%")).toBeInTheDocument());
    expect(
      screen.getByText(/recurring posts near market street reveal a predictable morning routine/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/this draft would expose a recognizable daily pattern/i),
    ).toBeInTheDocument();

    // The pre-analysis empty state must be gone now that a result rendered.
    expect(screen.queryByText(/add some text or an image to analyze/i)).not.toBeInTheDocument();
  });
});
