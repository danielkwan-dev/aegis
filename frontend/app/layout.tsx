import { UserProvider } from "@auth0/nextjs-auth0/client";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Aegis — Privacy Shield",
  description: "Proactive privacy tool that prevents accidental doxxing",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily:
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          backgroundColor: "#0a0a0a",
          color: "#e0e0e0",
          minHeight: "100vh",
        }}
      >
        <UserProvider>{children}</UserProvider>
      </body>
    </html>
  );
}
