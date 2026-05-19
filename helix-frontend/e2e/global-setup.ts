import type { FullConfig } from "@playwright/test";

export default async function globalSetup(_config: FullConfig) {
  const backend = (process.env.E2E_BACKEND_URL || "http://127.0.0.1:8765").replace(/\/$/, "");
  const waitMs = Number(process.env.E2E_BACKEND_WAIT_MS || "90000");
  const deadline = Date.now() + waitMs;
  let lastErr = "";

  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${backend}/api/health`, { signal: AbortSignal.timeout(5000) });
      if (res.ok) return;
      lastErr = `HTTP ${res.status}`;
    } catch (e) {
      lastErr = e instanceof Error ? e.message : String(e);
    }
    await new Promise((r) => setTimeout(r, 2000));
  }

  throw new Error(
    `Helix backend not reachable at ${backend}/api/health (last error: ${lastErr}). ` +
      `Start the API (e.g. uvicorn on 8765) or set E2E_BACKEND_URL / E2E_BACKEND_WAIT_MS.`,
  );
}
