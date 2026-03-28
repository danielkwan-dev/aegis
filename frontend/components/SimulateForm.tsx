"use client";

import { useState, useRef } from "react";
import AuditResult from "./AuditResult";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ExposureMap {
  total_data_points: number;
  unique_streets: number;
  known_locations: number;
  unique_businesses: number;
  tracked_activities: number;
  day_patterns: number;
}

interface AnalysisResult {
  status: string;
  detected_entities: {
    streets: string[];
    places: string[];
    businesses: string[];
    times: string[];
    coordinates: string[];
  };
  category_similarity: Record<string, number>;
  breach_probability: number;
  vulnerability_map: any[];
  static_landmarks: any[];
  entity_triplets: any[];
  final_conclusion: string;
  signals: {
    draft_text_length: number;
    ocr_text: string | null;
    ocr_high_value: any[] | null;
    exif_metadata: Record<string, any> | null;
    time_context: any;
    merged_length: number;
  };
  web: { nodes: any[]; edges: any[] };
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
  detected_entities?: {
    streets: string[];
    places: string[];
    businesses: string[];
    times: string[];
    coordinates: string[];
  };
  exposure_map: ExposureMap;
  final_conclusion?: string;
}

export default function SimulateForm() {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ingestMsg, setIngestMsg] = useState<string | null>(null);
  const [ingestEntities, setIngestEntities] = useState<string[]>([]);
  const [exposureMap, setExposureMap] = useState<ExposureMap | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const ingestFileRef = useRef<HTMLInputElement>(null);

  const [ingestText, setIngestText] = useState("");
  const [ingestFile, setIngestFile] = useState<File | null>(null);

  async function handleIngest() {
    setIngesting(true);
    setIngestMsg(null);
    setIngestEntities([]);

    try {
      const formData = new FormData();
      formData.append("text", ingestText);
      if (ingestFile) formData.append("image", ingestFile);

      const res = await fetch(`${API_URL}/api/audit-ingest`, {
        method: "POST",
        body: formData,
      });

      const data: IngestResult = await res.json();
      setIngestMsg(data.message || "Ingested.");
      setExposureMap(data.exposure_map);

      // Collect detected entities for display
      if (data.detected_entities) {
        const ents: string[] = [
          ...data.detected_entities.streets,
          ...data.detected_entities.places,
          ...data.detected_entities.businesses,
          ...data.detected_entities.times,
        ];
        setIngestEntities(ents);
      }

      setIngestText("");
      setIngestFile(null);
    } catch (err) {
      console.error("Ingest error:", err);
      setIngestMsg("Error connecting to backend.");
    } finally {
      setIngesting(false);
    }
  }

  async function handleAnalyze() {
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("text", text);
      if (file) formData.append("image", file);

      const res = await fetch(`${API_URL}/api/analyze-threat`, {
        method: "POST",
        body: formData,
      });

      const data: AnalysisResult = await res.json();
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
    backgroundColor: "#0d1117",
    border: "1px solid #1e2228",
    borderRadius: "6px",
    color: "#c8ccd0",
    fontSize: "0.85rem",
    fontFamily: "inherit",
    outline: "none",
  };

  const labelStyle: React.CSSProperties = {
    fontSize: "0.6rem",
    fontWeight: 600,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    marginBottom: "0.75rem",
  };

  return (
    <div>
      {/* Exposure Map Stats Bar */}
      {exposureMap && (
        <div
          style={{
            padding: "0.75rem 1.25rem",
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
            {[
              { label: "Data Points", value: exposureMap.total_data_points },
              { label: "Streets", value: exposureMap.unique_streets },
              { label: "Locations", value: exposureMap.known_locations },
              { label: "Activities", value: exposureMap.tracked_activities },
              { label: "Day Patterns", value: exposureMap.day_patterns },
            ].map((stat) => (
              <div key={stat.label}>
                <div style={{ color: "#444", fontSize: "0.55rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  {stat.label}
                </div>
                <div style={{ color: "#c8ccd0", fontSize: "1.15rem", fontWeight: 700 }}>{stat.value}</div>
              </div>
            ))}
          </div>
          <span style={{ color: "#222", fontSize: "0.6rem", letterSpacing: "0.1em" }}>EXPOSURE MAP</span>
        </div>
      )}

      {/* STEP 1: Establish Baseline */}
      <div style={{ marginBottom: "2.5rem", paddingBottom: "2rem", borderBottom: "1px solid #141618" }}>
        <div style={{ ...labelStyle, color: "#16a34a" }}>STEP 1 // ESTABLISH BASELINE</div>
        <p style={{ color: "#555", fontSize: "0.78rem", margin: "0 0 1rem", lineHeight: 1.5 }}>
          Feed your past posts, photos, and check-ins to build the exposure map.
          The more data you provide, the more accurate the threat analysis becomes.
        </p>

        <textarea
          value={ingestText}
          onChange={(e) => setIngestText(e.target.value)}
          placeholder="Paste a past post, caption, or check-in..."
          rows={3}
          style={{ ...inputStyle, resize: "vertical", marginBottom: "0.75rem" }}
        />

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
          <button
            type="button"
            onClick={() => ingestFileRef.current?.click()}
            style={{
              padding: "0.35rem 0.85rem",
              backgroundColor: "#141618",
              border: "1px solid #1e2228",
              borderRadius: "5px",
              color: "#888",
              cursor: "pointer",
              fontSize: "0.75rem",
              fontFamily: "inherit",
            }}
          >
            + Attach photo
          </button>
          <span style={{ color: "#444", fontSize: "0.75rem" }}>
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
            padding: "0.6rem 1.5rem",
            backgroundColor: ingesting ? "#141618" : "#0a1f0a",
            color: ingesting ? "#555" : "#16a34a",
            border: `1px solid ${ingesting ? "#1e2228" : "#16a34a30"}`,
            borderRadius: "6px",
            fontWeight: 600,
            fontSize: "0.82rem",
            fontFamily: "inherit",
            cursor: ingesting ? "not-allowed" : "pointer",
            letterSpacing: "0.02em",
          }}
        >
          {ingesting ? "Securing..." : "Secure Data Point"}
        </button>

        {ingestMsg && (
          <span style={{ marginLeft: "0.75rem", color: "#16a34a", fontSize: "0.78rem" }}>
            {ingestMsg}
          </span>
        )}

        {/* Detected entities from ingest */}
        {ingestEntities.length > 0 && (
          <div style={{ marginTop: "0.75rem", display: "flex", flexWrap: "wrap", gap: "0.3rem" }}>
            {ingestEntities.map((ent, i) => (
              <span
                key={i}
                style={{
                  padding: "0.15rem 0.45rem",
                  backgroundColor: "#06b6d410",
                  border: "1px solid #06b6d420",
                  borderRadius: "3px",
                  fontSize: "0.68rem",
                  color: "#06b6d4",
                }}
              >
                {ent}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* STEP 2: Pre-Post Analysis */}
      <div style={{ ...labelStyle, color: "#dc2626" }}>STEP 2 // PRE-POST ANALYSIS</div>
      <p style={{ color: "#555", fontSize: "0.78rem", margin: "0 0 1rem", lineHeight: 1.5 }}>
        Paste your draft post below. Aegis will scan it against your baseline
        to detect Identity Links that could expose sensitive patterns.
      </p>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste your draft post here..."
        rows={5}
        style={{ ...inputStyle, resize: "vertical", marginBottom: "1rem" }}
      />

      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.5rem" }}>
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          style={{
            padding: "0.35rem 0.85rem",
            backgroundColor: "#141618",
            border: "1px solid #1e2228",
            borderRadius: "5px",
            color: "#888",
            cursor: "pointer",
            fontSize: "0.75rem",
            fontFamily: "inherit",
          }}
        >
          + Attach image
        </button>
        <span style={{ color: "#444", fontSize: "0.75rem" }}>
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
          backgroundColor: loading ? "#141618" : "#dc2626",
          color: loading ? "#555" : "#fff",
          border: "none",
          borderRadius: "6px",
          fontWeight: 700,
          fontSize: "0.9rem",
          fontFamily: "inherit",
          cursor: loading ? "not-allowed" : "pointer",
          letterSpacing: "0.04em",
          transition: "background-color 0.2s ease",
        }}
      >
        {loading ? "Scanning..." : "Run Threat Analysis"}
      </button>

      {error && (
        <p style={{ color: "#dc2626", fontSize: "0.78rem", marginTop: "1rem" }}>{error}</p>
      )}

      {/* Results */}
      {result && (
        <div style={{ marginTop: "2rem" }}>
          <AuditResult result={result} />
        </div>
      )}
    </div>
  );
}
