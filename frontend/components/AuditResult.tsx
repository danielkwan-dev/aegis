"use client";

import { motion } from "framer-motion";
import RiskGauge from "./RiskGauge";
import TypingEffect from "./TypingEffect";
import DigitalShadow from "./DigitalShadow";
import VisualizationWrapper from "./VisualizationWrapper";
import ScoreTracker, { type ScoreEntry } from "./ScoreTracker";
import HexDashboard from "./HexDashboard";

interface VulnFinding {
  category: string;
  severity: string;
  finding: string;
  evidence_count: number;
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
  vulnerability_map: VulnFinding[];
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
  web: {
    nodes: any[];
    edges: any[];
  };
  exposure_map: Record<string, any>;
  hex?: {
    runId?: string;
    runUrl?: string;
    projectId?: string;
    error?: string;
  } | null;
  risk_reductions?: {
    action: string;
    detail: string;
    current_risk: number;
    reduced_risk: number;
    risk_drop: number;
    category: string;
  }[];
  score_history?: ScoreEntry[];
}

interface AuditResultProps {
  result: AnalysisResult;
  username?: string;
}

const SEVERITY_CONFIG: Record<
  string,
  { color: string; bg: string; border: string; icon: string }
> = {
  critical: {
    color: "#ff4444",
    bg: "#2d0a0a",
    border: "#dc262640",
    icon: "!!",
  },
  high: { color: "#f59e0b", bg: "#2d1a0a", border: "#d9770640", icon: "!" },
  medium: { color: "#eab308", bg: "#1a1a0a", border: "#ca8a0440", icon: "~" },
  low: { color: "#4ade80", bg: "#0a1a0a", border: "#16a34a40", icon: "-" },
};

const CATEGORY_LABELS: Record<string, string> = {
  locations: "Location Match",
  timestamps: "Time Pattern",
  activities: "Activity Match",
};

export default function AuditResult({ result, username }: AuditResultProps) {
  const sortedVulns = [...result.vulnerability_map].sort((a, b) => {
    const order: Record<string, number> = {
      critical: 0,
      high: 1,
      medium: 2,
      low: 3,
    };
    return (order[a.severity] ?? 4) - (order[b.severity] ?? 4);
  });

  const hasCritical = sortedVulns.some((v) => v.severity === "critical");
  const hasHigh = sortedVulns.some((v) => v.severity === "high");

  // Severity counts for Hex dashboard
  const severityCounts = sortedVulns.reduce(
    (acc, v) => {
      const sev = v.severity as "critical" | "high" | "medium" | "low";
      acc[sev] = (acc[sev] ?? 0) + 1;
      return acc;
    },
    { critical: 0, high: 0, medium: 0, low: 0 } as Record<string, number>,
  );

  // Collect all detected entities for the entity tag cloud
  const allEntities: { label: string; type: string }[] = [];
  result.detected_entities.streets.forEach((s) =>
    allEntities.push({ label: s, type: "street" }),
  );
  result.detected_entities.places.forEach((s) =>
    allEntities.push({ label: s, type: "place" }),
  );
  result.detected_entities.businesses.forEach((s) =>
    allEntities.push({ label: s, type: "business" }),
  );
  result.detected_entities.times.forEach((s) =>
    allEntities.push({ label: s, type: "time" }),
  );
  result.detected_entities.coordinates.forEach((s) =>
    allEntities.push({ label: s, type: "coord" }),
  );

  const entityTypeColor: Record<string, string> = {
    street: "#f43f5e",
    place: "#06b6d4",
    business: "#a855f7",
    time: "#f59e0b",
    coord: "#dc2626",
  };

  return (
    <div style={{ animation: "fadeInUp 0.5s ease-out" }}>
      {/* Score Tracker — gamified history */}
      {result.score_history && <ScoreTracker history={result.score_history} />}

      {/* Breach Report Header */}
      <div
        style={{
          padding: "1.25rem 1.5rem",
          backgroundColor: hasCritical
            ? "#1a0808"
            : hasHigh
              ? "#1a1208"
              : "#0d1117",
          border: `1px solid ${hasCritical ? "#dc262630" : hasHigh ? "#d9770630" : "#1a1a1a"}`,
          borderRadius: "10px",
          marginBottom: "1.5rem",
          ...(hasCritical
            ? { animation: "pulseGlow 3s ease-in-out infinite" }
            : {}),
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
          }}
        >
          <div>
            <div
              style={{
                fontSize: "0.65rem",
                fontWeight: 600,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "#555",
                marginBottom: "0.4rem",
              }}
            >
              BREACH REPORT
            </div>
            <div
              style={{
                fontSize: "1.1rem",
                fontWeight: 700,
                color: hasCritical
                  ? "#ff4444"
                  : hasHigh
                    ? "#f59e0b"
                    : "#4ade80",
              }}
            >
              {sortedVulns.length}{" "}
              {sortedVulns.length === 1 ? "Finding" : "Findings"} Detected
            </div>
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-end",
              gap: "0.6rem",
            }}
          >
            <RiskGauge breachProbability={result.breach_probability} />
            {/* Quick-access Hex button */}
            <a
              href={
                result.hex?.runUrl ??
                `https://app.hex.tech/019d3274-b978-7110-8122-c30aea21a224/app/Aegis-032pYjM1wOXFrsi6nXOwag/latest`
              }
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.3rem",
                padding: "0.25rem 0.65rem",
                backgroundColor: "#06b6d415",
                border: "1px solid #06b6d430",
                borderRadius: "4px",
                color: "#06b6d4",
                fontSize: "0.6rem",
                fontWeight: 600,
                letterSpacing: "0.06em",
                textDecoration: "none",
                whiteSpace: "nowrap",
                cursor: "pointer",
              }}
            >
              ↗ View in Hex
            </a>
          </div>
        </div>
      </div>

      {/* ── Hex Analytics Dashboard (live embed) ── */}
      <HexDashboard
        breachProbability={result.breach_probability}
        username={username}
        totalDataPoints={result.exposure_map?.total_data_points}
        uniqueStreets={result.exposure_map?.unique_streets}
        knownLocations={result.exposure_map?.known_locations}
        trackedActivities={result.exposure_map?.tracked_activities}
        dayPatterns={result.exposure_map?.day_patterns}
        criticalCount={severityCounts.critical}
        highCount={severityCounts.high}
        mediumCount={severityCounts.medium}
        lowCount={severityCounts.low}
        finalConclusion={result.final_conclusion}
        runUrl={result.hex?.runUrl ?? null}
        runId={result.hex?.runId ?? null}
        defaultOpen
      />

      {/* Digital Shadow Scorecard */}
      <DigitalShadow
        breachProbability={result.breach_probability}
        knownAnchors={result.static_landmarks?.length ?? 0}
        routineConfidence={
          result.entity_triplets?.[0]?.confidence
            ? Math.round(result.entity_triplets[0].confidence * 100)
            : 0
        }
      />

      {/* Detected Entities */}
      {allEntities.length > 0 && (
        <div
          style={{
            padding: "1rem 1.25rem",
            backgroundColor: "#0d1117",
            border: "1px solid #1a1a1a",
            borderRadius: "10px",
            marginBottom: "1.5rem",
          }}
        >
          <div
            style={{
              fontSize: "0.65rem",
              fontWeight: 600,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "#555",
              marginBottom: "0.75rem",
            }}
          >
            EXTRACTED ENTITIES
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
            {allEntities.map((ent, i) => (
              <span
                key={`${ent.type}-${i}`}
                style={{
                  padding: "0.2rem 0.55rem",
                  backgroundColor: `${entityTypeColor[ent.type] ?? "#666"}10`,
                  border: `1px solid ${entityTypeColor[ent.type] ?? "#666"}30`,
                  borderRadius: "4px",
                  fontSize: "0.72rem",
                  color: entityTypeColor[ent.type] ?? "#666",
                }}
              >
                {ent.label}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Category Similarity Bars */}
      {Object.keys(result.category_similarity).length > 0 && (
        <div
          style={{
            padding: "1rem 1.25rem",
            backgroundColor: "#0d1117",
            border: "1px solid #1a1a1a",
            borderRadius: "10px",
            marginBottom: "1.5rem",
          }}
        >
          <div
            style={{
              fontSize: "0.65rem",
              fontWeight: 600,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "#555",
              marginBottom: "0.75rem",
            }}
          >
            CATEGORY SIMILARITY
          </div>
          {Object.entries(result.category_similarity).map(([cat, score]) => (
            <div key={cat} style={{ marginBottom: "0.6rem" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: "0.2rem",
                }}
              >
                <span style={{ color: "#888", fontSize: "0.72rem" }}>
                  {CATEGORY_LABELS[cat] ?? cat}
                </span>
                <span
                  style={{
                    color: "#06b6d4",
                    fontSize: "0.72rem",
                    fontWeight: 600,
                  }}
                >
                  {(score * 100).toFixed(1)}%
                </span>
              </div>
              <div
                style={{
                  width: "100%",
                  height: 4,
                  backgroundColor: "rgba(255,255,255,0.04)",
                  borderRadius: 2,
                }}
              >
                <div
                  style={{
                    width: `${Math.min(score * 100, 100)}%`,
                    height: "100%",
                    backgroundColor: "#06b6d4",
                    borderRadius: 2,
                    transition: "width 0.8s ease",
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Vulnerability Map */}
      {sortedVulns.length > 0 && (
        <div
          style={{
            padding: "1rem 1.25rem",
            backgroundColor: "#0d1117",
            border: "1px solid #1a1a1a",
            borderRadius: "10px",
            marginBottom: "1.5rem",
          }}
        >
          <div
            style={{
              fontSize: "0.65rem",
              fontWeight: 600,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "#555",
              marginBottom: "0.75rem",
            }}
          >
            VULNERABILITY MAP
          </div>
          <div
            style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}
          >
            {sortedVulns.map((vuln, i) => {
              const cfg = SEVERITY_CONFIG[vuln.severity] ?? SEVERITY_CONFIG.low;
              return (
                <div
                  key={i}
                  style={{
                    padding: "0.6rem 0.85rem",
                    backgroundColor: cfg.bg,
                    border: `1px solid ${cfg.border}`,
                    borderRadius: "6px",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "0.6rem",
                  }}
                >
                  <span
                    style={{
                      flexShrink: 0,
                      width: 20,
                      height: 20,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      backgroundColor: `${cfg.color}20`,
                      borderRadius: "3px",
                      color: cfg.color,
                      fontSize: "0.65rem",
                      fontWeight: 700,
                    }}
                  >
                    {cfg.icon}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "0.15rem",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "0.7rem",
                          fontWeight: 600,
                          color: cfg.color,
                          textTransform: "uppercase",
                          letterSpacing: "0.05em",
                        }}
                      >
                        {vuln.category}
                      </span>
                      <span style={{ fontSize: "0.6rem", color: "#444" }}>
                        {vuln.evidence_count} evidence
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: "0.75rem",
                        color: "#999",
                        lineHeight: 1.4,
                      }}
                    >
                      {vuln.finding}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Pattern Detection / Final Conclusion */}
      {result.final_conclusion && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          style={{
            padding: "1.25rem 1.5rem",
            backgroundColor: "#0a1018",
            border: "1px solid #06b6d420",
            borderRadius: "10px",
            marginBottom: "1.5rem",
          }}
        >
          <div
            style={{
              fontSize: "0.6rem",
              fontWeight: 600,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "#06b6d4",
              marginBottom: "1rem",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                backgroundColor: "#06b6d4",
                display: "inline-block",
                boxShadow: "0 0 6px rgba(6,182,212,0.5)",
              }}
            />
            PATTERN DETECTION
          </div>
          <div
            style={{ fontSize: "0.82rem", color: "#b0b8c0", lineHeight: 1.7 }}
          >
            {result.final_conclusion.includes("[SIGNAL DETECTED]") ? (
              // Structured conclusion format
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.85rem",
                }}
              >
                {result.final_conclusion.split("\n\n").map((block, i) => {
                  const tagMatch = block.match(/^\[([A-Z\s]+)\]:\s*([\s\S]*)/);
                  if (!tagMatch) return <span key={i}>{block}</span>;
                  const tag = tagMatch[1];
                  const body = tagMatch[2];
                  const tagColors: Record<string, string> = {
                    "SIGNAL DETECTED": "#dc2626",
                    "LEAK SOURCE": "#f59e0b",
                    FORECAST: "#06b6d4",
                  };
                  return (
                    <div key={i}>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "0.15rem 0.5rem",
                          backgroundColor: `${tagColors[tag] ?? "#555"}15`,
                          border: `1px solid ${tagColors[tag] ?? "#555"}30`,
                          borderRadius: "3px",
                          fontSize: "0.6rem",
                          fontWeight: 700,
                          letterSpacing: "0.08em",
                          color: tagColors[tag] ?? "#555",
                          marginBottom: "0.35rem",
                        }}
                      >
                        {tag}
                      </span>
                      <div
                        style={{
                          fontSize: "0.8rem",
                          color: "#999",
                          lineHeight: 1.6,
                        }}
                      >
                        {i === 2 ? (
                          <TypingEffect text={body} speed={12} />
                        ) : (
                          body
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <TypingEffect text={result.final_conclusion} speed={12} />
            )}
          </div>
        </motion.div>
      )}

      {/* Stalker's Web + Privacy Improvements */}
      <VisualizationWrapper
        web={result.web}
        improvements={result.risk_reductions}
      />

      {/* Signals: OCR + EXIF */}
      {result.signals.ocr_text && (
        <div
          style={{
            padding: "0.85rem 1.25rem",
            backgroundColor: "#0d1117",
            border: "1px solid #1a1a1a",
            borderRadius: "10px",
            marginBottom: "1rem",
          }}
        >
          <div
            style={{
              fontSize: "0.65rem",
              fontWeight: 600,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "#06b6d4",
              marginBottom: "0.5rem",
            }}
          >
            OCR EXTRACTED TEXT
          </div>
          <p
            style={{
              color: "#777",
              fontSize: "0.78rem",
              margin: 0,
              whiteSpace: "pre-wrap",
              lineHeight: 1.5,
            }}
          >
            {result.signals.ocr_text}
          </p>
        </div>
      )}
      {result.signals.exif_metadata && (
        <div
          style={{
            padding: "0.85rem 1.25rem",
            backgroundColor: "#0d1117",
            border: "1px solid #1a1a1a",
            borderRadius: "10px",
            marginBottom: "1rem",
          }}
        >
          <div
            style={{
              fontSize: "0.65rem",
              fontWeight: 600,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "#f43f5e",
              marginBottom: "0.5rem",
            }}
          >
            EXIF METADATA LEAKED
          </div>
          <pre
            style={{
              color: "#777",
              fontSize: "0.72rem",
              margin: 0,
              fontFamily: "inherit",
              whiteSpace: "pre-wrap",
            }}
          >
            {JSON.stringify(result.signals.exif_metadata, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
