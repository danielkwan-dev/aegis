"use client";

import { useState, useEffect, useRef } from "react";

const HEX_APP_URL =
  "https://app.hex.tech/019d3274-b978-7110-8122-c30aea21a224/app/Aegis-032pYjM1wOXFrsi6nXOwag/latest";

// The 4 hardcoded demo stages — cycles through on each analysis run
const DEMO_STAGES = [
  {
    breach: 100,
    label: "CRITICAL",
    color: "#dc2626",
    critical: 4,
    high: 3,
    medium: 2,
    low: 0,
    tagline: "Maximum exposure detected — immediate action required.",
  },
  {
    breach: 60,
    label: "ELEVATED",
    color: "#f59e0b",
    critical: 2,
    high: 3,
    medium: 3,
    low: 1,
    tagline: "Significant risk remains — several leaks still active.",
  },
  {
    breach: 35,
    label: "MODERATE",
    color: "#eab308",
    critical: 0,
    high: 2,
    medium: 4,
    low: 2,
    tagline: "Improving — key location patterns still exposed.",
  },
  {
    breach: 15,
    label: "NOMINAL",
    color: "#16a34a",
    critical: 0,
    high: 0,
    medium: 2,
    low: 3,
    tagline: "Low risk — minor residual signals only.",
  },
];

export interface HexDashboardProps {
  breachProbability?: number;
  username?: string;
  totalDataPoints?: number;
  uniqueStreets?: number;
  knownLocations?: number;
  trackedActivities?: number;
  dayPatterns?: number;
  criticalCount?: number;
  highCount?: number;
  mediumCount?: number;
  lowCount?: number;
  finalConclusion?: string;
  runId?: string | null;
  runUrl?: string | null;
  defaultOpen?: boolean;
}

export default function HexDashboard(props: HexDashboardProps) {
  const { defaultOpen = false } = props;

  // Which demo stage we're on (0-3), persisted across renders via ref
  const stageIndexRef = useRef<number>(-1);
  const prevTriggerRef = useRef<string>("");

  const [open, setOpen] = useState(defaultOpen);
  const [stageIndex, setStageIndex] = useState<number>(-1);
  const [iframeKey, setIframeKey] = useState(0);
  const [iframeVisible, setIframeVisible] = useState(false);

  // Advance to next stage each time a new analysis result arrives
  useEffect(() => {
    if (props.breachProbability === undefined) return;

    const triggerKey = `${props.breachProbability}-${props.username ?? ""}-${props.totalDataPoints ?? ""}`;
    if (triggerKey === prevTriggerRef.current) return;
    prevTriggerRef.current = triggerKey;

    const next = (stageIndexRef.current + 1) % DEMO_STAGES.length;
    stageIndexRef.current = next;
    setStageIndex(next);
    setIframeKey((k) => k + 1);
    setIframeVisible(false);
    setOpen(true);
  }, [props.breachProbability, props.username, props.totalDataPoints]);

  const stage = stageIndex >= 0 ? DEMO_STAGES[stageIndex] : null;

  const riskColor = stage?.color ?? "#06b6d4";
  const riskLabel = stage?.label ?? "—";
  const breachPct = stage?.breach ?? 0;

  const iframeSrc = HEX_APP_URL;

  return (
    <div
      style={{
        marginTop: "1.5rem",
        border: `1px solid ${open && stage ? `${riskColor}35` : "#1a1a1a"}`,
        borderRadius: "12px",
        overflow: "hidden",
        transition: "border-color 0.4s ease",
        backgroundColor: "#0a0d12",
      }}
    >
      {/* ── Header bar ── */}
      <div
        onClick={() => setOpen((o) => !o)}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0.85rem 1.25rem",
          cursor: "pointer",
          userSelect: "none",
          backgroundColor: open ? "#0d1520" : "#0a0d12",
          transition: "background-color 0.2s ease",
          borderBottom: open ? "1px solid #06b6d415" : "none",
        }}
      >
        {/* Left */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.65rem",
            flexWrap: "wrap",
          }}
        >
          {/* Status dot */}
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              flexShrink: 0,
              backgroundColor: stage ? riskColor : "#333",
              boxShadow: stage ? `0 0 8px ${riskColor}80` : "none",
              transition: "background-color 0.4s ease, box-shadow 0.4s ease",
            }}
          />

          <span
            style={{
              fontSize: "0.65rem",
              fontWeight: 700,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "#06b6d4",
            }}
          >
            Hex Analytics Dashboard
          </span>

          {/* Risk badge — updates each run */}
          {stage && (
            <span
              style={{
                padding: "0.1rem 0.5rem",
                backgroundColor: `${riskColor}18`,
                border: `1px solid ${riskColor}40`,
                borderRadius: "3px",
                fontSize: "0.58rem",
                fontWeight: 700,
                letterSpacing: "0.08em",
                color: riskColor,
                transition: "all 0.4s ease",
              }}
            >
              {riskLabel} · {breachPct}%
            </span>
          )}

          {/* Run counter badge */}
          {stageIndex >= 0 && (
            <span
              style={{
                fontSize: "0.55rem",
                color: "#444",
                letterSpacing: "0.06em",
              }}
            >
              analysis #{stageIndex + 1}
            </span>
          )}
        </div>

        {/* Right */}
        <div
          style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}
          onClick={(e) => e.stopPropagation()}
        >
          {open && (
            <button
              title="Reload dashboard"
              onClick={() => {
                setIframeKey((k) => k + 1);
                setIframeVisible(false);
              }}
              style={{
                padding: "0.25rem 0.6rem",
                backgroundColor: "#141618",
                border: "1px solid #1e2228",
                borderRadius: "4px",
                color: "#555",
                cursor: "pointer",
                fontSize: "0.65rem",
                fontFamily: "inherit",
                letterSpacing: "0.05em",
                display: "flex",
                alignItems: "center",
                gap: "0.3rem",
              }}
            >
              ↺ Reload
            </button>
          )}

          <a
            href={HEX_APP_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              padding: "0.25rem 0.7rem",
              backgroundColor: "#06b6d415",
              border: "1px solid #06b6d430",
              borderRadius: "4px",
              color: "#06b6d4",
              cursor: "pointer",
              fontSize: "0.65rem",
              fontFamily: "inherit",
              letterSpacing: "0.05em",
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              gap: "0.3rem",
              whiteSpace: "nowrap",
            }}
          >
            ↗ Open in Hex
          </a>

          <span
            onClick={() => setOpen((o) => !o)}
            style={{
              color: "#333",
              fontSize: "0.8rem",
              transform: open ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 0.25s ease",
              cursor: "pointer",
              lineHeight: 1,
            }}
          >
            ▾
          </span>
        </div>
      </div>

      {/* ── Body ── */}
      <div
        style={{
          maxHeight: open ? "800px" : "0px",
          overflow: "hidden",
          transition: "max-height 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
        }}
      >
        {/* Stats strip */}
        {stage && (
          <div
            style={{
              display: "flex",
              gap: "1.5rem",
              padding: "0.65rem 1.25rem",
              backgroundColor: "#0d1117",
              borderBottom: "1px solid #1a1a1a",
              overflowX: "auto",
            }}
          >
            {[
              {
                label: "Breach Risk",
                value: `${breachPct}%`,
                color: riskColor,
              },
              {
                label: "Data Points",
                value: props.totalDataPoints ?? "—",
                color: "#c8ccd0",
              },
              {
                label: "Streets",
                value: props.uniqueStreets ?? "—",
                color: "#c8ccd0",
              },
              {
                label: "Locations",
                value: props.knownLocations ?? "—",
                color: "#c8ccd0",
              },
              {
                label: "Activities",
                value: props.trackedActivities ?? "—",
                color: "#c8ccd0",
              },
              { label: "Critical", value: stage.critical, color: "#dc2626" },
              { label: "High", value: stage.high, color: "#f59e0b" },
              { label: "Medium", value: stage.medium, color: "#eab308" },
              { label: "Low", value: stage.low, color: "#4ade80" },
            ].map((s) => (
              <div key={s.label} style={{ flexShrink: 0 }}>
                <div
                  style={{
                    color: "#444",
                    fontSize: "0.5rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    marginBottom: "0.15rem",
                  }}
                >
                  {s.label}
                </div>
                <div
                  style={{
                    color: s.color,
                    fontSize: "0.95rem",
                    fontWeight: 700,
                    lineHeight: 1,
                    transition: "color 0.4s ease",
                  }}
                >
                  {s.value}
                </div>
              </div>
            ))}

            {/* Progress bar across all 4 stages */}
            <div
              style={{
                marginLeft: "auto",
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                minWidth: 120,
              }}
            >
              <div
                style={{
                  color: "#444",
                  fontSize: "0.5rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  marginBottom: "0.3rem",
                }}
              >
                Analysis progress
              </div>
              <div style={{ display: "flex", gap: "0.3rem" }}>
                {DEMO_STAGES.map((s, i) => (
                  <div
                    key={i}
                    style={{
                      flex: 1,
                      height: 4,
                      borderRadius: 2,
                      backgroundColor: i <= stageIndex ? s.color : "#1e2228",
                      transition: "background-color 0.4s ease",
                    }}
                  />
                ))}
              </div>
              <div
                style={{
                  color: "#333",
                  fontSize: "0.5rem",
                  marginTop: "0.25rem",
                }}
              >
                {stageIndex + 1} / {DEMO_STAGES.length}
              </div>
            </div>
          </div>
        )}

        {/* Tagline */}
        {stage && (
          <div
            style={{
              padding: "0.5rem 1.25rem",
              backgroundColor: `${riskColor}08`,
              borderBottom: "1px solid #1a1a1a",
              fontSize: "0.68rem",
              color: riskColor,
              letterSpacing: "0.04em",
              fontStyle: "italic",
              transition: "all 0.4s ease",
            }}
          >
            {stage.tagline}
          </div>
        )}

        {/* iframe wrapper */}
        <div style={{ position: "relative", width: "100%", height: 620 }}>
          {/* Loading overlay */}
          {!iframeVisible && (
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: "#0a0d12",
                gap: "1rem",
                zIndex: 2,
              }}
            >
              <div
                style={{
                  width: 32,
                  height: 32,
                  border: "2px solid #06b6d420",
                  borderTop: "2px solid #06b6d4",
                  borderRadius: "50%",
                  animation: "spin 0.9s linear infinite",
                }}
              />
              <span
                style={{
                  fontSize: "0.65rem",
                  color: "#444",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                }}
              >
                Loading Hex dashboard…
              </span>
            </div>
          )}

          <iframe
            key={iframeKey}
            src={iframeSrc}
            title="Aegis Hex Analytics Dashboard"
            width="100%"
            height="620"
            style={{
              border: "none",
              display: "block",
              opacity: iframeVisible ? 1 : 0,
              transition: "opacity 0.5s ease",
            }}
            allow="fullscreen"
            onLoad={() => setIframeVisible(true)}
            onError={() => setIframeVisible(false)}
          />

          {/* Always-visible Open in Hex button overlay */}
          {iframeVisible && (
            <div
              style={{
                position: "absolute",
                bottom: "1rem",
                right: "1rem",
                zIndex: 10,
              }}
            >
              <a
                href={HEX_APP_URL}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.3rem",
                  padding: "0.4rem 0.9rem",
                  backgroundColor: "#06b6d4",
                  borderRadius: "5px",
                  color: "#000",
                  fontSize: "0.68rem",
                  fontWeight: 700,
                  letterSpacing: "0.05em",
                  textDecoration: "none",
                  boxShadow: "0 2px 12px rgba(6,182,212,0.4)",
                }}
              >
                ↗ Open in Hex
              </a>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "0.5rem 1.25rem",
            borderTop: "1px solid #141618",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span
            style={{
              fontSize: "0.55rem",
              color: "#222",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Powered by Hex · Updates on every analysis run
          </span>
          <a
            href={HEX_APP_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              fontSize: "0.55rem",
              color: "#333",
              letterSpacing: "0.06em",
              textDecoration: "none",
            }}
          >
            hex.tech ↗
          </a>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
