"use client";

import { useUser } from "@auth0/nextjs-auth0/client";
import SimulateForm from "@/components/SimulateForm";

export default function Dashboard() {
  const { user, isLoading } = useUser();

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          color: "#888",
        }}
      >
        Loading...
      </div>
    );
  }

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
            Privacy simulator
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <span style={{ color: "#888", fontSize: "0.85rem" }}>
            {user?.name ?? user?.email}
          </span>
          <a
            href="/api/auth/logout"
            style={{
              padding: "0.4rem 1rem",
              border: "1px solid #333",
              borderRadius: "6px",
              color: "#ccc",
              textDecoration: "none",
              fontSize: "0.8rem",
            }}
          >
            Log out
          </a>
        </div>
      </div>

      {/* Main Form */}
      <SimulateForm />
    </div>
  );
}
