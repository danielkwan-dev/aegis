import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
    // pool: "threads" avoids a worker-startup timeout with the default
    // "forks" pool that occurs in this environment because the repo path
    // contains a space (C:\Users\Daniel Kwan\...); threads runs reliably.
    pool: "threads",
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
