"use client";

export default function Home() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        padding: "2rem",
      }}
    >
      <div
        style={{
          maxWidth: 420,
          width: "100%",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: "3rem", marginBottom: "0.25rem" }}>🛡️</div>
        <h1
          style={{
            fontSize: "2.5rem",
            fontWeight: 700,
            margin: "0 0 0.5rem",
            letterSpacing: "-0.02em",
          }}
        >
          Aegis
        </h1>
        <p
          style={{
            color: "#888",
            fontSize: "1.05rem",
            margin: "0 0 2.5rem",
            lineHeight: 1.5,
          }}
        >
          Proactive privacy shield.
          <br />
          Catch personal info before you post it.
        </p>

        <a
          href="/api/auth/login"
          style={{
            display: "inline-block",
            padding: "0.85rem 2.5rem",
            backgroundColor: "#fff",
            color: "#0a0a0a",
            borderRadius: "8px",
            textDecoration: "none",
            fontWeight: 600,
            fontSize: "1rem",
            transition: "opacity 0.15s",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.85")}
          onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
        >
          Sign in to continue
        </a>

        <p style={{ color: "#555", fontSize: "0.8rem", marginTop: "2rem" }}>
          Secured with Auth0
        </p>
      </div>
    </div>
  );
}
