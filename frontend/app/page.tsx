"use client";

import SimulateForm from "@/components/SimulateForm";

export default function Dashboard() {
  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "2rem 1.5rem" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          marginBottom: "2.5rem",
          paddingBottom: "1rem",
          borderBottom: "1px solid #141618",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                backgroundColor: "#dc2626",
                boxShadow: "0 0 8px rgba(220,38,38,0.5)",
              }}
            />
            <h1
              style={{
                margin: 0,
                fontSize: "1.4rem",
                fontWeight: 700,
                letterSpacing: "0.08em",
                color: "#e0e0e0",
              }}
            >
              AEGIS
            </h1>
          </div>
          <p
            style={{
              margin: "0.3rem 0 0",
              color: "#444",
              fontSize: "0.7rem",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
            }}
          >
            Security Dashboard // Privacy Intelligence
          </p>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            color: "#333",
            fontSize: "0.65rem",
            letterSpacing: "0.06em",
          }}
        >
          <div
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              backgroundColor: "#16a34a",
            }}
          />
          ENGINE ONLINE
        </div>
      </div>

      {/* Main Form */}
      <SimulateForm />

      {/* Footer */}
      <div
        style={{
          marginTop: "3rem",
          paddingTop: "1rem",
          borderTop: "1px solid #141618",
          textAlign: "center",
          color: "#222",
          fontSize: "0.6rem",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
        }}
      >
        Aegis Privacy Intelligence Engine
      </div>
    </div>
  );
}
