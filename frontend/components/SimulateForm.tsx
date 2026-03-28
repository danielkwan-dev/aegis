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

interface SyncPost {
  index: number;
  label: string;
  timestamp: string | null;
  entities_found: {
    streets: string[];
    places: string[];
    businesses: string[];
    times: string[];
  };
  ocr_text: string | null;
  has_location: boolean;
}

interface SyncResult {
  status: string;
  username?: string;
  posts_scraped?: number;
  posts?: SyncPost[];
  exposure_map?: ExposureMap;
  final_conclusion?: string;
  message?: string;
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

export default function SimulateForm() {
  // Step 1: Instagram sync
  const [username, setUsername] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [syncProgress, setSyncProgress] = useState(0);

  // Step 2: Threat analysis
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exposureMap, setExposureMap] = useState<ExposureMap | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleSync() {
    const handle = username.replace("@", "").trim();
    if (!handle) return;

    setSyncing(true);
    setSyncResult(null);
    setSyncError(null);
    setSyncProgress(0);

    // Simulate progress while waiting for the backend
    const progressInterval = setInterval(() => {
      setSyncProgress((prev) => {
        if (prev >= 85) return Math.min(prev + 0.5, 92);
        return prev + Math.random() * 5;
      });
    }, 800);

    try {
      const formData = new FormData();
      formData.append("username", handle);

      const res = await fetch(`${API_URL}/api/sync-instagram`, {
        method: "POST",
        body: formData,
      });

      const data: SyncResult = await res.json();
      clearInterval(progressInterval);
      setSyncProgress(100);

      if (data.status === "synced") {
        setSyncResult(data);
        if (data.exposure_map) setExposureMap(data.exposure_map);
      } else {
        setSyncError(data.message || "Failed to sync profile.");
      }
    } catch (err) {
      clearInterval(progressInterval);
      console.error("Sync error:", err);
      setSyncError("Error connecting to backend. Is the FastAPI server running?");
    } finally {
      setSyncing(false);
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

  const profileSynced = syncResult?.status === "synced";
  const isAlarm = result && result.breach_probability > 80;

  return (
    <div
      style={isAlarm ? {
        border: "1px solid rgba(220,38,38,0.15)",
        borderRadius: "12px",
        padding: "1.5rem",
        margin: "-1.5rem",
        animation: "alarmPulse 3s ease-in-out infinite",
      } : undefined}
    >
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

      {/* STEP 1: Instagram OSINT */}
      <div style={{ marginBottom: "2.5rem", paddingBottom: "2rem", borderBottom: "1px solid #141618" }}>
        <div style={{ ...labelStyle, color: "#16a34a" }}>STEP 1 // INSTAGRAM OSINT</div>
        <p style={{ color: "#555", fontSize: "0.78rem", margin: "0 0 1rem", lineHeight: 1.5 }}>
          Enter a public Instagram handle. Aegis will scrape their past posts,
          run OCR on images, extract locations and timestamps, and build the exposure map.
        </p>

        <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1rem" }}>
          <div style={{ position: "relative", flex: 1 }}>
            <span
              style={{
                position: "absolute",
                left: "0.75rem",
                top: "50%",
                transform: "translateY(-50%)",
                color: "#444",
                fontSize: "0.85rem",
                pointerEvents: "none",
              }}
            >
              @
            </span>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !syncing && handleSync()}
              placeholder="username"
              disabled={syncing}
              style={{
                ...inputStyle,
                paddingLeft: "1.6rem",
              }}
            />
          </div>
          <button
            onClick={handleSync}
            disabled={syncing || !username.trim()}
            style={{
              padding: "0.6rem 1.5rem",
              backgroundColor: syncing ? "#141618" : "#0a1f0a",
              color: syncing ? "#555" : "#16a34a",
              border: `1px solid ${syncing ? "#1e2228" : "#16a34a30"}`,
              borderRadius: "6px",
              fontWeight: 600,
              fontSize: "0.82rem",
              fontFamily: "inherit",
              cursor: syncing ? "not-allowed" : "pointer",
              letterSpacing: "0.02em",
              whiteSpace: "nowrap",
            }}
          >
            {syncing ? "Scanning..." : "Scan Profile"}
          </button>
        </div>

        {/* Progress bar */}
        {syncing && (
          <div style={{ marginBottom: "1rem" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "0.3rem",
              }}
            >
              <span style={{ color: "#16a34a", fontSize: "0.7rem", fontWeight: 600 }}>
                Scanning @{username.replace("@", "")}...
              </span>
              <span style={{ color: "#444", fontSize: "0.7rem" }}>
                {Math.round(syncProgress)}%
              </span>
            </div>
            <div
              style={{
                width: "100%",
                height: 4,
                backgroundColor: "#141618",
                borderRadius: 2,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${syncProgress}%`,
                  height: "100%",
                  backgroundColor: "#16a34a",
                  borderRadius: 2,
                  transition: "width 0.4s ease",
                }}
              />
            </div>
          </div>
        )}

        {/* Sync error */}
        {syncError && (
          <p style={{ color: "#dc2626", fontSize: "0.78rem", margin: "0.5rem 0 0" }}>
            {syncError}
          </p>
        )}

        {/* Sync results */}
        {profileSynced && syncResult && (
          <div
            style={{
              padding: "1rem 1.25rem",
              backgroundColor: "#0a1a0a",
              border: "1px solid #16a34a20",
              borderRadius: "8px",
              animation: "fadeInUp 0.4s ease-out",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <span style={{ color: "#16a34a", fontSize: "0.78rem", fontWeight: 600 }}>
                @{syncResult.username} scanned
              </span>
              <span style={{ color: "#444", fontSize: "0.7rem" }}>
                {syncResult.posts_scraped} posts ingested
              </span>
            </div>

            {/* Post summary tags */}
            {syncResult.posts && syncResult.posts.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", marginBottom: "0.75rem" }}>
                {syncResult.posts.flatMap((p) => [
                  ...p.entities_found.streets,
                  ...p.entities_found.places,
                  ...p.entities_found.businesses,
                ]).filter((v, i, a) => a.indexOf(v) === i).slice(0, 20).map((ent, i) => (
                  <span
                    key={i}
                    style={{
                      padding: "0.15rem 0.45rem",
                      backgroundColor: "#06b6d410",
                      border: "1px solid #06b6d420",
                      borderRadius: "3px",
                      fontSize: "0.65rem",
                      color: "#06b6d4",
                    }}
                  >
                    {ent}
                  </span>
                ))}
              </div>
            )}

            {syncResult.final_conclusion && (
              <p style={{ color: "#667", fontSize: "0.75rem", margin: 0, lineHeight: 1.5 }}>
                {syncResult.final_conclusion}
              </p>
            )}
          </div>
        )}
      </div>

      {/* STEP 2: Pre-Post Analysis */}
      <div style={{ ...labelStyle, color: "#dc2626" }}>STEP 2 // PRE-POST ANALYSIS</div>
      <p style={{ color: "#555", fontSize: "0.78rem", margin: "0 0 1rem", lineHeight: 1.5 }}>
        Paste your draft post below. Aegis will scan it against the scraped baseline
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
