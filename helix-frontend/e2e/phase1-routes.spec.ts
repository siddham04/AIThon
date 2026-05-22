import { expect, test } from "@playwright/test";

const demoEmail = process.env.E2E_LOGIN_EMAIL || "demo@demo.com";
const demoPassword = process.env.E2E_LOGIN_PASSWORD || "demo123";

const PRODUCT_ROUTES = [
  "/mission-control",
  "/ai-workspace",
  "/delivery-command",
  "/copilot",
  "/settings",
];

/** Must match LEGACY_GLOBAL_REDIRECTS in productFlow.js */
const LEGACY_REDIRECTS = [
  ["/dashboard", "/mission-control"],
  ["/new", "/mission-control"],
  ["/winning-demo", "/judge-demo"],
  ["/demo", "/mission-control"],
  ["/judge-demo", "/judge-demo"],
  ["/delivery-package", "/ai-workspace"],
  ["/delivery-readiness", "/ai-workspace"],
  ["/workspace", "/copilot"],
];

test.describe("Phase 1 — routes & console", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      try {
        window.localStorage.setItem("helix_onboarding_seen", "1");
      } catch {
        /* noop */
      }
    });
  });

  test("login lands on mission control", async ({ page }) => {
    const errors: string[] = [];
    const warnings: string[] = [];
    page.on("console", (msg) => {
      const t = msg.type();
      const text = msg.text();
      if (t === "error") errors.push(text);
      if (t === "warning") warnings.push(text);
    });
    page.on("pageerror", (err) => errors.push(err.message));

    await page.goto("/login");
    await page.getByLabel(/email or username/i).fill(demoEmail);
    await page.getByLabel(/^password$/i).fill(demoPassword);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/mission-control/, { timeout: 30_000 });

    for (const path of PRODUCT_ROUTES) {
      await page.goto(path);
      await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
      await expect(page.locator("body")).toBeVisible();
    }

    for (const [from, toSegment] of LEGACY_REDIRECTS) {
      await page.goto(from);
      await expect(page).toHaveURL(new RegExp(toSegment.replace("/", "\\/")), {
        timeout: 15_000,
      });
    }

    const hydration = errors.filter((e) =>
      /hydration|did not match|Text content does not match/i.test(e),
    );
    expect(hydration, `hydration errors: ${hydration.join("; ")}`).toHaveLength(0);

    const fatal = errors.filter(
      (e) =>
        !/favicon|Failed to load resource.*404|ResizeObserver|chunk/i.test(e) &&
        !e.includes("net::ERR"),
    );
    if (fatal.length) console.log("console errors:", fatal);
    if (warnings.length) console.log("console warnings:", warnings.slice(0, 10));
    expect(fatal, `console errors on product routes: ${fatal.join("; ")}`).toHaveLength(0);
  });
});
