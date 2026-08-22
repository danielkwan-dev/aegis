import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EntityGraph, toForceGraphData } from "./entity-graph";
import type { GraphEdge, GraphNode } from "@/lib/api-types";

vi.mock("react-force-graph-2d", () => ({
  default: () => <div data-testid="force-graph-stub" />,
}));

const NODES: GraphNode[] = [
  { id: "new_post", label: "Your Draft Post", type: "post", color: "#f59e0b" },
  { id: "fp_1", label: "Coffee, Market Street", type: "footprint", color: "#ef4444" },
];
const EDGES: GraphEdge[] = [
  { source: "new_post", target: "fp_1", type: "identity_link", weight: 0.4, label: "both mention Market Street" },
];

describe("toForceGraphData", () => {
  it("maps nodes/edges into the react-force-graph-2d graphData shape", () => {
    const data = toForceGraphData(NODES, EDGES);
    expect(data.nodes).toEqual([
      { id: "new_post", label: "Your Draft Post", color: "#f59e0b" },
      { id: "fp_1", label: "Coffee, Market Street", color: "#ef4444" },
    ]);
    expect(data.links).toEqual([
      { source: "new_post", target: "fp_1", label: "both mention Market Street", value: 0.4 },
    ]);
  });
});

describe("EntityGraph", () => {
  it("renders the graph card when there are nodes", () => {
    render(<EntityGraph nodes={NODES} edges={EDGES} />);
    expect(screen.getByText(/entity relationship graph/i)).toBeInTheDocument();
  });

  it("renders nothing when there are no nodes", () => {
    const { container } = render(<EntityGraph nodes={[]} edges={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
