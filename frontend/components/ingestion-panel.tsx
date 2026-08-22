"use client";

import { useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useIngestExport, useIngestManual } from "@/lib/hooks/use-ingest";

export function IngestionPanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Build your baseline
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="manual">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="manual">Manual entry</TabsTrigger>
            <TabsTrigger value="export">Import export</TabsTrigger>
          </TabsList>
          <TabsContent value="manual">
            <ManualEntryForm />
          </TabsContent>
          <TabsContent value="export">
            <ExportImportForm />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

function ManualEntryForm() {
  const [text, setText] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const mutation = useIngestManual();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const formData = new FormData();
    formData.set("text", text);
    if (image) formData.set("image", image);
    mutation.mutate(formData, {
      onSuccess: () => {
        setText("");
        setImage(null);
      },
    });
  }

  return (
    <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
      <Textarea
        placeholder="Grabbing my usual morning coffee down on Market Street"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
      />
      <label className="text-sm text-muted-foreground">
        Optional image
        <input
          type="file"
          accept="image/*"
          aria-label="manual entry image"
          onChange={(e) => setImage(e.target.files?.[0] ?? null)}
          className="mt-1 block text-sm"
        />
      </label>
      <Button type="submit" disabled={mutation.isPending || !text.trim()}>
        {mutation.isPending ? "Securing…" : "Add to baseline"}
      </Button>
      {mutation.isSuccess && mutation.data.status === "secured" && (
        <Alert>
          <AlertDescription>{mutation.data.message}</AlertDescription>
        </Alert>
      )}
      {mutation.isError && (
        <Alert variant="destructive">
          <AlertDescription>{(mutation.error as Error).message}</AlertDescription>
        </Alert>
      )}
    </form>
  );
}

function ExportImportForm() {
  const [file, setFile] = useState<File | null>(null);
  const mutation = useIngestExport();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    const formData = new FormData();
    formData.set("file", file);
    mutation.mutate(formData, { onSuccess: () => setFile(null) });
  }

  return (
    <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
      <label className="text-sm text-muted-foreground">
        Instagram data export (.zip)
        <input
          type="file"
          accept=".zip"
          aria-label="export file"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="mt-1 block text-sm"
        />
      </label>
      <Button type="submit" disabled={mutation.isPending || !file}>
        {mutation.isPending ? "Importing…" : "Import export"}
      </Button>
      {mutation.isSuccess && mutation.data.status === "synced" && (
        <Alert>
          <AlertDescription>
            {mutation.data.posts_ingested} posts ingested, {mutation.data.posts_skipped} skipped.
          </AlertDescription>
        </Alert>
      )}
      {mutation.isSuccess && mutation.data.status === "error" && (
        <Alert variant="destructive">
          <AlertDescription>{mutation.data.message}</AlertDescription>
        </Alert>
      )}
      {mutation.isError && (
        <Alert variant="destructive">
          <AlertDescription>{(mutation.error as Error).message}</AlertDescription>
        </Alert>
      )}
    </form>
  );
}
