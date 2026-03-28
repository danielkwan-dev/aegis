"use client";

import StalkerWeb from "./StalkerWeb";

interface VisualizationWrapperProps {
  web: {
    nodes: any[];
    edges: any[];
  };
}

export default function VisualizationWrapper({ web }: VisualizationWrapperProps) {
  return (
    <div>
      <StalkerWeb nodes={web.nodes} edges={web.edges} />
    </div>
  );
}
