"use client";

export interface ScoreEntry {
  timestamp: string;
  breach_probability: number;
  severity_counts: Record<string, number>;
  entity_counts: Record<string, number>;
}

interface ScoreTrackerProps {
  history: ScoreEntry[];
}

const GRADES = [
  { max: 10,  grade: "S", label: "GHOST",       color: "#06b6d4" },
  { max: 25,  grade: "A", label: "SHADOW",      color: "#4ade80" },
  { max: 45,  grade: "B", label: "OPERATIVE",   color: "#a3e635" },
  { max: 65,  grade: "C", label: "EXPOSED",     color: "#f59e0b" },
  { max: 80,  grade: "D", label: "COMPROMISED", color: "#f97316" },
  { max: 101, grade: "F", label: "BURNED",      color: "#dc2626" },
];

function getGrade(score: number) {
  return GRADES.find((g) => score <= g.max) ?? GRADES[GRADES.length - 1];
}

function Sparkline({ history }: { history: ScoreEntry[] }) {
  if (history.length < 2) return null;
  const recent = history.slice(-12);
  const scores = recent.map((r) => r.breach_probability);
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const range = max - min || 1;
  const W = 110, H = 28;
  const pts = scores
    .map((s, i) => {
      const x = (i / (scores.length - 1)) * W;
      const y = H - ((s - min) / range) * (H - 6) - 3;
      return `${x},${y}`;
    })
    .join(" ");

  const last = scores[scores.length - 1];
  const prev = scores[scores.length - 2];
  const color = last <= prev ? "#4ade80" : "#f43f5e";
  const lastX = W;
  const lastY = H - ((last - min) / range) * (H - 6) - 3;

  return (
    <svg width={W} height={H} style={{ overflow: "visible" }}>
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={0.75}
      />
      <circle cx={lastX} cy={lastY} r={2.5} fill={color} />
    </svg>
  );
}

function getAchievements(history: ScoreEntry[], current: number) {
  const all = history.map((h) => h.breach_probability);
  const best = Math.min(...all);
  const prev = history.length >= 2 ? history[history.length - 2].breach_probability : null;
  const badges: { icon: string; label: string; color: string }[] = [];

  if (history.length === 1)                         badges.push({ icon: "◎", label: "FIRST CONTACT",   color: "#06b6d4" });
  if (current === best && history.length > 1)       badges.push({ icon: "★", label: "PERSONAL BEST",   color: "#fbbf24" });
  if (prev !== null && current < prev)              badges.push({ icon: "▼", label: "IMPROVING",        color: "#4ade80" });
  if (prev !== null && current > prev)              badges.push({ icon: "▲", label: "SLIPPING",         color: "#f43f5e" });
  if (current <= 10)                                badges.push({ icon: "◉", label: "GHOST PROTOCOL",  color: "#06b6d4" });
  else if (current <= 25)                           badges.push({ icon: "◑", label: "IN THE SHADOWS",  color: "#4ade80" });
  if (history.length >= 5)                          badges.push({ icon: "◈", label: "VETERAN",          color: "#a855f7" });
  if (history.length >= 10)                         badges.push({ icon: "◆", label: "DEEP COVER",       color: "#f59e0b" });

  return badges;
}

export default function ScoreTracker({ history }: ScoreTrackerProps) {
  if (!history || history.length === 0) return null;

  const current = history[history.length - 1];
  const score = current.breach_probability;
  const grade = getGrade(score);
  const allScores = history.map((h) => h.breach_probability);
  const personalBest = Math.min(...allScores);
  const prev = history.length >= 2 ? history[history.length - 2].breach_probability : null;
  const delta = prev !== null ? score - prev : null;
  const badges = getAchievements(history, score);

  return (
    <div
      style={{
        padding: "1.25rem 1.5rem",
        backgroundColor: "#0d1117",
        border: `1px solid ${grade.color}30`,
        borderRadius: "10px",
        marginBottom: "1.5rem",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Background corner glow */}
      <div
        style={{
          position: "absolute",
          top: -20, right: -20,
          width: 140, height: 140,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${grade.color}0e 0%, transparent 70%)`,
          pointerEvents: "none",
        }}
      />

      {/* Top row: score + grade */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
        <div>
          <div
            style={{
              fontSize: "0.58rem",
              fontWeight: 600,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "#444",
              marginBottom: "0.3rem",
            }}
          >
            RISK SCORE — LOWER IS BETTER
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.7rem" }}>
            <span
              style={{
                fontSize: "2.8rem",
                fontWeight: 800,
                color: grade.color,
                lineHeight: 1,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {score.toFixed(1)}
            </span>
            {delta !== null && (
              <span
                style={{
                  fontSize: "0.85rem",
                  fontWeight: 700,
                  color: delta < 0 ? "#4ade80" : delta > 0 ? "#f43f5e" : "#555",
                }}
              >
                {delta < 0 ? "▼" : delta > 0 ? "▲" : "—"}
                {Math.abs(delta).toFixed(1)}
              </span>
            )}
          </div>
        </div>

        {/* Grade badge */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            padding: "0.5rem 0.9rem",
            backgroundColor: `${grade.color}12`,
            border: `1px solid ${grade.color}35`,
            borderRadius: "8px",
          }}
        >
          <span style={{ fontSize: "1.7rem", fontWeight: 900, color: grade.color, lineHeight: 1 }}>
            {grade.grade}
          </span>
          <span
            style={{
              fontSize: "0.48rem",
              fontWeight: 700,
              letterSpacing: "0.1em",
              color: grade.color,
              opacity: 0.85,
              marginTop: "0.15rem",
            }}
          >
            {grade.label}
          </span>
        </div>
      </div>

      {/* Stats row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "1.5rem",
          marginBottom: badges.length > 0 ? "0.85rem" : 0,
        }}
      >
        {history.length >= 2 && (
          <div>
            <div style={{ fontSize: "0.48rem", color: "#3a3a3a", letterSpacing: "0.1em", marginBottom: "0.25rem", textTransform: "uppercase" }}>
              Trend ({history.length} runs)
            </div>
            <Sparkline history={history} />
          </div>
        )}

        {history.length > 1 && (
          <div>
            <div style={{ fontSize: "0.48rem", color: "#3a3a3a", letterSpacing: "0.1em", marginBottom: "0.25rem", textTransform: "uppercase" }}>
              Personal Best
            </div>
            <div style={{ fontSize: "1rem", fontWeight: 700, color: "#fbbf24" }}>
              {personalBest.toFixed(1)}
            </div>
          </div>
        )}

        <div>
          <div style={{ fontSize: "0.48rem", color: "#3a3a3a", letterSpacing: "0.1em", marginBottom: "0.25rem", textTransform: "uppercase" }}>
            Total Runs
          </div>
          <div style={{ fontSize: "1rem", fontWeight: 700, color: "#444" }}>
            {history.length}
          </div>
        </div>
      </div>

      {/* Achievement badges */}
      {badges.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
          {badges.map((b, i) => (
            <span
              key={i}
              style={{
                padding: "0.15rem 0.5rem",
                backgroundColor: `${b.color}14`,
                border: `1px solid ${b.color}30`,
                borderRadius: "3px",
                fontSize: "0.55rem",
                fontWeight: 700,
                letterSpacing: "0.08em",
                color: b.color,
              }}
            >
              {b.icon} {b.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
