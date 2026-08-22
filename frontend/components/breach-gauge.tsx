import { cn } from "@/lib/utils";

const RADIUS = 54;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function bandFor(score: number): { label: string; className: string } {
  if (score >= 70) return { label: "Critical", className: "text-severity-critical stroke-severity-critical" };
  if (score >= 40) return { label: "Moderate", className: "text-severity-high stroke-severity-high" };
  if (score >= 15) return { label: "Low", className: "text-severity-medium stroke-severity-medium" };
  return { label: "Minimal", className: "text-severity-low stroke-severity-low" };
}

export function BreachGauge({ score }: { score: number }) {
  const clamped = Math.max(0, Math.min(100, score));
  const offset = CIRCUMFERENCE - (clamped / 100) * CIRCUMFERENCE;
  const band = bandFor(clamped);

  return (
    <div
      className="relative flex h-[140px] w-[140px] items-center justify-center"
      role="img"
      aria-label={`Breach probability ${Math.round(clamped)}%, ${band.label}`}
    >
      <svg width={140} height={140} viewBox="0 0 140 140" className="-rotate-90">
        <circle cx={70} cy={70} r={RADIUS} strokeWidth={10} className="stroke-muted" fill="none" />
        <circle
          cx={70}
          cy={70}
          r={RADIUS}
          strokeWidth={10}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          className={cn("transition-[stroke-dashoffset] duration-500", band.className)}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-3xl font-bold">{Math.round(clamped)}%</span>
        <span className={cn("text-xs font-medium uppercase tracking-wide", band.className)}>
          {band.label}
        </span>
      </div>
    </div>
  );
}
