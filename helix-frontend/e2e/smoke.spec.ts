import { expect, test, type Page } from "@playwright/test";

const demoEmail = process.env.E2E_LOGIN_EMAIL || "demo@demo.com";
const demoPassword = process.env.E2E_LOGIN_PASSWORD || "demo123";

const PRODUCT_ROUTES = [
  "/mission-control",
  "/ai-workspace",
  "/delivery-command",
  "/copilot",
  "/settings",
];

async function loginToMissionControl(page: Page) {
  await page.goto("/login");
  await page.getByLabel(/email or username/i).fill(demoEmail);
  await page.getByLabel(/^password$/i).fill(demoPassword);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/mission-control/, { timeout: 30_000 });
}

test.describe("smoke", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      try {
        window.localStorage.setItem("helix_onboarding_seen", "1");
      } catch {
        /* noop */
      }
    });
  });

  test("login → mission control → launch controls visible", async ({ page }) => {
    await loginToMissionControl(page);

    await expect(page.getByRole("heading", { name: /mission control/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /launch ai team/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /load demo prd/i })).toBeEnabled();
  });

  test("product routes load after login", async ({ page }) => {
    await loginToMissionControl(page);

    for (const path of PRODUCT_ROUTES) {
      await page.goto(path);
      await page.waitForLoadState("domcontentloaded");
      await expect(page.locator("body")).toBeVisible();
    }
  });

  test("legacy redirects (new, delivery-package, workspace)", async ({ page }) => {
    await loginToMissionControl(page);

    await page.goto("/new");
    await expect(page).toHaveURL(/mission-control/, { timeout: 15_000 });

    await page.goto("/delivery-package");
    await expect(page).toHaveURL(/ai-workspace/, { timeout: 15_000 });

    await page.goto("/workspace");
    await expect(page).toHaveURL(/copilot/, { timeout: 15_000 });
  });

  test("judge demo route loads", async ({ page }) => {
    await loginToMissionControl(page);

    await page.goto("/judge-demo");
    await expect(page).toHaveURL(/judge-demo/, { timeout: 15_000 });
    await expect(
      page.getByRole("button", { name: /start autonomous sdlc demo/i }),
    ).toBeVisible();
  });
});
