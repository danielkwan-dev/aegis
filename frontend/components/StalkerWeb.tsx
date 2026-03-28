"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";

// Dynamically import to avoid SSR issues with canvas
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
  text_preview?: string;
  description?: string;
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

export default function StalkerWeb({ nodes, edges }: StalkerWebProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 680, height: 450 });

  useEffect(() => {
    if (!containerRef.current) return;
    const { clientWidth } = containerRef.current;
    if (clientWidth > 0) {
      setDimensions({ width: clientWidth, height: 450 });
    }
  }, []);

  // Build graph data in the shape react-force-graph expects
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
    // History nodes: muted gray unless high similarity
    if (node.similarity && node.similarity >= 0.2) {
      return node.color || "#888";
    }
    return "#444";
  }, []);

  const nodeSize = useCallback((node: any) => {
    // Use weight field for sizing if available (0-1 scale)
    const w = node.weight ?? 0;
    if (node.type === "post") return 14;
    if (node.type === "metadata") return 6 + w * 14; // landmarks scale big
    if (node.type === "extraction") return 6 + w * 10;
    // History nodes scale by similarity or weight
    const sim = node.similarity ?? w;
    return 4 + sim * 18;
  }, []);

  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const size = nodeSize(node);
    const color = nodeColor(node);
    const x = node.x ?? 0;
    const y = node.y ?? 0;

    const riskLevel = typeof node.risk_level === "number" ? node.risk_level : 0;

    // Glow for center node
    if (node.type === "post") {
      ctx.beginPath();
      ctx.arc(x, y, size + 4, 0, 2 * Math.PI);
      ctx.fillStyle = "rgba(255, 34, 34, 0.15)";
      ctx.fill();
    }
    // Glow for high-risk landmarks
    if (riskLevel >= 0.8 && node.type === "metadata") {
      ctx.beginPath();
      ctx.arc(x, y, size + 5, 0, 2 * Math.PI);
      ctx.fillStyle = `rgba(244, 63, 94, ${riskLevel * 0.15})`;
      ctx.fill();
    }

    // Main circle
    ctx.beginPath();
    ctx.arc(x, y, size, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    // Border
    ctx.strokeStyle = node.type === "post" ? "#ff6666" : "rgba(255,255,255,0.1)";
    ctx.lineWidth = node.type === "post" ? 2 : 0.5;
    ctx.stroke();

    // Label
    const label = node.label || node.id;
    const fontSize = Math.max(10 / globalScale, 2.5);
    ctx.font = `${fontSize}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillStyle = node.type === "post" ? "#ff8888" : "#777";
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
      // OCR + Text = thick glowing cyan line
      ctx.strokeStyle = `rgba(6, 182, 212, ${Math.max(weight * 0.8, 0.4)})`;
      ctx.lineWidth = Math.max(weight * 5, 2.5);
      ctx.shadowColor = "rgba(6, 182, 212, 0.6)";
      ctx.shadowBlur = 8;
    } else if (link.edgeType === "leaks") {
      ctx.strokeStyle = `rgba(244, 63, 94, ${Math.max(weight * 0.6, 0.15)})`;
      ctx.lineWidth = Math.max(weight * 3, 0.5);
      ctx.shadowColor = "transparent";
      ctx.shadowBlur = 0;
    } else if (link.edgeType === "confirms") {
      ctx.strokeStyle = `rgba(244, 63, 94, ${Math.max(weight * 0.5, 0.2)})`;
      ctx.lineWidth = Math.max(weight * 3.5, 0.8);
      ctx.shadowColor = "transparent";
      ctx.shadowBlur = 0;
    } else {
      ctx.strokeStyle = `rgba(255, 255, 255, ${Math.max(weight * 0.5, 0.05)})`;
      ctx.lineWidth = Math.max(weight * 2.5, 0.3);
      ctx.shadowColor = "transparent";
      ctx.shadowBlur = 0;
    }
    ctx.stroke();
    // Reset shadow
    ctx.shadowColor = "transparent";
    ctx.shadowBlur = 0;
  }, []);

  if (nodes.length === 0) return null;

  return (
    <div
      ref={containerRef}
      style={{
        backgroundColor: "#0d0d0d",
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
          borderBottom: "1px solid #1a1a1a",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ color: "#666", fontSize: "0.8rem", fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" }}>
          Stalker&apos;s Web
        </span>
        <span style={{ color: "#444", fontSize: "0.7rem" }}>
          {nodes.length} nodes &middot; {edges.length} connections
        </span>
      </div>

      {/* Force graph */}
      <ForceGraph2D
        graphData={graphData}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor="#0d0d0d"
        nodeCanvasObject={paintNode}
        linkCanvasObject={paintLink}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          const size = nodeSize(node);
          ctx.beginPath();
          ctx.arc(node.x ?? 0, node.y ?? 0, size + 4, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        cooldownTicks={80}
        d3AlphaDecay={0.03}
        d3VelocityDecay={0.3}
        enableZoomInteraction={true}
        enablePanInteraction={true}
      />

      {/* Legend */}
      <div
        style={{
          padding: "0.5rem 1rem",
          borderTop: "1px solid #1a1a1a",
          display: "flex",
          gap: "1rem",
          flexWrap: "wrap",
        }}
      >
        {[
          { color: "#ff2222", label: "Your Post" },
          { color: "#06b6d4", label: "OCR Text" },
          { color: "#f43f5e", label: "EXIF Leak" },
          { color: "#444", label: "History" },
        ].map((item) => (
          <div key={item.label} style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: item.color }} />
            <span style={{ color: "#555", fontSize: "0.7rem" }}>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
