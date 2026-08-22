import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { VulnerabilityFinding } from "@/lib/api-types";

const SEVERITY_ORDER: VulnerabilityFinding["severity"][] = ["critical", "high", "medium", "low"];

const SEVERITY_LABEL: Record<VulnerabilityFinding["severity"], string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

const SEVERITY_BADGE_CLASS: Record<VulnerabilityFinding["severity"], string> = {
  critical: "bg-severity-critical/15 text-severity-critical border-severity-critical/30",
  high: "bg-severity-high/15 text-severity-high border-severity-high/30",
  medium: "bg-severity-medium/15 text-severity-medium border-severity-medium/30",
  low: "bg-severity-low/15 text-severity-low border-severity-low/30",
};

export function groupBySeverity(
  findings: VulnerabilityFinding[],
): Record<VulnerabilityFinding["severity"], VulnerabilityFinding[]> {
  const groups: Record<VulnerabilityFinding["severity"], VulnerabilityFinding[]> = {
    critical: [],
    high: [],
    medium: [],
    low: [],
  };
  for (const finding of findings) {
    groups[finding.severity].push(finding);
  }
  return groups;
}

export function FindingsList({ findings }: { findings: VulnerabilityFinding[] }) {
  if (findings.length === 0) {
    return <p className="text-sm text-muted-foreground">No vulnerabilities detected in this draft.</p>;
  }

  const groups = groupBySeverity(findings);

  return (
    <div className="flex flex-col gap-4">
      {SEVERITY_ORDER.filter((sev) => groups[sev].length > 0).map((sev) => (
        <div key={sev}>
          <div className="mb-2 flex items-center gap-2">
            <Badge variant="outline" className={SEVERITY_BADGE_CLASS[sev]}>
              {SEVERITY_LABEL[sev]}
            </Badge>
            <span className="text-xs text-muted-foreground">{groups[sev].length} finding(s)</span>
          </div>
          <div className="flex flex-col gap-2">
            {groups[sev].map((finding, i) => (
              <Card key={`${sev}-${i}`}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">{finding.category}</CardTitle>
                </CardHeader>
                <CardContent className="pt-0 text-sm text-muted-foreground">
                  {finding.finding}
                  <span className="ml-2 text-xs">({finding.evidence_count} evidence)</span>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
