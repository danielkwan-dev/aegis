"use client";

import RiskGauge from "./RiskGauge";
import TypingEffect from "./TypingEffect";
import VisualizationWrapper from "./VisualizationWrapper";

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
}

interface AuditResultProps {
  result: AnalysisResult;
}

const SEVERITY_CONFIG: Record<string, { color: string; bg: string; border: string; icon: string }> = {
  critical: { color: "#ff4444", bg: "#2d0a0a", border: "#dc262640", icon: "!!" },
  high:     { color: "#f59e0b", bg: "#2d1a0a", border: "#d9770640", icon: "!" },
  medium:   { color: "#eab308", bg: "#1a1a0a", border: "#ca8a0440", icon: "~" },
  low:      { color: "#4ade80", bg: "#0a1a0a", border: "#16a34a40", icon: "-" },
};

const CATEGORY_LABELS: Record<string, string> = {
  locations: "Location Match",
  timestamps: "Time Pattern",
  activities: "Activity Match",
};

export default function AuditResult({ result }: AuditResultProps) {
  const sortedVulns = [...result.vulnerability_map].sort((a, b) => {
    const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
    return (order[a.severity] ?? 4) - (order[b.severity] ?? 4);
  });

  const hasCritical = sortedVulns.some((v) => v.severity === "critical");
  const hasHigh = sortedVulns.some((v) => v.severity === "high");

  // Collect all detected entities for the entity tag cloud
  const allEntities: { label: string; type: string }[] = [];
  result.detected_entities.streets.forEach((s) => allEntities.push({ label: s, type: "street" }));
  result.detected_entities.places.forEach((s) => allEntities.push({ label: s, type: "place" }));
  result.detected_entities.businesses.forEach((s) => allEntities.push({ label: s, type: "business" }));
  result.detected_entities.times.forEach((s) => allEntities.push({ label: s, type: "time" }));
  result.detected_entities.coordinates.forEach((s) => allEntities.push({ label: s, type: "coord" }));

  const entityTypeColor: Record<string, string> = {
    street: "#f43f5e",
    place: "#06b6d4",
    business: "#a855f7",
    time: "#f59e0b",
    coord: "#dc2626",
  };

  return (
    <div style={{ animation: "fadeInUp 0.5s ease-out" }}>
      {/* Breach Report Header */}
      <div
        style={{
          padding: "1.25rem 1.5rem",
          backgroundColor: hasCritical ? "#1a0808" : hasHigh ? "#1a1208" : "#0d1117",
          border: `1px solid ${hasCritical ? "#dc262630" : hasHigh ? "#d9770630" : "#1a1a1a"}`,
          borderRadius: "10px",
          marginBottom: "1.5rem",
          ...(hasCritical ? { animation: "pulseGlow 3s ease-in-out infinite" } : {}),
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
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
                color: hasCritical ? "#ff4444" : hasHigh ? "#f59e0b" : "#4ade80",
              }}
            >
              {sortedVulns.length} {sortedVulns.length === 1 ? "Finding" : "Findings"} Detected
            </div>
          </div>
          <RiskGauge breachProbability={result.breach_probability} />
        </div>
      </div>

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
                <span style={{ color: "#06b6d4", fontSize: "0.72rem", fontWeight: 600 }}>
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
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
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
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.15rem" }}>
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
                    <div style={{ fontSize: "0.75rem", color: "#999", lineHeight: 1.4 }}>
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
        <div
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
              fontSize: "0.65rem",
              fontWeight: 600,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "#06b6d4",
              marginBottom: "0.75rem",
            }}
          >
            PATTERN DETECTION
          </div>
          <div style={{ fontSize: "0.85rem", color: "#b0b8c0", lineHeight: 1.6 }}>
            <TypingEffect text={result.final_conclusion} speed={15} />
          </div>
        </div>
      )}

      {/* Stalker's Web + Hex */}
      <VisualizationWrapper web={result.web} hex={result.hex} />

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
          <p style={{ color: "#777", fontSize: "0.78rem", margin: 0, whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
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
          <pre style={{ color: "#777", fontSize: "0.72rem", margin: 0, fontFamily: "inherit", whiteSpace: "pre-wrap" }}>
            {JSON.stringify(result.signals.exif_metadata, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
