"use client";

import StalkerWeb from "./StalkerWeb";

interface HexInfo {
  runId?: string;
  runUrl?: string;
  runStatusUrl?: string;
  projectId?: string;
  error?: string;
}

interface VisualizationWrapperProps {
  web: {
    nodes: any[];
    edges: any[];
  };
  hex?: HexInfo | null;
}

export default function VisualizationWrapper({ web, hex }: VisualizationWrapperProps) {
  return (
    <div>
      {/* Local force graph */}
      <StalkerWeb nodes={web.nodes} edges={web.edges} />

      {/* Hex embed */}
      {hex && !hex.error && hex.runUrl && (
        <div style={{ marginBottom: "1.5rem" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "0.6rem 1rem",
              backgroundColor: "#0a0a0a",
              border: "1px solid #1a1a1a",
              borderRadius: "10px 10px 0 0",
              borderBottom: "none",
            }}
          >
            <span
              style={{
                color: "#555",
                fontSize: "0.7rem",
                fontWeight: 600,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
              }}
            >
              Hex Analytics Dashboard
            </span>
            <a
              href={hex.runUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "#06b6d4", fontSize: "0.65rem", textDecoration: "none", letterSpacing: "0.05em" }}
            >
              Open in Hex ↗
            </a>
          </div>
          <iframe
            src={hex.runUrl}
            style={{
              width: "100%",
              height: 520,
              border: "1px solid #1a1a1a",
              borderTop: "none",
              borderRadius: "0 0 10px 10px",
              backgroundColor: "#0d0d0d",
            }}
            allow="clipboard-write"
            sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
          />
        </div>
      )}

      {/* Hex error */}
      {hex?.error && (
        <div
          style={{
            padding: "0.6rem 1rem",
            backgroundColor: "#0d0d0d",
            border: "1px solid #1a1a1a",
            borderRadius: "8px",
            marginBottom: "1.5rem",
          }}
        >
          <span style={{ color: "#555", fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase" }}>
            Hex Analytics
          </span>
          <span style={{ color: "#666", fontSize: "0.7rem", marginLeft: "0.75rem" }}>
            {hex.error}
          </span>
        </div>
      )}
    </div>
  );
}
