"use client";

import StalkerWeb from "./StalkerWeb";

interface RiskReduction {
  action: string;
  detail: string;
  current_risk: number;
  reduced_risk: number;
  risk_drop: number;
  category: string;
}

interface VisualizationWrapperProps {
  web: {
    nodes: any[];
    edges: any[];
  };
  improvements?: RiskReduction[] | null;
}

const CATEGORY_CONFIG: Record<string, { color: string; symbol: string; label: string }> = {
  location: { color: "#f43f5e", symbol: "◈", label: "LOCATION" },
  temporal:  { color: "#f59e0b", symbol: "◷", label: "TEMPORAL" },
  activity:  { color: "#a855f7", symbol: "◉", label: "ACTIVITY" },
  all:       { color: "#06b6d4", symbol: "◆", label: "ALL FIXES" },
};

function HexTile({ imp }: { imp: RiskReduction }) {
  const cfg = CATEGORY_CONFIG[imp.category] ?? CATEGORY_CONFIG.location;

  return (
    <div style={{ filter: `drop-shadow(0 0 8px ${cfg.color}45)`, flexShrink: 0 }}>
      <div
        style={{
          width: 162,
          height: 142,
          clipPath: "polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%)",
          background: `linear-gradient(155deg, ${cfg.color}1e 0%, ${cfg.color}08 100%)`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "0.3rem",
          padding: "0 28px",
          textAlign: "center",
        }}
      >
        <span style={{ fontSize: "1rem", color: cfg.color }}>{cfg.symbol}</span>
        <div
          style={{
            fontSize: "0.55rem",
            fontWeight: 700,
            letterSpacing: "0.14em",
            color: cfg.color,
            textTransform: "uppercase",
          }}
        >
          {cfg.label}
        </div>
        <div style={{ fontSize: "0.68rem", color: "#b0b8c0", lineHeight: 1.3 }}>
          {imp.action.replace(/^Remove /, "").replace(/^Apply ALL$/, "all leaks")}
        </div>
        <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "#4ade80" }}>
          -{imp.risk_drop}%
        </div>
      </div>
    </div>
  );
}

export default function VisualizationWrapper({ web, improvements }: VisualizationWrapperProps) {
  const tiles = improvements?.filter((r) => r.category !== "all") ?? [];
  const applyAll = improvements?.find((r) => r.category === "all");

  return (
    <div>
      <StalkerWeb nodes={web.nodes} edges={web.edges} />

      {improvements && improvements.length > 0 && (
        <div style={{ marginBottom: "1.5rem" }}>
          {/* Section header */}
          <div
            style={{
              fontSize: "0.65rem",
              fontWeight: 600,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "#555",
              marginBottom: "1.25rem",
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
                backgroundColor: "#4ade80",
                display: "inline-block",
                boxShadow: "0 0 6px rgba(74,222,128,0.5)",
              }}
            />
            PRIVACY IMPROVEMENTS
          </div>

          {/* Hex tile grid */}
          {tiles.length > 0 && (
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                gap: "10px",
                flexWrap: "wrap",
                marginBottom: "1rem",
              }}
            >
              {tiles.map((imp, i) => (
                <HexTile key={i} imp={imp} />
              ))}
            </div>
          )}

          {/* Apply ALL card */}
          {applyAll && (
            <div
              style={{
                padding: "1rem 1.25rem",
                backgroundColor: "#06b6d40c",
                border: "1px solid #06b6d430",
                borderRadius: "8px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "0.65rem",
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: "0.6rem",
                      fontWeight: 700,
                      letterSpacing: "0.1em",
                      color: "#06b6d4",
                      marginBottom: "0.25rem",
                      textTransform: "uppercase",
                    }}
                  >
                    ◆ Apply All Fixes
                  </div>
                  <div style={{ fontSize: "0.74rem", color: "#666" }}>{applyAll.detail}</div>
                </div>
                <div style={{ textAlign: "right", flexShrink: 0, marginLeft: "1rem" }}>
                  <div style={{ fontSize: "0.65rem", color: "#555", marginBottom: "0.15rem" }}>
                    {applyAll.current_risk}%{" "}
                    <span style={{ color: "#333" }}>→</span>{" "}
                    <span style={{ color: "#4ade80", fontWeight: 700 }}>{applyAll.reduced_risk}%</span>
                  </div>
                  <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#4ade80" }}>
                    -{applyAll.risk_drop}%
                  </div>
                </div>
              </div>
              {/* Risk reduction bar */}
              <div
                style={{
                  width: "100%",
                  height: 3,
                  backgroundColor: "rgba(255,255,255,0.04)",
                  borderRadius: 2,
                }}
              >
                <div
                  style={{
                    width: `${applyAll.current_risk > 0
                      ? Math.min(((applyAll.current_risk - applyAll.reduced_risk) / applyAll.current_risk) * 100, 100)
                      : 0}%`,
                    height: "100%",
                    backgroundColor: "#4ade80",
                    borderRadius: 2,
                    transition: "width 0.8s ease",
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
