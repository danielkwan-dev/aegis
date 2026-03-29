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
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
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

          {/* Hex dashboard shortcut */}
          <a
            href="https://app.hex.tech/019d3274-b978-7110-8122-c30aea21a224/app/Aegis-032pYjM1wOXFrsi6nXOwag/latest"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.35rem",
              padding: "0.3rem 0.75rem",
              backgroundColor: "#06b6d412",
              border: "1px solid #06b6d430",
              borderRadius: "5px",
              color: "#06b6d4",
              fontSize: "0.6rem",
              fontWeight: 600,
              letterSpacing: "0.08em",
              textDecoration: "none",
              textTransform: "uppercase",
              whiteSpace: "nowrap",
              transition: "background-color 0.2s ease, border-color 0.2s ease",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.backgroundColor =
                "#06b6d422";
              (e.currentTarget as HTMLAnchorElement).style.borderColor =
                "#06b6d460";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.backgroundColor =
                "#06b6d412";
              (e.currentTarget as HTMLAnchorElement).style.borderColor =
                "#06b6d430";
            }}
          >
            <svg
              width="10"
              height="10"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            Hex Dashboard ↗
          </a>
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
