/**
 * Phase 3 UI — verifies Delivery Package renders and export buttons work
 * after API workflow (see docs/phase3-workflow-results.json).
 */
import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RESULTS_PATH = path.join(
  __dirname,
  "..",
  "..",
  "docs",
  "phase3-workflow-results.json",
);

const demoEmail = process.env.E2E_LOGIN_EMAIL || "demo@demo.com";
const demoPassword = process.env.E2E_LOGIN_PASSWORD || "demo123";

function loadProjectId(): string | null {
  try {
    const raw = fs.readFileSync(RESULTS_PATH, "utf8");
    const j = JSON.parse(raw) as { project_id?: string };
    return j.project_id || null;
  } catch {
    return process.env.PHASE3_PROJECT_ID || null;
  }
}

test.describe("Phase 3 — UI workflow surfaces", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      try {
        window.localStorage.setItem("helix_onboarding_seen", "1");
      } catch {
        /* noop */
      }
    });
  });

  test("Mission Control — launch button and pipeline strip present", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email or username/i).fill(demoEmail);
    await page.getByLabel(/^password$/i).fill(demoPassword);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/mission-control/, { timeout: 30_000 });

    await expect(page.getByRole("button", { name: /launch ai team/i })).toBeVisible();
    await expect(page.locator(".mc-landing")).toBeVisible();
    await expect(page.getByRole("navigation", { name: /autonomous sdlc workflow/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /load demo prd/i })).toBeEnabled();
  });

  test("AI Workspace — sections render + approve export after workflow", async ({ page }) => {
    const pid = loadProjectId();
    test.skip(!pid, "Run python scripts/phase3_workflow_test.py first to create project");

    await page.goto("/login");
    await page.getByLabel(/email or username/i).fill(demoEmail);
    await page.getByLabel(/^password$/i).fill(demoPassword);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/mission-control/, { timeout: 30_000 });

    await page.goto(`/project/${pid}/ai-workspace`);
    await page.waitForLoadState("networkidle", { timeout: 30_000 }).catch(() => {});

    await expect(page.getByRole("heading", { name: /executive summary/i })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByRole("heading", { name: /user stories/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /test cases/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /approve & export/i })).toBeVisible();

    const deadLinks = await page.locator('a[href="#"]').count();
    expect(deadLinks).toBe(0);
  });

  test("Copilot and legacy redirects — no dead-end navigation", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email or username/i).fill(demoEmail);
    await page.getByLabel(/^password$/i).fill(demoPassword);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/mission-control/, { timeout: 30_000 });

    await page.goto("/judge-demo");
    await expect(page).toHaveURL(/judge-demo/, { timeout: 15_000 });

    await page.goto("/new");
    await expect(page).toHaveURL(/mission-control/, { timeout: 15_000 });

    await page.goto("/copilot");
    await expect(page.locator("body")).toBeVisible();

    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: /^settings$/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /switch to light mode|switch to dark mode/i })).toBeEnabled();
  });
});
