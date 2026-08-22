import { ShieldQuestion } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border p-12 text-center">
      <ShieldQuestion className="h-8 w-8 text-muted-foreground" />
      <div>
        <p className="font-medium">No analysis yet</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Ingest a few baseline posts on the left, then draft a post below and analyze it to see what it reveals.
        </p>
      </div>
    </div>
  );
}
