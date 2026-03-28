"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

interface WebNode {
  id: string;
  label: string;
  type: string;
  color: string;
  risk_level?: number | string;
  weight?: number;
  category?: string;
  similarity?: number;
  cluster_id?: number;
  cluster_name?: string;
  detail?: string;
}

interface WebEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
  category?: string;
  connection_strength?: string;
  label?: string;
}

interface StalkerWebProps {
  nodes: WebNode[];
  edges: WebEdge[];
}

// Cluster color palette
const CLUSTER_COLORS = ["#c084fc", "#06b6d4", "#f59e0b", "#4ade80", "#f43f5e"];

// Human-readable edge type descriptions
const EDGE_LABELS: Record<string, string> = {
  leaks: "leaks",
  confirms: "confirms",
  similarity: "matches",
  pattern: "same routine",
  corridor: "daily corridor",
  detected_in: "OCR detected",
  identity_link: "identity link",
  contains: "extracted from",
};

export default function StalkerWeb({ nodes, edges }: StalkerWebProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 680, height: 480 });
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [hoveredNode, setHoveredNode] = useState<any>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (!containerRef.current) return;
    const update = () => {
      const el = containerRef.current;
      if (!el) return;
      if (isFullscreen) {
        setDimensions({ width: window.innerWidth, height: window.innerHeight });
      } else {
        const { clientWidth } = el;
        if (clientWidth > 0) setDimensions({ width: clientWidth, height: 480 });
      }
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [isFullscreen]);

  // Re-center graph when toggling fullscreen
  useEffect(() => {
    if (graphRef.current) {
      setTimeout(() => graphRef.current?.zoomToFit(400, 60), 200);
    }
  }, [isFullscreen]);

  // Escape to exit fullscreen
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isFullscreen) setIsFullscreen(false);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isFullscreen]);

  const graphData = {
    nodes: nodes.map((n) => ({ ...n })),
    links: edges.map((e) => ({
      source: e.source,
      target: e.target,
      edgeType: e.type,
      weight: e.weight,
      category: e.category,
      connectionStrength: e.connection_strength,
      edgeLabel: e.label || EDGE_LABELS[e.type] || e.type,
    })),
  };

  const nodeColor = useCallback((node: any) => {
    if (node.type === "post") return "#ff2222";
    if (node.type === "extraction") return "#06b6d4";
    if (node.type === "metadata") return "#f43f5e";
    if (node.cluster_id !== undefined) {
      return CLUSTER_COLORS[node.cluster_id % CLUSTER_COLORS.length];
    }
    if (node.similarity && node.similarity >= 0.2) return node.color || "#888";
    return "#444";
  }, []);

  const nodeSize = useCallback((node: any) => {
    const w = node.weight ?? 0;
    if (node.type === "post") return 16;
    if (node.type === "metadata") return 7 + w * 13;
    if (node.type === "extraction") return 6 + w * 9;
    const sim = node.similarity ?? w;
    return 5 + sim * 16;
  }, []);

  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const size = nodeSize(node);
    const color = nodeColor(node);
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    const riskLevel = typeof node.risk_level === "number" ? node.risk_level : 0;
    const isHovered = hoveredNode?.id === node.id;

    // Hover highlight ring
    if (isHovered) {
      ctx.beginPath();
      ctx.arc(x, y, size + 8, 0, 2 * Math.PI);
      ctx.fillStyle = "rgba(255, 255, 255, 0.06)";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(x, y, size + 5, 0, 2 * Math.PI);
      ctx.strokeStyle = "rgba(255, 255, 255, 0.3)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Outer glow for center node
    if (node.type === "post") {
      ctx.beginPath();
      ctx.arc(x, y, size + 6, 0, 2 * Math.PI);
      ctx.fillStyle = "rgba(255, 34, 34, 0.12)";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(x, y, size + 3, 0, 2 * Math.PI);
      ctx.fillStyle = "rgba(255, 34, 34, 0.2)";
      ctx.fill();
    }

    // Glow for high-risk landmarks
    if (riskLevel >= 0.8 && node.type === "metadata") {
      ctx.beginPath();
      ctx.arc(x, y, size + 5, 0, 2 * Math.PI);
      ctx.fillStyle = `rgba(244, 63, 94, ${riskLevel * 0.12})`;
      ctx.fill();
    }

    // Main circle
    ctx.beginPath();
    ctx.arc(x, y, size, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    // Border
    if (node.type === "post") {
      ctx.strokeStyle = "#ff6666";
      ctx.lineWidth = 2;
    } else if (node.type === "metadata") {
      ctx.strokeStyle = "rgba(244,63,94,0.4)";
      ctx.lineWidth = 1.5;
    } else {
      ctx.strokeStyle = "rgba(255,255,255,0.08)";
      ctx.lineWidth = 0.5;
    }
    ctx.stroke();

    // Label -- truncate long labels
    let label = node.label || node.id;
    if (label.length > 32) label = label.slice(0, 30) + "...";

    const fontSize = Math.max(11 / globalScale, 3);
    ctx.font = `600 ${fontSize}px 'SF Mono', monospace`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";

    // Label background for readability
    if (globalScale > 0.5) {
      const metrics = ctx.measureText(label);
      const pad = 2 / globalScale;
      ctx.fillStyle = "rgba(8, 9, 10, 0.8)";
      ctx.fillRect(
        x - metrics.width / 2 - pad,
        y + size + 1,
        metrics.width + pad * 2,
        fontSize + pad,
      );
    }

    ctx.fillStyle = node.type === "post" ? "#ff8888"
      : node.type === "metadata" ? "#f4a0b0"
      : node.type === "extraction" ? "#7dd3e8"
      : "#aaa";
    ctx.fillText(label, x, y + size + 2);
  }, [nodeColor, nodeSize, hoveredNode]);

  const paintLink = useCallback((link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const sx = link.source?.x ?? 0;
    const sy = link.source?.y ?? 0;
    const tx = link.target?.x ?? 0;
    const ty = link.target?.y ?? 0;
    const weight = link.weight ?? 0.1;
    const isMultiSource = link.connectionStrength === "ocr+text";

    ctx.beginPath();
    ctx.moveTo(sx, sy);
    ctx.lineTo(tx, ty);

    if (isMultiSource) {
      ctx.strokeStyle = `rgba(6, 182, 212, ${Math.max(weight * 0.8, 0.4)})`;
      ctx.lineWidth = Math.max(weight * 5, 2.5);
      ctx.shadowColor = "rgba(6, 182, 212, 0.5)";
      ctx.shadowBlur = 6;
    } else if (link.edgeType === "leaks" || link.edgeType === "confirms") {
      ctx.strokeStyle = `rgba(244, 63, 94, ${Math.max(weight * 0.5, 0.15)})`;
      ctx.lineWidth = Math.max(weight * 3, 0.8);
      ctx.shadowColor = "transparent";
      ctx.shadowBlur = 0;
    } else if (link.edgeType === "pattern" || link.edgeType === "corridor") {
      ctx.strokeStyle = `rgba(192, 132, 252, ${Math.max(weight * 0.4, 0.1)})`;
      ctx.lineWidth = Math.max(weight * 2, 0.5);
      ctx.setLineDash([4, 3]);
      ctx.shadowColor = "transparent";
      ctx.shadowBlur = 0;
    } else {
      ctx.strokeStyle = `rgba(255, 255, 255, ${Math.max(weight * 0.35, 0.05)})`;
      ctx.lineWidth = Math.max(weight * 2, 0.3);
      ctx.shadowColor = "transparent";
      ctx.shadowBlur = 0;
    }
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.shadowColor = "transparent";
    ctx.shadowBlur = 0;

    // Edge label at midpoint
    if (link.edgeLabel && globalScale > 0.7) {
      const mx = (sx + tx) / 2;
      const my = (sy + ty) / 2;
      const labelFontSize = Math.max(9 / globalScale, 2.5);
      ctx.font = `500 ${labelFontSize}px 'SF Mono', monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      const metrics = ctx.measureText(link.edgeLabel);
      const pad = 2 / globalScale;
      ctx.fillStyle = "rgba(8, 9, 10, 0.85)";
      ctx.fillRect(
        mx - metrics.width / 2 - pad,
        my - labelFontSize / 2 - pad / 2,
        metrics.width + pad * 2,
        labelFontSize + pad,
      );

      ctx.fillStyle = isMultiSource ? "rgba(6, 182, 212, 0.7)"
        : link.edgeType === "leaks" || link.edgeType === "confirms" ? "rgba(244, 63, 94, 0.6)"
        : link.edgeType === "pattern" || link.edgeType === "corridor" ? "rgba(192, 132, 252, 0.6)"
        : "rgba(255, 255, 255, 0.35)";
      ctx.fillText(link.edgeLabel, mx, my);
    }
  }, []);

  const handleNodeHover = useCallback((node: any, prevNode: any) => {
    setHoveredNode(node || null);
  }, []);

  const handleBackgroundClick = useCallback(() => {
    setHoveredNode(null);
  }, []);

  if (nodes.length === 0) return null;

  // Collect unique cluster names for legend
  const clusterNames = new Map<number, string>();
  nodes.forEach((n) => {
    if (n.cluster_id !== undefined && n.cluster_name) {
      clusterNames.set(n.cluster_id, n.cluster_name);
    }
  });

  const containerStyle: React.CSSProperties = isFullscreen
    ? {
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        backgroundColor: "#050505",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
      }
    : {
        backgroundColor: "#0a0a0a",
        border: "1px solid #1a1a1a",
        borderRadius: "10px",
        overflow: "hidden",
        marginBottom: "1.5rem",
      };

  return (
    <div ref={containerRef} style={containerStyle}>
      {/* Graph header */}
      <div
        style={{
          padding: isFullscreen ? "1rem 1.5rem" : "0.75rem 1rem",
          borderBottom: "1px solid #141618",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexShrink: 0,
        }}
      >
        <span style={{ color: "#555", fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase" }}>
          Stalker&apos;s Web — Identity Link Graph
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <span style={{ color: "#333", fontSize: "0.65rem" }}>
            {nodes.length} nodes · {edges.length} connections
          </span>
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            style={{
              padding: "0.3rem 0.7rem",
              backgroundColor: isFullscreen ? "#1a0a0a" : "#0a0a14",
              border: `1px solid ${isFullscreen ? "#dc262630" : "#1e2228"}`,
              borderRadius: "4px",
              color: isFullscreen ? "#dc2626" : "#555",
              fontSize: "0.65rem",
              fontWeight: 600,
              cursor: "pointer",
              fontFamily: "inherit",
              letterSpacing: "0.05em",
              textTransform: "uppercase",
            }}
          >
            {isFullscreen ? "✕ Close" : "⛶ Expand"}
          </button>
        </div>
      </div>

      {/* Force graph */}
      <div style={{ flex: isFullscreen ? 1 : undefined, position: "relative" }}>
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          width={dimensions.width}
          height={isFullscreen ? dimensions.height - 110 : dimensions.height}
          backgroundColor={isFullscreen ? "#050505" : "#0a0a0a"}
          nodeCanvasObject={paintNode}
          linkCanvasObject={paintLink}
          nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
            const size = nodeSize(node);
            ctx.beginPath();
            ctx.arc(node.x ?? 0, node.y ?? 0, size + 4, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }}
          onNodeHover={handleNodeHover}
          onBackgroundClick={handleBackgroundClick}
          cooldownTicks={120}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.25}
          enableZoomInteraction={true}
          enablePanInteraction={true}
          warmupTicks={30}
        />

        {/* Hover tooltip */}
        {hoveredNode && (
          <div
            style={{
              position: "absolute",
              bottom: 12,
              left: 12,
              maxWidth: isFullscreen ? 420 : 320,
              padding: "0.75rem 1rem",
              backgroundColor: "rgba(10, 10, 10, 0.95)",
              border: "1px solid #1e2228",
              borderRadius: "8px",
              pointerEvents: "none",
              zIndex: 10,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
              <div style={{
                width: 8, height: 8, borderRadius: "50%",
                backgroundColor: nodeColor(hoveredNode),
              }} />
              <span style={{ color: "#c8ccd0", fontSize: "0.78rem", fontWeight: 700 }}>
                {hoveredNode.label || hoveredNode.id}
              </span>
            </div>

            {hoveredNode.detail && (
              <p style={{ color: "#888", fontSize: "0.72rem", margin: "0 0 0.3rem", lineHeight: 1.5 }}>
                {hoveredNode.detail}
              </p>
            )}

            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.25rem" }}>
              {hoveredNode.type && (
                <span style={{ color: "#555", fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  {hoveredNode.type}
                </span>
              )}
              {hoveredNode.cluster_name && (
                <span style={{
                  fontSize: "0.6rem",
                  color: CLUSTER_COLORS[(hoveredNode.cluster_id ?? 0) % CLUSTER_COLORS.length],
                  letterSpacing: "0.05em",
                }}>
                  ● {hoveredNode.cluster_name}
                </span>
              )}
              {hoveredNode.similarity !== undefined && (
                <span style={{ color: "#555", fontSize: "0.6rem" }}>
                  similarity: {(hoveredNode.similarity * 100).toFixed(0)}%
                </span>
              )}
              {typeof hoveredNode.risk_level === "number" && hoveredNode.risk_level > 0 && (
                <span style={{ color: hoveredNode.risk_level >= 0.7 ? "#f43f5e" : "#555", fontSize: "0.6rem" }}>
                  risk: {(hoveredNode.risk_level * 100).toFixed(0)}%
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Legend + fullscreen hint */}
      <div
        style={{
          padding: isFullscreen ? "0.75rem 1.5rem" : "0.6rem 1rem",
          borderTop: "1px solid #141618",
          display: "flex",
          gap: "1rem",
          flexWrap: "wrap",
          alignItems: "center",
          flexShrink: 0,
        }}
      >
        {[
          { color: "#ff2222", label: "Draft Post" },
          { color: "#06b6d4", label: "Extracted Entity" },
          { color: "#f43f5e", label: "Landmark / OCR" },
        ].map((item) => (
          <div key={item.label} style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: item.color }} />
            <span style={{ color: "#444", fontSize: "0.65rem" }}>{item.label}</span>
          </div>
        ))}
        {/* Cluster legend */}
        {clusterNames.size > 0 && (
          <>
            <div style={{ width: 1, height: 12, backgroundColor: "#1a1a1a", margin: "0 0.25rem" }} />
            {Array.from(clusterNames.entries()).map(([cid, name]) => (
              <div key={cid} style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: CLUSTER_COLORS[cid % CLUSTER_COLORS.length] }} />
                <span style={{ color: "#444", fontSize: "0.65rem" }}>{name}</span>
              </div>
            ))}
          </>
        )}
        {isFullscreen && (
          <>
            <div style={{ flex: 1 }} />
            <span style={{ color: "#333", fontSize: "0.6rem" }}>
              Scroll to zoom · Drag to pan · Hover for details · ESC to close
            </span>
          </>
        )}
      </div>
    </div>
  );
}
