"use client";

import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GraphEdge, GraphNode } from "@/lib/api-types";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

export function toForceGraphData(nodes: GraphNode[], edges: GraphEdge[]) {
  return {
    nodes: nodes.map((n) => ({ id: n.id, label: n.label, color: n.color })),
    links: edges.map((e) => ({ source: e.source, target: e.target, label: e.label, value: e.weight })),
  };
}

export function EntityGraph({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  if (nodes.length === 0) {
    return null;
  }

  const data = toForceGraphData(nodes, edges);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Entity relationship graph
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[320px] w-full overflow-hidden rounded-md border border-border">
          <ForceGraph2D
            graphData={data}
            nodeLabel="label"
            nodeColor={(n: any) => n.color ?? "#888"}
            linkLabel="label"
            width={480}
            height={320}
            backgroundColor="transparent"
          />
        </div>
      </CardContent>
    </Card>
  );
}
