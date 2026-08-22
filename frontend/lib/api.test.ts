import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, analyzeThreat, fetchFootprint, ingestExport, ingestManual } from "./api";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches footprint with credentials included", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ exposure_map: { total_data_points: 0 }, entries: [] }),
    });
    vi.stubGlobal("fetch", mockFetch);

    await fetchFootprint();

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/footprint"),
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("throws ApiError on a network failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );

    await expect(fetchFootprint()).rejects.toBeInstanceOf(ApiError);
  });

  it("throws ApiError on a non-2xx HTTP response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) }),
    );

    await expect(fetchFootprint()).rejects.toBeInstanceOf(ApiError);
  });

  it("resolves with the parsed body for an in-band logical error (still HTTP 200)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "error", message: "bad zip file" }),
      }),
    );

    const formData = new FormData();
    const result = await ingestExport(formData);

    expect(result).toEqual({ status: "error", message: "bad zip file" });
  });

  it("posts FormData as the body for mutations", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "empty", message: "No data to ingest." }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const formData = new FormData();
    formData.set("text", "hello");
    await ingestManual(formData);

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/ingest/manual"),
      expect.objectContaining({ method: "POST", body: formData }),
    );
  });

  it("analyzeThreat posts to /api/analyze-threat", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "empty", message: "No text or image data to analyze.", web: { nodes: [], edges: [] }, exposure_map: { total_data_points: 0 } }),
    });
    vi.stubGlobal("fetch", mockFetch);

    await analyzeThreat(new FormData());

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/analyze-threat"),
      expect.objectContaining({ method: "POST" }),
    );
  });
});
