"use client";

interface ThreatBannerProps {
  riskLevel: string;
  maxSimilarity: number;
  breachProbability: number;
  entityScores: Record<string, number>;
}

const RISK_CONFIG: Record<string, { bg: string; border: string; text: string; glow: string }> = {
  CRITICAL: { bg: "#2d0a0a", border: "#dc2626", text: "#ff4444", glow: "0 0 30px rgba(220,38,38,0.4)" },
  HIGH:     { bg: "#2d1a0a", border: "#d97706", text: "#f59e0b", glow: "0 0 20px rgba(217,119,6,0.3)" },
  MEDIUM:   { bg: "#1a1a0a", border: "#ca8a04", text: "#eab308", glow: "none" },
  LOW:      { bg: "#0a1a0a", border: "#16a34a", text: "#4ade80", glow: "none" },
};

const ENTITY_LABELS: Record<string, string> = {
  daily_route: "Daily Route",
  home: "Home",
  work: "Work",
  family: "Family",
  general: "General",
};

export default function ThreatBanner({ riskLevel, maxSimilarity, breachProbability, entityScores }: ThreatBannerProps) {
  const config = RISK_CONFIG[riskLevel] ?? RISK_CONFIG.LOW;

  return (
    <div
      style={{
        backgroundColor: config.bg,
        border: `1px solid ${config.border}`,
        borderRadius: "10px",
        padding: "1.25rem 1.5rem",
        marginBottom: "1.5rem",
        boxShadow: config.glow,
      }}
    >
      {/* Top row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <span style={{ fontSize: "1.3rem" }}>
            {riskLevel === "CRITICAL" || riskLevel === "HIGH" ? "⚠️" : "🔍"}
          </span>
          <span
            style={{
              fontSize: "1.1rem",
              fontWeight: 700,
              color: config.text,
              letterSpacing: "0.05em",
              textTransform: "uppercase",
            }}
          >
            Threat Level: {riskLevel}
          </span>
        </div>
        <span style={{ color: "#888", fontSize: "0.8rem", fontFamily: "monospace" }}>
          similarity {(maxSimilarity * 100).toFixed(1)}%
        </span>
      </div>

      {/* Breach probability bar */}
      <div style={{ marginBottom: "0.75rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.3rem" }}>
          <span style={{ color: "#999", fontSize: "0.75rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Breach Probability
          </span>
          <span style={{ color: config.text, fontSize: "1rem", fontWeight: 700, fontFamily: "monospace" }}>
            {breachProbability.toFixed(1)}%
          </span>
        </div>
        <div style={{ width: "100%", height: 6, backgroundColor: "rgba(255,255,255,0.05)", borderRadius: 3 }}>
          <div
            style={{
              width: `${Math.min(breachProbability, 100)}%`,
              height: "100%",
              backgroundColor: config.text,
              borderRadius: 3,
              transition: "width 0.5s ease",
            }}
          />
        </div>
      </div>

      {/* Sensitive entity breakdown */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
        {Object.entries(entityScores)
          .filter(([, score]) => score > 0)
          .sort(([, a], [, b]) => b - a)
          .map(([entity, score]) => (
            <span
              key={entity}
              style={{
                padding: "0.25rem 0.6rem",
                backgroundColor: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "4px",
                fontSize: "0.75rem",
                color: "#aaa",
                fontFamily: "monospace",
              }}
            >
              {ENTITY_LABELS[entity] ?? entity}: {(score * 100).toFixed(0)}%
            </span>
          ))}
      </div>

      {/* Warning text */}
      {(riskLevel === "CRITICAL" || riskLevel === "HIGH") && (
        <p style={{ color: "#999", fontSize: "0.8rem", margin: "0.75rem 0 0", lineHeight: 1.4 }}>
          Identity Links detected. This post, combined with your existing digital footprint,
          could reveal sensitive entities to a motivated adversary.
        </p>
      )}
    </div>
  );
}
