import { expect, test } from "@playwright/test";

const demoEmail = process.env.E2E_LOGIN_EMAIL || "demo@demo.com";
const demoPassword = process.env.E2E_LOGIN_PASSWORD || "demo123";

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

  test("login → sample project → dashboard shows summary or readiness", async ({ page }) => {
    await page.goto("/login");

    await page.getByLabel("Email", { exact: true }).fill(demoEmail);
    await page.getByLabel("Password", { exact: true }).fill(demoPassword);
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL(/\/new$/);

    await page.getByRole("button", { name: "Load sample requirement" }).click();
    await page.getByRole("button", { name: "Ingest" }).click();

    await page.waitForURL(/\/project\/[^/]+$/, { timeout: 180_000 });

    const summaryOrReadiness = page.locator(".summary-card, section.readiness-panel");
    await expect(summaryOrReadiness.first()).toBeVisible({ timeout: 60_000 });
  });
});
