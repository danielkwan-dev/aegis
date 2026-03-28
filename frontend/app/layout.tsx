import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Aegis Security Dashboard",
  description: "Proactive privacy intelligence that prevents accidental doxxing",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <style>{`
          @keyframes gaugeAnimate {
            from { stroke-dashoffset: 314; }
          }
          @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
          }
          @keyframes pulseGlow {
            0%, 100% { box-shadow: 0 0 8px rgba(220,38,38,0.3); }
            50% { box-shadow: 0 0 20px rgba(220,38,38,0.6); }
          }
          @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
          }
          * { box-sizing: border-box; }
          ::-webkit-scrollbar { width: 6px; }
          ::-webkit-scrollbar-track { background: #0a0a0a; }
          ::-webkit-scrollbar-thumb { background: #222; border-radius: 3px; }
        `}</style>
      </head>
      <body
        style={{
          margin: 0,
          fontFamily:
            "'SF Mono', 'Fira Code', 'JetBrains Mono', 'Cascadia Code', monospace",
          backgroundColor: "#08090a",
          color: "#c8ccd0",
          minHeight: "100vh",
        }}
      >
        {children}
      </body>
    </html>
  );
}
