"use client";

import SimulateForm from "@/components/SimulateForm";

const MOCK_USER = { name: "Demo User", email: "demo@aegis.dev" };

export default function Dashboard() {
  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: "2rem 1.5rem" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "2.5rem",
          borderBottom: "1px solid #222",
          paddingBottom: "1rem",
        }}
      >
        <div>
          <h1
            style={{
              margin: 0,
              fontSize: "1.5rem",
              fontWeight: 700,
              letterSpacing: "-0.01em",
            }}
          >
            🛡️ Aegis
          </h1>
          <p style={{ margin: "0.25rem 0 0", color: "#666", fontSize: "0.85rem" }}>
            Threat detection simulator
          </p>
        </div>
        <span style={{ color: "#888", fontSize: "0.85rem" }}>
          {MOCK_USER.name}
        </span>
      </div>

      {/* Main Form */}
      <SimulateForm />
    </div>
  );
}
