import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BreachGauge, bandFor } from "./breach-gauge";

describe("bandFor", () => {
  it("labels 70+ as Critical", () => {
    expect(bandFor(85).label).toBe("Critical");
  });
  it("labels 40-69 as Moderate", () => {
    expect(bandFor(50).label).toBe("Moderate");
  });
  it("labels 15-39 as Low", () => {
    expect(bandFor(20).label).toBe("Low");
  });
  it("labels under 15 as Minimal", () => {
    expect(bandFor(5).label).toBe("Minimal");
  });
});

describe("BreachGauge", () => {
  it("renders the rounded score and band label", () => {
    render(<BreachGauge score={72.6} />);

    expect(screen.getByText("73%")).toBeInTheDocument();
    expect(screen.getByText("Critical")).toBeInTheDocument();
  });

  it("clamps out-of-range scores into 0-100", () => {
    render(<BreachGauge score={150} />);

    expect(screen.getByText("100%")).toBeInTheDocument();
  });
});
