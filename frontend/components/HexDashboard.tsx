"use client";

import { useState, useEffect, useRef } from "react";

const HEX_APP_URL =
  "https://app.hex.tech/019d3274-b978-7110-8122-c30aea21a224/app/Aegis-032pYjM1wOXFrsi6nXOwag/latest";

const HEX_EMBED_URL =
  "https://app.hex.tech/019d3274-b978-7110-8122-c30aea21a224/app/032pYjM1wOXFrsi6nXOwag/latest?embedded=true";

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
  runUrl?: string | null;
  runId?: string | null;
  /** If true, show the panel expanded by default */
  defaultOpen?: boolean;
}

function buildHexUrl(props: HexDashboardProps): string {
  const params = new URLSearchParams();

  if (props.breachProbability !== undefined)
    params.set(
      "breach_probability",
      String(Math.round(props.breachProbability)),
    );
  if (props.username) params.set("username", props.username);
  if (props.totalDataPoints !== undefined)
    params.set("total_data_points", String(props.totalDataPoints));
  if (props.uniqueStreets !== undefined)
    params.set("unique_streets", String(props.uniqueStreets));
  if (props.knownLocations !== undefined)
    params.set("known_locations", String(props.knownLocations));
  if (props.trackedActivities !== undefined)
    params.set("tracked_activities", String(props.trackedActivities));
  if (props.dayPatterns !== undefined)
    params.set("day_patterns", String(props.dayPatterns));
  if (props.criticalCount !== undefined)
    params.set("critical_count", String(props.criticalCount));
  if (props.highCount !== undefined)
    params.set("high_count", String(props.highCount));
  if (props.mediumCount !== undefined)
    params.set("medium_count", String(props.mediumCount));
  if (props.lowCount !== undefined)
    params.set("low_count", String(props.lowCount));

  const query = params.toString();
  // Always use the embed URL as base; append extra params after embedded=true
  const base = HEX_EMBED_URL;
  return query ? `${base}&${query}` : base;
}

export default function HexDashboard(props: HexDashboardProps) {
  const { defaultOpen = false, runUrl, runId } = props;
  const [open, setOpen] = useState(defaultOpen);
  const [iframeKey, setIframeKey] = useState(0);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [iframeError, setIframeError] = useState(false);
  const prevUrlRef = useRef<string>("");

  const hexUrl = buildHexUrl(props);

  // Re-mount iframe whenever the key data changes
  useEffect(() => {
    if (hexUrl !== prevUrlRef.current) {
      prevUrlRef.current = hexUrl;
      setIframeKey((k) => k + 1);
      setIframeLoaded(false);
      setIframeError(false);
    }
  }, [hexUrl]);

  // Auto-open when new results arrive
  useEffect(() => {
    if (props.breachProbability !== undefined) {
      setOpen(true);
    }
  }, [props.breachProbability, props.username]);

  const riskColor =
    (props.breachProbability ?? 0) >= 80
      ? "#dc2626"
      : (props.breachProbability ?? 0) >= 50
        ? "#f59e0b"
        : "#16a34a";

  const riskLabel =
    (props.breachProbability ?? 0) >= 80
      ? "CRITICAL"
      : (props.breachProbability ?? 0) >= 50
        ? "ELEVATED"
        : "NOMINAL";

  return (
    <div
      style={{
        marginTop: "1.5rem",
        border: `1px solid ${open ? "#06b6d430" : "#1a1a1a"}`,
        borderRadius: "12px",
        overflow: "hidden",
        transition: "border-color 0.3s ease",
        backgroundColor: "#0a0d12",
      }}
    >
      {/* ── Header / toggle bar ── */}
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
        {/* Left: icon + title */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: "#06b6d4",
              boxShadow: open ? "0 0 8px rgba(6,182,212,0.6)" : "none",
              transition: "box-shadow 0.3s ease",
              flexShrink: 0,
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

          {props.breachProbability !== undefined && (
            <span
              style={{
                padding: "0.1rem 0.45rem",
                backgroundColor: `${riskColor}18`,
                border: `1px solid ${riskColor}35`,
                borderRadius: "3px",
                fontSize: "0.55rem",
                fontWeight: 700,
                letterSpacing: "0.08em",
                color: riskColor,
              }}
            >
              {riskLabel} · {Math.round(props.breachProbability)}%
            </span>
          )}

          {runId && (
            <span
              style={{
                fontSize: "0.55rem",
                color: "#16a34a",
                letterSpacing: "0.06em",
              }}
            >
              run #{runId.slice(0, 8)}
            </span>
          )}
        </div>

        {/* Right: action buttons + chevron */}
        <div
          style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Refresh iframe */}
          {open && (
            <button
              title="Reload dashboard"
              onClick={() => {
                setIframeKey((k) => k + 1);
                setIframeLoaded(false);
                setIframeError(false);
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

          {/* Open in Hex (new tab) */}
          <a
            href={runUrl ?? hexUrl}
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

          {/* Chevron */}
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

      {/* ── Collapsible body ── */}
      <div
        style={{
          maxHeight: open ? "700px" : "0px",
          overflow: "hidden",
          transition: "max-height 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
        }}
      >
        {/* Stats strip (visible above iframe) */}
        {props.breachProbability !== undefined && (
          <div
            style={{
              display: "flex",
              gap: "1.5rem",
              padding: "0.6rem 1.25rem",
              backgroundColor: "#0d1117",
              borderBottom: "1px solid #1a1a1a",
              overflowX: "auto",
            }}
          >
            {[
              {
                label: "Breach Risk",
                value: `${Math.round(props.breachProbability)}%`,
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
              {
                label: "Critical",
                value: props.criticalCount ?? 0,
                color: "#dc2626",
              },
              { label: "High", value: props.highCount ?? 0, color: "#f59e0b" },
              {
                label: "Medium",
                value: props.mediumCount ?? 0,
                color: "#eab308",
              },
              { label: "Low", value: props.lowCount ?? 0, color: "#4ade80" },
            ].map((stat) => (
              <div key={stat.label} style={{ flexShrink: 0 }}>
                <div
                  style={{
                    color: "#444",
                    fontSize: "0.5rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    marginBottom: "0.15rem",
                  }}
                >
                  {stat.label}
                </div>
                <div
                  style={{
                    color: stat.color,
                    fontSize: "0.95rem",
                    fontWeight: 700,
                    lineHeight: 1,
                  }}
                >
                  {stat.value}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* iframe wrapper */}
        <div style={{ position: "relative", width: "100%", height: 620 }}>
          {/* Loading overlay */}
          {!iframeLoaded && !iframeError && (
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
                  fontSize: "0.68rem",
                  color: "#444",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                }}
              >
                Loading Hex dashboard…
              </span>
            </div>
          )}

          {/* Error / blocked state */}
          {iframeError && (
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
                padding: "2rem",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: "1.5rem" }}>📊</div>
              <div
                style={{
                  fontSize: "0.72rem",
                  color: "#555",
                  letterSpacing: "0.06em",
                  lineHeight: 1.6,
                  maxWidth: 340,
                }}
              >
                Hex prevents direct embedding via iframe (X-Frame-Options). Use
                the button below to open your live dashboard in a new tab — it
                will reflect the latest analysis data automatically.
              </div>
              <a
                href={runUrl ?? hexUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  marginTop: "0.5rem",
                  padding: "0.55rem 1.4rem",
                  backgroundColor: "#06b6d420",
                  border: "1px solid #06b6d450",
                  borderRadius: "6px",
                  color: "#06b6d4",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  letterSpacing: "0.06em",
                  textDecoration: "none",
                  cursor: "pointer",
                }}
              >
                ↗ Open Hex Dashboard
              </a>
              {props.finalConclusion && (
                <p
                  style={{
                    marginTop: "0.75rem",
                    color: "#444",
                    fontSize: "0.7rem",
                    lineHeight: 1.5,
                    maxWidth: 380,
                    fontStyle: "italic",
                  }}
                >
                  "{props.finalConclusion.slice(0, 180)}
                  {props.finalConclusion.length > 180 ? "…" : ""}"
                </p>
              )}
            </div>
          )}

          {/* Hex embed stylesheet */}
          <link
            rel="stylesheet"
            href="https://static.hex.site/embed/embedStyles.css"
          />

          <div className="hex-embed" style={{ width: "100%", height: "620px" }}>
            <iframe
              key={iframeKey}
              src={hexUrl}
              title="Aegis Hex Analytics Dashboard"
              width="100%"
              height="620"
              style={{
                border: "none",
                display: "block",
                opacity: iframeLoaded ? 1 : 0,
                transition: "opacity 0.4s ease",
              }}
              allow="fullscreen"
              onLoad={() => {
                setIframeLoaded(true);
                setIframeError(false);
              }}
              onError={() => {
                setIframeLoaded(false);
                setIframeError(true);
              }}
            />
            <a
              href="https://hex.tech/?embed"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "block",
                marginTop: "0.25rem",
                textAlign: "right",
              }}
            >
              <img
                src="https://static.hex.site/embed/hex-logo-embed.png"
                alt="Hex - a modern data workspace for collaborative notebooks, data apps, dashboards, and reports."
                style={{ height: 20 }}
              />
            </a>
          </div>
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
            Powered by Hex · Data updates on each analysis run
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

      {/* Global keyframe for spinner */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
