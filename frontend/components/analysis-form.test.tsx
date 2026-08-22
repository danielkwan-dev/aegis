import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AnalysisForm } from "./analysis-form";
import { renderWithQueryClient } from "@/lib/test-utils";
import * as api from "@/lib/api";

describe("AnalysisForm", () => {
  it("calls onResult with the analysis result on success", async () => {
    const result = {
      status: "analyzed" as const,
      detected_entities: { streets: [], places: [], businesses: [], times: [], coordinates: [] },
      category_similarity: {},
      breach_probability: 55,
      vulnerability_map: [],
      static_landmarks: [],
      entity_triplets: [],
      final_conclusion: "Baseline established.",
      signals: {
        draft_text_length: 5, ocr_text: null, ocr_high_value: null,
        exif_metadata: null, time_context: null, merged_length: 5,
      },
      web: { nodes: [], edges: [] },
      exposure_map: {
        total_data_points: 1, unique_streets: 0, known_locations: 0,
        unique_businesses: 0, tracked_activities: 0, day_patterns: 0,
      },
    };
    vi.spyOn(api, "analyzeThreat").mockResolvedValue(result);
    const onResult = vi.fn();

    renderWithQueryClient(<AnalysisForm onResult={onResult} />);

    fireEvent.change(screen.getByPlaceholderText(/draft the post/i), {
      target: { value: "Heading to the gym" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^analyze$/i }));

    await waitFor(() => expect(onResult).toHaveBeenCalledWith(result));
  });

  it("disables the analyze button while text is empty", () => {
    renderWithQueryClient(<AnalysisForm onResult={vi.fn()} />);

    expect(screen.getByRole("button", { name: /^analyze$/i })).toBeDisabled();
  });

  it("shows an error message when analysis fails", async () => {
    vi.spyOn(api, "analyzeThreat").mockRejectedValue(new Error("server exploded"));

    renderWithQueryClient(<AnalysisForm onResult={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText(/draft the post/i), {
      target: { value: "test" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^analyze$/i }));

    await waitFor(() => expect(screen.getByText("server exploded")).toBeInTheDocument());
  });
});
