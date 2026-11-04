import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    // Bound parallelism on Windows and avoid spawning a process per test file.
    pool: "threads",
    maxWorkers: 2
  }
});
