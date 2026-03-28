"use client";

import StalkerWeb from "./StalkerWeb";

/**
 * VisualizationWrapper — swap layer for the graph visualization.
 *
 * Currently renders the local StalkerWeb (react-force-graph-2d).
 * To migrate to Hex for the sponsor prize track, replace the body
 * of this component with a Hex iframe embed:
 *
 *   <iframe
 *     src={`https://app.hex.tech/embed/YOUR_HEX_PROJECT_ID?threat_data=${encodeURIComponent(JSON.stringify(data))}`}
 *     style={{ width: "100%", height: 500, border: "none", borderRadius: 10 }}
 *   />
 *
 * The props interface stays the same — the parent never needs to change.
 */

interface VisualizationWrapperProps {
  web: {
    nodes: any[];
    edges: any[];
  };
}

export default function VisualizationWrapper({ web }: VisualizationWrapperProps) {
  return <StalkerWeb nodes={web.nodes} edges={web.edges} />;
}
