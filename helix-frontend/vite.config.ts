import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  /** Pre-bundle GSAP subpaths so dev server does not return 504 "Outdated Optimize Dep" after cache churn. */
  optimizeDeps: {
    include: ["gsap", "gsap/ScrollTrigger", "@gsap/react"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8765",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
