/**
 * Judge Snapshot — populated-state screenshots for the judge tour.
 *
 * The existing `phase2-ui.spec.ts` captures empty-state screens
 * (no project loaded), which is the regression target for the
 * Phase-2 audit. This spec captures the OPPOSITE — the seeded demo
 * project `proj_demo_seed01` in its fully-loaded "this is what the
 * judge actually sees" state, with stories, tasks, tests, Kanban,
 * traceability, and Jira CSV preview visible.
 *
 * Output → helix-frontend/docs/judge-screenshots/*.png
 * Walkthrough → docs/SCREENSHOT_TOUR.md (uses these filenames verbatim)
 *
 * Run locally:
 *
 *   # Terminal A — backend (port 8765)
 *   cd helix-backend; .\run.ps1
 *
 *   # Terminal B — frontend (port 5173, npm run dev starts via webServer config)
 *   cd helix-frontend
 *   npx playwright test e2e/judge-snapshot.spec.ts --project=chromium
 *
 * If the demo project isn't seeded yet (first boot), wait ~60 s for
 * `helix-backend/scripts/seed.py` to finish before re-running.
 */
import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const OUT_DIR = path.join(__dirname, "..", "docs", "judge-screenshots");
const EXPORT_DIR = path.join(REPO_ROOT, "docs", "sample-exports");

const demoEmail = process.env.E2E_LOGIN_EMAIL || "demo@demo.com";
const demoPassword = process.env.E2E_LOGIN_PASSWORD || "demo123";
const SEED_PROJECT = process.env.JUDGE_SEED_PROJECT_ID || "proj_demo_seed01";

const DESKTOP = { width: 1440, height: 900 } as const;

// Record a WebM video of the entire flow so we have a pre-recorded
// fallback demo if the live system is offline at pitch time. The
// video is written by Playwright into test-results/<test>/video.webm
// and a post-step copies it into docs/judge-screenshots/.
test.use({
  video: { mode: "on", size: { width: DESKTOP.width, height: DESKTOP.height } },
});

async function login(page: Page) {
  await page.addInitScript(() => {
    try {
      window.localStorage.setItem("helix_onboarding_seen", "1");
    } catch {
      /* noop */
    }
  });
  await page.goto("/login");
  await page.getByLabel(/email or username/i).fill(demoEmail);
  await page.getByLabel(/^password$/i).fill(demoPassword);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/mission-control/, { timeout: 30_000 });
}

async function shot(page: Page, filename: string, opts?: { fullPage?: boolean }) {
  await page.waitForTimeout(600);
  const file = path.join(OUT_DIR, filename);
  await page.screenshot({ path: file, fullPage: opts?.fullPage ?? true });
  /* eslint-disable-next-line no-console */
  console.log(`[judge-snapshot] saved ${path.relative(process.cwd(), file)}`);
}

async function dumpExport(
  page: Page,
  urlPath: string,
  filename: string,
  token: string,
) {
  const res = await page.request.get(urlPath, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok()) {
    /* eslint-disable-next-line no-console */
    console.warn(
      `[judge-snapshot] export ${urlPath} returned ${res.status()} — skipping ${filename}`,
    );
    return;
  }
  const body = await res.body();
  const target = path.join(EXPORT_DIR, filename);
  fs.writeFileSync(target, body);
  /* eslint-disable-next-line no-console */
  console.log(`[judge-snapshot] saved ${path.relative(process.cwd(), target)} (${body.length} bytes)`);
}

async function readSessionToken(page: Page): Promise<string> {
  return await page.evaluate(() => {
    try {
      return sessionStorage.getItem("helix_token") || localStorage.getItem("helix_token") || "";
    } catch {
      return "";
    }
  });
}

async function copyVideo(page: Page) {
  // Playwright writes the video on context.close(); flush it now.
  const video = page.video();
  if (!video) return;
  try {
    const source = await video.path();
    if (!source) return;
    const dest = path.join(OUT_DIR, "judge-walkthrough.webm");
    // The source file is only finalized after the context closes; copy
    // happens in afterAll once Playwright has flushed it.
    /* eslint-disable-next-line no-console */
    console.log(`[judge-snapshot] video will be copied from ${source} to ${dest}`);
    return { source, dest };
  } catch (err) {
    /* eslint-disable-next-line no-console */
    console.warn(`[judge-snapshot] video copy skipped: ${(err as Error).message}`);
  }
}

test.describe("Judge snapshot — populated-state demo screenshots", () => {
  let videoCopy: { source: string; dest: string } | undefined;

  test.beforeAll(() => {
    fs.mkdirSync(OUT_DIR, { recursive: true });
    fs.mkdirSync(EXPORT_DIR, { recursive: true });
  });

  test.afterAll(async () => {
    if (!videoCopy) return;
    // Wait briefly for Playwright to finalize the WebM file on disk.
    for (let i = 0; i < 20; i += 1) {
      if (fs.existsSync(videoCopy.source) && fs.statSync(videoCopy.source).size > 10_000) break;
      await new Promise((r) => setTimeout(r, 500));
    }
    try {
      fs.copyFileSync(videoCopy.source, videoCopy.dest);
      /* eslint-disable-next-line no-console */
      console.log(
        `[judge-snapshot] copied video → ${path.relative(process.cwd(), videoCopy.dest)} ` +
          `(${fs.statSync(videoCopy.dest).size} bytes)`,
      );
    } catch (err) {
      /* eslint-disable-next-line no-console */
      console.warn(`[judge-snapshot] video copy failed: ${(err as Error).message}`);
    }
  });

  test("capture the judge walkthrough", async ({ page }) => {
    await page.setViewportSize(DESKTOP);

    // 1. Landing — the hero (logged out)
    await page.context().clearCookies();
    await page.goto("/");
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    await shot(page, "01-landing.png");

    // 2. Log in as the seeded demo user (lands on Mission Control)
    await login(page);
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    await shot(page, "02-mission-control.png");

    // 3. Judge Demo screen
    await page.goto("/judge-demo");
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    await shot(page, "03-judge-demo.png");

    // 4. AI Workspace — Delivery Package fully loaded for the seeded project
    await page.goto(`/project/${SEED_PROJECT}/ai-workspace`);
    await page.waitForLoadState("networkidle", { timeout: 30_000 }).catch(() => {});

    // Give the parallel artifact fetches + delivery sections a moment to settle.
    await page
      .locator(".dp-section, .p5-panel, .hx-export-hub")
      .first()
      .waitFor({ state: "visible", timeout: 30_000 })
      .catch(() => {});
    await page.waitForTimeout(2_000);
    await shot(page, "04-delivery-package--full.png");

    // 5. Scroll to the Jira export hub for a tight crop
    const exportHub = page.locator(".hx-export-hub").first();
    if ((await exportHub.count()) > 0) {
      await exportHub.scrollIntoViewIfNeeded();
      await page.waitForTimeout(400);
      await shot(page, "05-export-hub.png", { fullPage: false });
    }

    // 6. Scroll to the traceability / trace-flow animator
    const trace = page.locator(".trace-flow-anim, [aria-label*='Traceability']").first();
    if ((await trace.count()) > 0) {
      await trace.scrollIntoViewIfNeeded();
      await page.waitForTimeout(400);
      await shot(page, "06-traceability.png", { fullPage: false });
    }

    // 7. Jira CSV preview panel
    const csv = page.locator(".jira-csv-preview, [class*='jira'][class*='preview']").first();
    if ((await csv.count()) > 0) {
      await csv.scrollIntoViewIfNeeded();
      await page.waitForTimeout(400);
      await shot(page, "07-jira-csv-preview.png", { fullPage: false });
    }

    // 8. Sanity assertion: the page rendered SOMETHING that looks like the
    //    delivery package, not the empty state.
    const bodyText = (await page.locator("body").innerText()).toLowerCase();
    const hasDeliveryContent = ["stories", "tasks", "tests", "readiness", "approve"].some(
      (token) => bodyText.includes(token),
    );
    expect(hasDeliveryContent, "Delivery Package should contain stories/tasks/tests").toBeTruthy();

    // 9. Pull the actual deliverable artefacts from the live API so the
    //    repo carries committed sample exports for async judges. The
    //    backend uses Bearer-JWT auth from sessionStorage — read the
    //    token Vite stored after login and forward it explicitly.
    const token = await readSessionToken(page);
    if (!token) {
      /* eslint-disable-next-line no-console */
      console.warn("[judge-snapshot] no auth token in sessionStorage — exports will 401");
    }
    // /api/export/csv is the tasks-only flat CSV (engineering deliverable).
    await dumpExport(page, `/api/export/csv/${SEED_PROJECT}`, "checkout-revamp.tasks.csv", token);
    // /api/backlog/{id}/jira-csv is the FULL Jira-importable CSV with
    // Epic / Story / Task / Sub-task hierarchy and parent links — this
    // is the CSV the preview panel in the UI renders.
    await dumpExport(
      page,
      `/api/backlog/${SEED_PROJECT}/jira-csv`,
      "checkout-revamp.jira.csv",
      token,
    );
    await dumpExport(
      page,
      `/api/backlog/${SEED_PROJECT}/ado-csv`,
      "checkout-revamp.azure-devops.csv",
      token,
    );
    await dumpExport(page, `/api/export/markdown/${SEED_PROJECT}`, "checkout-revamp.brief.md", token);
    await dumpExport(page, `/api/export/json/${SEED_PROJECT}`, "checkout-revamp.backlog.json", token);

    // 10. Register the video for post-run copy. The actual file is only
    //     flushed to disk by Playwright after the context closes, so the
    //     real copy happens in afterAll().
    videoCopy = await copyVideo(page);
  });
});
