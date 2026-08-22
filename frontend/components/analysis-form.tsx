"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useAnalyze } from "@/lib/hooks/use-analyze";
import type { AnalyzeThreatResult } from "@/lib/api-types";

export function AnalysisForm({
  onResult,
}: {
  onResult: (result: AnalyzeThreatResult) => void;
}) {
  const [text, setText] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const mutation = useAnalyze();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const formData = new FormData();
    formData.set("text", text);
    if (image) formData.set("image", image);
    mutation.mutate(formData, { onSuccess: (result) => onResult(result) });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Analyze a draft post
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <Textarea
            placeholder="Draft the post you're thinking about publishing…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={3}
          />
          <label className="text-sm text-muted-foreground">
            Optional image
            <input
              type="file"
              accept="image/*"
              aria-label="analysis image"
              onChange={(e) => setImage(e.target.files?.[0] ?? null)}
              className="mt-1 block text-sm"
            />
          </label>
          <Button type="submit" disabled={mutation.isPending || !text.trim()}>
            {mutation.isPending ? "Analyzing…" : "Analyze"}
          </Button>
          {mutation.isError && (
            <p className="text-sm text-destructive">{(mutation.error as Error).message}</p>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
