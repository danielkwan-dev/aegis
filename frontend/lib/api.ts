import type {
  AnalyzeThreatResult,
  FootprintResponse,
  IngestExportResult,
  IngestManualResult,
  ScoreHistoryResponse,
} from "./api-types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: "include",
    });
  } catch {
    throw new ApiError(
      "Couldn't reach the server. Check your connection and that the backend is running.",
    );
  }

  if (!response.ok) {
    throw new ApiError(`Server returned an unexpected error (${response.status}).`);
  }

  return (await response.json()) as T;
}

export function fetchFootprint(): Promise<FootprintResponse> {
  return request<FootprintResponse>("/api/footprint");
}

export function fetchScoreHistory(): Promise<ScoreHistoryResponse> {
  return request<ScoreHistoryResponse>("/api/score-history");
}

export function ingestManual(formData: FormData): Promise<IngestManualResult> {
  return request<IngestManualResult>("/api/ingest/manual", {
    method: "POST",
    body: formData,
  });
}

export function ingestExport(formData: FormData): Promise<IngestExportResult> {
  return request<IngestExportResult>("/api/ingest/export", {
    method: "POST",
    body: formData,
  });
}

export function analyzeThreat(formData: FormData): Promise<AnalyzeThreatResult> {
  return request<AnalyzeThreatResult>("/api/analyze-threat", {
    method: "POST",
    body: formData,
  });
}
