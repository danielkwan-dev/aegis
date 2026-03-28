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

      {/* Hex: geographic threat map link */}
      {hex && !hex.error && hex.runUrl && (
        <a
          href={hex.runUrl}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "0.6rem",
            padding: "0.75rem 1.25rem",
            backgroundColor: "#0a0a0a",
            border: "1px solid #1a1a1a",
            borderRadius: "8px",
            marginBottom: "1.5rem",
            textDecoration: "none",
            cursor: "pointer",
            transition: "border-color 0.2s ease",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#dc262650")}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#1a1a1a")}
        >
          <span style={{ fontSize: "1rem" }}>🗺</span>
          <span style={{ color: "#c8ccd0", fontSize: "0.78rem", fontWeight: 600, letterSpacing: "0.03em" }}>
            Open Geographic Threat Map
          </span>
          <span style={{ color: "#555", fontSize: "0.65rem", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Powered by Hex
          </span>
          <span style={{ color: "#dc2626", fontSize: "0.75rem", marginLeft: "auto" }}>↗</span>
        </a>
      )}
    </div>
  );
}
