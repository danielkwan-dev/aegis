"use client";

import { useState, useEffect, useRef, useCallback } from "react";

const HEX_APP_URL =
  "https://app.hex.tech/019d3274-b978-7110-8122-c30aea21a224/app/Aegis-032pYjM1wOXFrsi6nXOwag/latest";

const API_URL =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    : "http://localhost:8000";

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
  /** runId returned by the backend after triggering a Hex run */
  runId?: string | null;
  /** runUrl returned by the backend (used as fallback) */
  runUrl?: string | null;
  defaultOpen?: boolean;
}

type RunPhase =
  | "idle" // no run triggered yet
  | "polling" // waiting for Hex run to complete
  | "ready" // run completed, iframe loaded with live URL
  | "error" // run failed or API error
  | "blocked"; // iframe loaded but XFO blocked it

function StatStrip(props: HexDashboardProps & { riskColor: string }) {
  const { breachProbability, riskColor } = props;
  if (breachProbability === undefined) return null;
  const stats = [
    {
      label: "Breach Risk",
      value: `${Math.round(breachProbability)}%`,
      color: riskColor,
    },
    {
      label: "Data Points",
      value: props.totalDataPoints ?? "—",
      color: "#c8ccd0",
    },
    { label: "Streets", value: props.uniqueStreets ?? "—", color: "#c8ccd0" },
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
    { label: "Critical", value: props.criticalCount ?? 0, color: "#dc2626" },
    { label: "High", value: props.highCount ?? 0, color: "#f59e0b" },
    { label: "Medium", value: props.mediumCount ?? 0, color: "#eab308" },
    { label: "Low", value: props.lowCount ?? 0, color: "#4ade80" },
  ];
  return (
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
      {stats.map((s) => (
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
            }}
          >
            {s.value}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function HexDashboard(props: HexDashboardProps) {
  const { defaultOpen = false, runId, runUrl: fallbackRunUrl } = props;

  const [open, setOpen] = useState(defaultOpen);
  const [phase, setPhase] = useState<RunPhase>("idle");
  const [liveRunUrl, setLiveRunUrl] = useState<string | null>(null);
  const [pollSeconds, setPollSeconds] = useState(0);
  const [iframeKey, setIframeKey] = useState(0);
  const [iframeVisible, setIframeVisible] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevRunId = useRef<string | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  // Start polling whenever a new runId arrives
  useEffect(() => {
    if (!runId || runId === prevRunId.current) return;
    prevRunId.current = runId;

    // Reset state for new run
    setPhase("polling");
    setLiveRunUrl(null);
    setIframeVisible(false);
    setPollSeconds(0);
    setStatusMsg("Hex run triggered — waiting for results…");
    setOpen(true);

    stopPolling();

    // Tick counter so the user sees "Xm Ys elapsed"
    tickRef.current = setInterval(() => {
      setPollSeconds((s) => s + 1);
    }, 1000);

    // Poll /api/hex-run-status/:runId every 4 s
    const doPoll = async () => {
      try {
        const res = await fetch(`${API_URL}/api/hex-run-status/${runId}`);
        const data = await res.json();
        const status: string = data.status ?? "UNKNOWN";

        setStatusMsg(`Hex run status: ${status}`);

        if (status === "COMPLETED") {
          stopPolling();
          const url: string = data.runUrl || fallbackRunUrl || HEX_APP_URL;
          setLiveRunUrl(url);
          setPhase("ready");
          setIframeKey((k) => k + 1);
          setIframeVisible(false); // will fade in on iframe load
        } else if (
          status === "FAILED" ||
          status === "KILLED" ||
          status === "ERROR"
        ) {
          stopPolling();
          // Fall back to the static app URL so something is still shown
          setLiveRunUrl(fallbackRunUrl || HEX_APP_URL);
          setPhase("error");
          setIframeKey((k) => k + 1);
          setIframeVisible(false);
          setStatusMsg(
            `Run ${status.toLowerCase()} — showing last published version`,
          );
        }
        // PENDING / RUNNING → keep polling
      } catch {
        // Network hiccup — keep trying
      }
    };

    doPoll(); // immediate first check
    pollRef.current = setInterval(doPoll, 4000);

    return () => stopPolling();
  }, [runId, fallbackRunUrl, stopPolling]);

  // Auto-open when new results arrive even without a runId
  useEffect(() => {
    if (props.breachProbability !== undefined && !runId) {
      setOpen(true);
    }
  }, [props.breachProbability, props.username, runId]);

  // Cleanup on unmount
  useEffect(() => () => stopPolling(), [stopPolling]);

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

  // The URL the iframe should actually load
  const iframeSrc = liveRunUrl ?? HEX_APP_URL;

  // Elapsed time string
  const elapsed =
    pollSeconds > 0
      ? pollSeconds < 60
        ? `${pollSeconds}s`
        : `${Math.floor(pollSeconds / 60)}m ${pollSeconds % 60}s`
      : null;

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
              backgroundColor:
                phase === "polling"
                  ? "#f59e0b"
                  : phase === "ready"
                    ? "#16a34a"
                    : phase === "error"
                      ? "#dc2626"
                      : "#06b6d4",
              boxShadow:
                phase === "polling"
                  ? "0 0 8px rgba(245,158,11,0.7)"
                  : open
                    ? "0 0 8px rgba(6,182,212,0.6)"
                    : "none",
              animation:
                phase === "polling"
                  ? "hexPulse 1.2s ease-in-out infinite"
                  : "none",
              transition: "background-color 0.3s ease, box-shadow 0.3s ease",
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

          {/* Risk badge */}
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

          {/* Phase badge */}
          {phase === "polling" && (
            <span
              style={{
                fontSize: "0.55rem",
                color: "#f59e0b",
                letterSpacing: "0.06em",
                display: "flex",
                alignItems: "center",
                gap: "0.3rem",
              }}
            >
              <span
                style={{
                  display: "inline-block",
                  width: 6,
                  height: 6,
                  border: "1px solid #f59e0b80",
                  borderTop: "1px solid #f59e0b",
                  borderRadius: "50%",
                  animation: "spin 0.9s linear infinite",
                }}
              />
              Computing{elapsed ? ` · ${elapsed}` : "…"}
            </span>
          )}

          {phase === "ready" && runId && (
            <span
              style={{
                fontSize: "0.55rem",
                color: "#16a34a",
                letterSpacing: "0.06em",
              }}
            >
              ✓ run #{runId.slice(0, 8)} complete
            </span>
          )}

          {phase === "error" && (
            <span
              style={{
                fontSize: "0.55rem",
                color: "#dc2626",
                letterSpacing: "0.06em",
              }}
            >
              Run failed · showing last version
            </span>
          )}
        </div>

        {/* Right */}
        <div
          style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}
          onClick={(e) => e.stopPropagation()}
        >
          {open && phase !== "polling" && (
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
            href={liveRunUrl ?? fallbackRunUrl ?? HEX_APP_URL}
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
          maxHeight: open ? "760px" : "0px",
          overflow: "hidden",
          transition: "max-height 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
        }}
      >
        <StatStrip {...props} riskColor={riskColor} />

        {/* Polling state — full-height waiting screen */}
        {phase === "polling" && (
          <div
            style={{
              height: 480,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "1.25rem",
              backgroundColor: "#0a0d12",
            }}
          >
            {/* Animated ring */}
            <div style={{ position: "relative", width: 52, height: 52 }}>
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  border: "2px solid #06b6d410",
                  borderTop: "2px solid #06b6d4",
                  borderRadius: "50%",
                  animation: "spin 1s linear infinite",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  inset: 8,
                  border: "2px solid #f59e0b10",
                  borderTop: "2px solid #f59e0b",
                  borderRadius: "50%",
                  animation: "spin 1.6s linear infinite reverse",
                }}
              />
            </div>

            <div style={{ textAlign: "center" }}>
              <div
                style={{
                  fontSize: "0.72rem",
                  fontWeight: 600,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  color: "#06b6d4",
                  marginBottom: "0.4rem",
                }}
              >
                Hex is recomputing your dashboard
              </div>
              <div
                style={{
                  fontSize: "0.65rem",
                  color: "#444",
                  letterSpacing: "0.06em",
                }}
              >
                {statusMsg}
                {elapsed && (
                  <span style={{ color: "#333", marginLeft: "0.5rem" }}>
                    · {elapsed} elapsed
                  </span>
                )}
              </div>
            </div>

            {/* Progress dots */}
            <div style={{ display: "flex", gap: "0.4rem" }}>
              {[0, 1, 2, 3].map((i) => (
                <div
                  key={i}
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: "50%",
                    backgroundColor: "#06b6d4",
                    animation: `bounceDot 1.4s ease-in-out ${i * 0.18}s infinite`,
                  }}
                />
              ))}
            </div>

            <a
              href={fallbackRunUrl ?? HEX_APP_URL}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                marginTop: "0.5rem",
                padding: "0.35rem 1rem",
                backgroundColor: "#06b6d410",
                border: "1px solid #06b6d425",
                borderRadius: "5px",
                color: "#06b6d480",
                fontSize: "0.62rem",
                letterSpacing: "0.05em",
                textDecoration: "none",
              }}
            >
              Open last version while waiting ↗
            </a>
          </div>
        )}

        {/* iframe — shown when ready or error (both load a URL) */}
        {(phase === "ready" || phase === "error" || phase === "idle") && (
          <div style={{ position: "relative", width: "100%", height: 620 }}>
            {/* Loading overlay — shown until iframe fires onLoad */}
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
                  {phase === "ready"
                    ? "Loading updated dashboard…"
                    : "Loading Hex dashboard…"}
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

            {/* XFO-blocked overlay — shown when iframe loaded */}
            {iframeVisible && (
              <div
                id="hex-xfo-hint"
                style={{
                  position: "absolute",
                  bottom: "1rem",
                  right: "1rem",
                  zIndex: 10,
                }}
              >
                <a
                  href={liveRunUrl ?? fallbackRunUrl ?? HEX_APP_URL}
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
        )}

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
        @keyframes hexPulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.3; }
        }
        @keyframes bounceDot {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.3; }
          40%            { transform: translateY(-6px); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
