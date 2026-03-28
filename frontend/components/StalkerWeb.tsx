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
}

interface WebEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
  category?: string;
  connection_strength?: string;
}

interface StalkerWebProps {
  nodes: WebNode[];
  edges: WebEdge[];
}

// Cluster color palette
const CLUSTER_COLORS = ["#c084fc", "#06b6d4", "#f59e0b", "#4ade80", "#f43f5e"];

export default function StalkerWeb({ nodes, edges }: StalkerWebProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 680, height: 480 });

  useEffect(() => {
    if (!containerRef.current) return;
    const { clientWidth } = containerRef.current;
    if (clientWidth > 0) {
      setDimensions({ width: clientWidth, height: 480 });
    }
  }, []);

  const graphData = {
    nodes: nodes.map((n) => ({ ...n })),
    links: edges.map((e) => ({
      source: e.source,
      target: e.target,
      edgeType: e.type,
      weight: e.weight,
      category: e.category,
      connectionStrength: e.connection_strength,
    })),
  };

  const nodeColor = useCallback((node: any) => {
    if (node.type === "post") return "#ff2222";
    if (node.type === "extraction") return "#06b6d4";
    if (node.type === "metadata") return "#f43f5e";
    // Color history nodes by cluster if available
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
    if (label.length > 28) label = label.slice(0, 26) + "...";

    const fontSize = Math.max(11 / globalScale, 3);
    ctx.font = `600 ${fontSize}px 'SF Mono', monospace`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";

    // Label background for readability
    if (globalScale > 0.6) {
      const metrics = ctx.measureText(label);
      const pad = 2 / globalScale;
      ctx.fillStyle = "rgba(8, 9, 10, 0.75)";
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
      : "#888";
    ctx.fillText(label, x, y + size + 2);
  }, [nodeColor, nodeSize]);

  const paintLink = useCallback((link: any, ctx: CanvasRenderingContext2D) => {
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
  }, []);

  if (nodes.length === 0) return null;

  // Collect unique cluster names for legend
  const clusterNames = new Map<number, string>();
  nodes.forEach((n) => {
    if (n.cluster_id !== undefined && n.cluster_name) {
      clusterNames.set(n.cluster_id, n.cluster_name);
    }
  });

  return (
    <div
      ref={containerRef}
      style={{
        backgroundColor: "#0a0a0a",
        border: "1px solid #1a1a1a",
        borderRadius: "10px",
        overflow: "hidden",
        marginBottom: "1.5rem",
      }}
    >
      {/* Graph header */}
      <div
        style={{
          padding: "0.75rem 1rem",
          borderBottom: "1px solid #141618",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ color: "#555", fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase" }}>
          Stalker&apos;s Web — Identity Link Graph
        </span>
        <span style={{ color: "#333", fontSize: "0.65rem" }}>
          {nodes.length} nodes · {edges.length} connections
        </span>
      </div>

      {/* Force graph */}
      <ForceGraph2D
        graphData={graphData}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor="#0a0a0a"
        nodeCanvasObject={paintNode}
        linkCanvasObject={paintLink}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          const size = nodeSize(node);
          ctx.beginPath();
          ctx.arc(node.x ?? 0, node.y ?? 0, size + 4, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        cooldownTicks={120}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.25}
        enableZoomInteraction={true}
        enablePanInteraction={true}
        warmupTicks={30}
      />

      {/* Legend */}
      <div
        style={{
          padding: "0.6rem 1rem",
          borderTop: "1px solid #141618",
          display: "flex",
          gap: "1rem",
          flexWrap: "wrap",
          alignItems: "center",
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
      </div>
    </div>
  );
}
