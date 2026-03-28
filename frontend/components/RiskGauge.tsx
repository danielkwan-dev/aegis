"use client";

import { useEffect, useState } from "react";

interface RiskGaugeProps {
  breachProbability: number;
}

function getRiskColor(prob: number): string {
  if (prob >= 70) return "#dc2626";
  if (prob >= 40) return "#d97706";
  if (prob >= 15) return "#ca8a04";
  return "#16a34a";
}

function getRiskLabel(prob: number): string {
  if (prob >= 70) return "CRITICAL";
  if (prob >= 40) return "HIGH";
  if (prob >= 15) return "MEDIUM";
  return "LOW";
}

export default function RiskGauge({ breachProbability }: RiskGaugeProps) {
  const [animatedValue, setAnimatedValue] = useState(0);

  useEffect(() => {
    let frame: number;
    const start = performance.now();
    const duration = 1200;
    const target = breachProbability;

    function animate(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedValue(eased * target);
      if (progress < 1) {
        frame = requestAnimationFrame(animate);
      }
    }

    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [breachProbability]);

  const color = getRiskColor(animatedValue);
  const label = getRiskLabel(breachProbability);

  // SVG semi-circle gauge
  const radius = 80;
  const circumference = Math.PI * radius; // half circle
  const fillLength = (animatedValue / 100) * circumference;
  const dashOffset = circumference - fillLength;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "1.5rem 0 0.5rem",
      }}
    >
      <svg width="200" height="115" viewBox="0 0 200 115">
        {/* Track */}
        <path
          d="M 15 100 A 80 80 0 0 1 185 100"
          fill="none"
          stroke="#1a1a1a"
          strokeWidth="12"
          strokeLinecap="round"
        />
        {/* Fill */}
        <path
          d="M 15 100 A 80 80 0 0 1 185 100"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={`${circumference}`}
          strokeDashoffset={dashOffset}
          style={{
            transition: "stroke 0.3s ease",
            filter: `drop-shadow(0 0 6px ${color}66)`,
          }}
        />
        {/* Center value */}
        <text
          x="100"
          y="80"
          textAnchor="middle"
          fill={color}
          fontSize="28"
          fontWeight="700"
          fontFamily="inherit"
        >
          {animatedValue.toFixed(1)}%
        </text>
        <text
          x="100"
          y="100"
          textAnchor="middle"
          fill="#555"
          fontSize="10"
          fontWeight="600"
          letterSpacing="0.1em"
          fontFamily="inherit"
        >
          BREACH PROBABILITY
        </text>
      </svg>

      <div
        style={{
          marginTop: "0.25rem",
          padding: "0.2rem 0.8rem",
          backgroundColor: `${color}15`,
          border: `1px solid ${color}40`,
          borderRadius: "4px",
          color: color,
          fontSize: "0.75rem",
          fontWeight: 700,
          letterSpacing: "0.1em",
        }}
      >
        {label}
      </div>
    </div>
  );
}
