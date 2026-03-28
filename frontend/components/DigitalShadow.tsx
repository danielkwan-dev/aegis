"use client";

import { motion } from "framer-motion";

interface DigitalShadowProps {
  breachProbability: number;
  knownAnchors: number;
  routineConfidence: number;
}

function getBarColor(value: number): string {
  if (value <= 25) return "#16a34a";
  if (value <= 50) return "#ca8a04";
  if (value <= 75) return "#d97706";
  return "#dc2626";
}

function StatRing({
  value,
  label,
  suffix,
  color,
  delay,
}: {
  value: number;
  label: string;
  suffix: string;
  color: string;
  delay: number;
}) {
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const fill = (Math.min(value, 100) / 100) * circumference;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "0.5rem",
        flex: 1,
      }}
    >
      <svg width="90" height="90" viewBox="0 0 90 90">
        {/* Track */}
        <circle
          cx="45"
          cy="45"
          r={radius}
          fill="none"
          stroke="#141618"
          strokeWidth="5"
        />
        {/* Fill */}
        <motion.circle
          cx="45"
          cy="45"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - fill }}
          transition={{ duration: 1.2, delay: delay + 0.2, ease: "easeOut" }}
          transform="rotate(-90 45 45)"
          style={{ filter: `drop-shadow(0 0 4px ${color}55)` }}
        />
        {/* Value */}
        <text
          x="45"
          y="43"
          textAnchor="middle"
          fill={color}
          fontSize="18"
          fontWeight="700"
          fontFamily="inherit"
        >
          {Math.round(value)}
        </text>
        <text
          x="45"
          y="56"
          textAnchor="middle"
          fill="#444"
          fontSize="8"
          fontFamily="inherit"
        >
          {suffix}
        </text>
      </svg>
      <span
        style={{
          fontSize: "0.6rem",
          fontWeight: 600,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "#555",
          textAlign: "center",
        }}
      >
        {label}
      </span>
    </motion.div>
  );
}

export default function DigitalShadow({
  breachProbability,
  knownAnchors,
  routineConfidence,
}: DigitalShadowProps) {
  const anonymityScore = Math.max(0, 100 - breachProbability);
  const anonymityColor = getBarColor(100 - anonymityScore);
  const anchorsDisplay = Math.min(knownAnchors * 20, 100); // scale for visual
  const routineColor = routineConfidence > 70 ? "#dc2626" : routineConfidence > 40 ? "#d97706" : "#16a34a";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      style={{
        padding: "1.25rem 1.5rem",
        backgroundColor: "#0d1117",
        border: "1px solid #1a1a1a",
        borderRadius: "10px",
        marginBottom: "1.5rem",
      }}
    >
      <div
        style={{
          fontSize: "0.6rem",
          fontWeight: 600,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: "#06b6d4",
          marginBottom: "1.25rem",
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
        }}
      >
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            backgroundColor: "#06b6d4",
            display: "inline-block",
            boxShadow: "0 0 6px rgba(6,182,212,0.5)",
          }}
        />
        DIGITAL SHADOW
      </div>

      <div style={{ display: "flex", justifyContent: "space-around" }}>
        <StatRing
          value={anonymityScore}
          label="Anonymity Score"
          suffix={anonymityScore <= 25 ? "EXPOSED" : anonymityScore <= 50 ? "AT RISK" : "HIDDEN"}
          color={anonymityColor}
          delay={0}
        />
        <StatRing
          value={anchorsDisplay}
          label="Known Anchors"
          suffix={`${knownAnchors} LOCATIONS`}
          color="#06b6d4"
          delay={0.15}
        />
        <StatRing
          value={routineConfidence}
          label="Routine Confidence"
          suffix={routineConfidence > 70 ? "PREDICTABLE" : routineConfidence > 40 ? "PARTIAL" : "OBSCURED"}
          color={routineColor}
          delay={0.3}
        />
      </div>
    </motion.div>
  );
}
