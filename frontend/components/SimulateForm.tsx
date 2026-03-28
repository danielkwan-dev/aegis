"use client";

import { useState, useRef } from "react";
import ThreatBanner from "./ThreatBanner";
import VisualizationWrapper from "./VisualizationWrapper";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ExposureMap {
  total_data_points: number;
  sensitive_entities: Record<string, number>;
  known_locations: number;
}

interface AnalysisResult {
  status: string;
  risk_level: string;
  max_similarity: number;
  breach_probability: number;
  entity_scores: Record<string, number>;
  signals: {
    draft_text_length: number;
    ocr_text: string | null;
    exif_metadata: Record<string, any> | null;
    merged_length: number;
  };
  web: {
    nodes: any[];
    edges: any[];
  };
  exposure_map: ExposureMap;
  hex?: {
    runId?: string;
    runUrl?: string;
    projectId?: string;
    error?: string;
  } | null;
  message?: string;
}

interface IngestResult {
  status: string;
  message: string;
  exposure_map: ExposureMap;
}

export default function SimulateForm() {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ingestMsg, setIngestMsg] = useState<string | null>(null);
  const [exposureMap, setExposureMap] = useState<ExposureMap | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const ingestFileRef = useRef<HTMLInputElement>(null);

  // ── Ingest a data point ──
  const [ingestText, setIngestText] = useState("");
  const [ingestFile, setIngestFile] = useState<File | null>(null);

  async function handleIngest() {
    setIngesting(true);
    setIngestMsg(null);

    try {
      const formData = new FormData();
      formData.append("text", ingestText);
      if (ingestFile) {
        formData.append("image", ingestFile);
      }

      const res = await fetch(`${API_URL}/api/audit-ingest`, {
        method: "POST",
        body: formData,
      });

      const data: IngestResult = await res.json();
      console.log("Ingest response:", data);
      setIngestMsg(data.message || "Ingested.");
      setExposureMap(data.exposure_map);
      setIngestText("");
      setIngestFile(null);
    } catch (err) {
      console.error("Ingest error:", err);
      setIngestMsg("Error connecting to backend.");
    } finally {
      setIngesting(false);
    }
  }

  // ── Analyze threat ──
  async function handleAnalyze() {
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("text", text);
      if (file) {
        formData.append("image", file);
      }

      const res = await fetch(`${API_URL}/api/analyze-threat`, {
        method: "POST",
        body: formData,
      });

      const data: AnalysisResult = await res.json();
      console.log("Aegis response:", data);
      setExposureMap(data.exposure_map);

      if (data.status === "analyzed") {
        setResult(data);
      } else {
        setError(data.message || "No analysis returned.");
      }
    } catch (err) {
      console.error("Analyze error:", err);
      setError("Error connecting to backend. Is the FastAPI server running?");
    } finally {
      setLoading(false);
    }
  }

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "0.75rem",
    backgroundColor: "#111",
    border: "1px solid #333",
    borderRadius: "8px",
    color: "#e0e0e0",
    fontSize: "0.95rem",
    outline: "none",
    boxSizing: "border-box",
  };

  const sectionHeader: React.CSSProperties = {
    fontSize: "0.75rem",
    fontWeight: 600,
    letterSpacing: "0.05em",
    textTransform: "uppercase" as const,
    marginBottom: "0.75rem",
  };

  return (
    <div>
      {/* Exposure Map Stats */}
      {exposureMap && (
        <div
          style={{
            padding: "0.75rem 1rem",
            backgroundColor: "#0d1117",
            border: "1px solid #1a1a1a",
            borderRadius: "8px",
            marginBottom: "2rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", gap: "1.5rem" }}>
            <div>
              <div style={{ color: "#666", fontSize: "0.65rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Data Points</div>
              <div style={{ color: "#e0e0e0", fontSize: "1.25rem", fontWeight: 700 }}>{exposureMap.total_data_points}</div>
            </div>
            <div>
              <div style={{ color: "#666", fontSize: "0.65rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Known Locations</div>
              <div style={{ color: "#e0e0e0", fontSize: "1.25rem", fontWeight: 700 }}>{exposureMap.known_locations}</div>
            </div>
            <div>
              <div style={{ color: "#666", fontSize: "0.65rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Entity Types</div>
              <div style={{ color: "#e0e0e0", fontSize: "1.25rem", fontWeight: 700 }}>{Object.keys(exposureMap.sensitive_entities).length}</div>
            </div>
          </div>
          <span style={{ color: "#333", fontSize: "0.7rem" }}>EXPOSURE MAP</span>
        </div>
      )}

      {/* ── SECTION 1: Audit Ingest ── */}
      <div style={{ marginBottom: "2.5rem", paddingBottom: "2rem", borderBottom: "1px solid #1a1a1a" }}>
        <div style={{ ...sectionHeader, color: "#4ade80" }}>1. Build Security Baseline</div>
        <p style={{ color: "#666", fontSize: "0.85rem", margin: "0 0 1rem" }}>
          Feed your past posts, photos, and check-ins to build the exposure map.
        </p>

        <textarea
          value={ingestText}
          onChange={(e) => setIngestText(e.target.value)}
          placeholder="Paste a past post, caption, or check-in..."
          rows={3}
          style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit", marginBottom: "0.75rem" }}
        />

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
          <button
            type="button"
            onClick={() => ingestFileRef.current?.click()}
            style={{
              padding: "0.4rem 1rem",
              backgroundColor: "#1a1a1a",
              border: "1px solid #333",
              borderRadius: "6px",
              color: "#ccc",
              cursor: "pointer",
              fontSize: "0.8rem",
            }}
          >
            📎 Attach photo
          </button>
          <span style={{ color: "#666", fontSize: "0.8rem" }}>
            {ingestFile ? ingestFile.name : "No file"}
          </span>
          <input
            ref={ingestFileRef}
            type="file"
            accept="image/*"
            style={{ display: "none" }}
            onChange={(e) => setIngestFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <button
          onClick={handleIngest}
          disabled={ingesting || (!ingestText && !ingestFile)}
          style={{
            padding: "0.65rem 1.5rem",
            backgroundColor: ingesting ? "#333" : "#1a3a1a",
            color: ingesting ? "#888" : "#4ade80",
            border: "1px solid #2d5a2d",
            borderRadius: "8px",
            fontWeight: 600,
            fontSize: "0.9rem",
            cursor: ingesting ? "not-allowed" : "pointer",
          }}
        >
          {ingesting ? "Ingesting..." : "Ingest Data Point"}
        </button>

        {ingestMsg && (
          <span style={{ marginLeft: "1rem", color: "#4ade80", fontSize: "0.85rem" }}>
            {ingestMsg}
          </span>
        )}
      </div>

      {/* ── SECTION 2: Analyze Threat ── */}
      <div style={{ ...sectionHeader, color: "#f87171" }}>2. Analyze Threat</div>
      <p style={{ color: "#666", fontSize: "0.85rem", margin: "0 0 1rem" }}>
        Test a new draft post against your baseline. Aegis will detect Identity Links
        that could expose sensitive entities like Home, Work, or Daily Route.
      </p>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste your draft post here..."
        rows={6}
        style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit", marginBottom: "1rem" }}
      />

      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.5rem" }}>
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          style={{
            padding: "0.5rem 1.25rem",
            backgroundColor: "#1a1a1a",
            border: "1px solid #333",
            borderRadius: "6px",
            color: "#ccc",
            cursor: "pointer",
            fontSize: "0.85rem",
          }}
        >
          📎 Attach image
        </button>
        <span style={{ color: "#666", fontSize: "0.85rem" }}>
          {file ? file.name : "No file selected"}
        </span>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          style={{ display: "none" }}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </div>

      <button
        onClick={handleAnalyze}
        disabled={loading || (!text && !file)}
        style={{
          width: "100%",
          padding: "0.85rem",
          backgroundColor: loading ? "#333" : "#fff",
          color: loading ? "#888" : "#0a0a0a",
          border: "none",
          borderRadius: "8px",
          fontWeight: 600,
          fontSize: "1rem",
          cursor: loading ? "not-allowed" : "pointer",
        }}
      >
        {loading ? "Analyzing..." : "Analyze Threat"}
      </button>

      {error && (
        <p style={{ color: "#f87171", fontSize: "0.85rem", marginTop: "1rem" }}>{error}</p>
      )}

      {/* Results */}
      {result && (
        <div style={{ marginTop: "2rem" }}>
          <ThreatBanner
            riskLevel={result.risk_level}
            maxSimilarity={result.max_similarity}
            breachProbability={result.breach_probability}
            entityScores={result.entity_scores}
          />
          <VisualizationWrapper web={result.web} hex={result.hex} />

          {result.signals.ocr_text && (
            <div
              style={{
                padding: "0.75rem 1rem",
                backgroundColor: "#111",
                border: "1px solid #1a1a1a",
                borderRadius: "8px",
                marginBottom: "0.75rem",
              }}
            >
              <span style={{ color: "#06b6d4", fontSize: "0.75rem", fontWeight: 600, textTransform: "uppercase" }}>
                OCR Extracted Text
              </span>
              <p style={{ color: "#888", fontSize: "0.8rem", margin: "0.4rem 0 0", whiteSpace: "pre-wrap" }}>
                {result.signals.ocr_text}
              </p>
            </div>
          )}
          {result.signals.exif_metadata && (
            <div
              style={{
                padding: "0.75rem 1rem",
                backgroundColor: "#111",
                border: "1px solid #1a1a1a",
                borderRadius: "8px",
                marginBottom: "0.75rem",
              }}
            >
              <span style={{ color: "#f43f5e", fontSize: "0.75rem", fontWeight: 600, textTransform: "uppercase" }}>
                EXIF Metadata Leaked
              </span>
              <pre style={{ color: "#888", fontSize: "0.75rem", margin: "0.4rem 0 0", fontFamily: "monospace" }}>
                {JSON.stringify(result.signals.exif_metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
