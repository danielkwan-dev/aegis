"use client";

import { useState, useRef } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SimulateForm() {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleSubmit() {
    setLoading(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("text", text);
      if (file) {
        formData.append("image", file);
      }

      const res = await fetch(`${API_URL}/api/simulate`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      console.log("Aegis response:", data);
      setResult(JSON.stringify(data, null, 2));
    } catch (err) {
      console.error("Simulate error:", err);
      setResult("Error connecting to backend. Is the FastAPI server running?");
    } finally {
      setLoading(false);
    }
  }

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "0.75rem",
    backgroundColor: "#111",
    border: "1px solid #333",
    borderRadius: "8px",
    color: "#e0e0e0",
    fontSize: "0.95rem",
    outline: "none",
    boxSizing: "border-box",
  };

  return (
    <div>
      <h2
        style={{
          fontSize: "1.15rem",
          fontWeight: 600,
          margin: "0 0 0.25rem",
        }}
      >
        Simulate a post
      </h2>
      <p style={{ color: "#666", fontSize: "0.85rem", margin: "0 0 1.5rem" }}>
        Paste your draft text and optionally attach an image. Aegis will scan
        for personal information you may not want to share.
      </p>

      {/* Text area */}
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste your draft post here..."
        rows={6}
        style={{
          ...inputStyle,
          resize: "vertical",
          fontFamily: "inherit",
          marginBottom: "1rem",
        }}
      />

      {/* Image upload */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          marginBottom: "1.5rem",
        }}
      >
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          style={{
            padding: "0.5rem 1.25rem",
            backgroundColor: "#1a1a1a",
            border: "1px solid #333",
            borderRadius: "6px",
            color: "#ccc",
            cursor: "pointer",
            fontSize: "0.85rem",
          }}
        >
          📎 Attach image
        </button>
        <span style={{ color: "#666", fontSize: "0.85rem" }}>
          {file ? file.name : "No file selected"}
        </span>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          style={{ display: "none" }}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={loading || (!text && !file)}
        style={{
          width: "100%",
          padding: "0.85rem",
          backgroundColor: loading ? "#333" : "#fff",
          color: loading ? "#888" : "#0a0a0a",
          border: "none",
          borderRadius: "8px",
          fontWeight: 600,
          fontSize: "1rem",
          cursor: loading ? "not-allowed" : "pointer",
          transition: "opacity 0.15s",
        }}
      >
        {loading ? "Scanning..." : "Simulate"}
      </button>

      {/* Result */}
      {result && (
        <pre
          style={{
            marginTop: "1.5rem",
            padding: "1rem",
            backgroundColor: "#111",
            border: "1px solid #222",
            borderRadius: "8px",
            fontSize: "0.8rem",
            color: "#aaa",
            overflow: "auto",
            whiteSpace: "pre-wrap",
          }}
        >
          {result}
        </pre>
      )}
    </div>
  );
}
