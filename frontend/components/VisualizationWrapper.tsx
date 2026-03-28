"use client";

import StalkerWeb from "./StalkerWeb";

interface HexInfo {
  runId?: string;
  runUrl?: string;
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

const HEX_PROJECT_ID = "Aegis-032pYjM1wOXFrsi6nXOwag";

export default function VisualizationWrapper({ web, hex }: VisualizationWrapperProps) {
  // Build the Hex embed URL with graph data passed as input param
  const hexEmbedUrl = `https://app.hex.tech/app/${HEX_PROJECT_ID}/latest?embeddable=true&input_data=${encodeURIComponent(JSON.stringify(web))}`;

  return (
    <div>
      {/* Local force graph — always rendered as fast fallback */}
      <StalkerWeb nodes={web.nodes} edges={web.edges} />

      {/* Hex embed */}
      {hex && !hex.error && (
        <div style={{ marginBottom: "1.5rem" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "0.5rem",
            }}
          >
            <span
              style={{
                color: "#666",
                fontSize: "0.8rem",
                fontWeight: 600,
                letterSpacing: "0.05em",
                textTransform: "uppercase",
              }}
            >
              Hex Analytics View
            </span>
            {hex.runUrl && (
              <a
                href={hex.runUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "#888", fontSize: "0.7rem", textDecoration: "underline" }}
              >
                Open in Hex ↗
              </a>
            )}
          </div>
          <iframe
            src={hexEmbedUrl}
            style={{
              width: "100%",
              height: 500,
              border: "1px solid #1a1a1a",
              borderRadius: "10px",
              backgroundColor: "#0d0d0d",
            }}
            allow="clipboard-write"
            sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
          />
        </div>
      )}

      {/* Hex error fallback */}
      {hex?.error && (
        <div
          style={{
            padding: "0.5rem 1rem",
            backgroundColor: "#1a1a0a",
            border: "1px solid #333",
            borderRadius: "8px",
            marginBottom: "1.5rem",
          }}
        >
          <span style={{ color: "#888", fontSize: "0.75rem" }}>
            Hex sync: {hex.error}
          </span>
        </div>
      )}
    </div>
  );
}
