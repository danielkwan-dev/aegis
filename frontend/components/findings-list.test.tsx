import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FindingsList, groupBySeverity } from "./findings-list";
import type { VulnerabilityFinding } from "@/lib/api-types";

const FINDINGS: VulnerabilityFinding[] = [
  { category: "Routine Leak", severity: "high", finding: "You post from home every morning", evidence_count: 3 },
  { category: "Identity Leak", severity: "critical", finding: "Street matches your home cluster", evidence_count: 1 },
  { category: "Metadata Leak", severity: "medium", finding: "Image has GPS coordinates", evidence_count: 1 },
];

describe("groupBySeverity", () => {
  it("buckets findings by severity", () => {
    const groups = groupBySeverity(FINDINGS);
    expect(groups.critical).toHaveLength(1);
    expect(groups.high).toHaveLength(1);
    expect(groups.medium).toHaveLength(1);
    expect(groups.low).toHaveLength(0);
  });
});

describe("FindingsList", () => {
  it("renders each finding grouped under its severity badge", () => {
    render(<FindingsList findings={FINDINGS} />);

    expect(screen.getByText("Critical")).toBeInTheDocument();
    expect(screen.getByText("Street matches your home cluster")).toBeInTheDocument();
    expect(screen.getByText("You post from home every morning")).toBeInTheDocument();
  });

  it("shows a no-vulnerabilities message when the list is empty", () => {
    render(<FindingsList findings={[]} />);

    expect(screen.getByText(/no vulnerabilities detected/i)).toBeInTheDocument();
  });
});
