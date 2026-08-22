import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { IngestionPanel } from "./ingestion-panel";
import { renderWithQueryClient } from "@/lib/test-utils";
import * as api from "@/lib/api";

describe("IngestionPanel", () => {
  it("submits manual entry text and shows the success message", async () => {
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

    renderWithQueryClient(<IngestionPanel />);

    fireEvent.change(screen.getByPlaceholderText(/grabbing my usual/i), {
      target: { value: "Coffee on Market Street" },
    });
    fireEvent.change(screen.getByPlaceholderText(/label this entry/i), {
      target: { value: "Morning routine" },
    });
    fireEvent.click(screen.getByRole("button", { name: /add to baseline/i }));

    await waitFor(() => expect(screen.getByText("Data Point Secured")).toBeInTheDocument());
    expect(api.ingestManual).toHaveBeenCalled();
    const formData = vi.mocked(api.ingestManual).mock.calls[0][0];
    expect(formData.get("text")).toBe("Coffee on Market Street");
    expect(formData.get("label")).toBe("Morning routine");
  });

  it("switches to the export tab and submits a zip file", async () => {
    vi.spyOn(api, "ingestExport").mockResolvedValue({
      status: "synced",
      posts_available: 10,
      posts_ingested: 10,
      posts_skipped: 0,
      exposure_map: {
        total_data_points: 10, unique_streets: 0, known_locations: 0,
        unique_businesses: 0, tracked_activities: 0, day_patterns: 0,
      },
    });

    renderWithQueryClient(<IngestionPanel />);

    fireEvent.click(screen.getByRole("tab", { name: /import export/i }));
    const file = new File(["zip-bytes"], "export.zip", { type: "application/zip" });
    const fileInput = screen.getByLabelText(/instagram data export/i) as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });
    fireEvent.change(screen.getByLabelText(/max posts to import/i), {
      target: { value: "25" },
    });
    fireEvent.click(screen.getByRole("button", { name: /import export/i }));

    await waitFor(() =>
      expect(screen.getByText(/10 posts ingested, 0 skipped/i)).toBeInTheDocument(),
    );
    const formData = vi.mocked(api.ingestExport).mock.calls[0][0];
    expect(formData.get("max_posts")).toBe("25");
  });

  it("disables the manual submit button when the text field is empty", () => {
    renderWithQueryClient(<IngestionPanel />);

    expect(screen.getByRole("button", { name: /add to baseline/i })).toBeDisabled();
  });

  it("shows an error message when manual entry submission fails", async () => {
    vi.spyOn(api, "ingestManual").mockRejectedValue(new Error("network down"));

    renderWithQueryClient(<IngestionPanel />);

    fireEvent.change(screen.getByPlaceholderText(/grabbing my usual/i), {
      target: { value: "test post" },
    });
    fireEvent.click(screen.getByRole("button", { name: /add to baseline/i }));

    await waitFor(() => expect(screen.getByText("network down")).toBeInTheDocument());
  });

  it("shows the backend's in-band error message when export import fails", async () => {
    vi.spyOn(api, "ingestExport").mockResolvedValue({
      status: "error",
      message: "not a valid zip file",
    });

    renderWithQueryClient(<IngestionPanel />);

    fireEvent.click(screen.getByRole("tab", { name: /import export/i }));
    const file = new File(["zip-bytes"], "export.zip", { type: "application/zip" });
    const fileInput = screen.getByLabelText(/instagram data export/i) as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: /import export/i }));

    await waitFor(() => expect(screen.getByText("not a valid zip file")).toBeInTheDocument());
  });
});
