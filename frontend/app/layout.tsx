import type { Metadata } from "next";
import "./globals.css";
import MatrixRain from "@/components/MatrixRain";

export const metadata: Metadata = {
  title: "Aegis Security Dashboard",
  description:
    "Proactive privacy intelligence that prevents accidental doxxing",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ position: "relative" }}>
        <MatrixRain side="left" width={130} />
        <MatrixRain side="right" width={130} />
        <div style={{ position: "relative", zIndex: 1 }}>{children}</div>
      </body>
    </html>
  );
}
