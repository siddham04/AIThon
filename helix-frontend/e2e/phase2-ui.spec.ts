import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = path.join(__dirname, "..", "docs", "phase2-screenshots");

const demoEmail = process.env.E2E_LOGIN_EMAIL || "demo@demo.com";
const demoPassword = process.env.E2E_LOGIN_PASSWORD || "demo123";

const PAGES = [
  { name: "mission-control", path: "/mission-control", label: "Mission Control" },
  { name: "ai-workspace", path: "/ai-workspace", label: "AI Workspace" },
  { name: "delivery-command", path: "/delivery-command", label: "Delivery Center" },
  { name: "copilot", path: "/copilot", label: "Copilot" },
  { name: "settings", path: "/settings", label: "Settings" },
] as const;

const VIEWPORTS = [
  { id: "mobile", width: 390, height: 844 },
  { id: "tablet", width: 768, height: 1024 },
  { id: "desktop", width: 1440, height: 900 },
] as const;

type Finding = {
  page: string;
  viewport: string;
  category: string;
  severity: "high" | "medium" | "low";
  detail: string;
};

const findings: Finding[] = [];

function record(
  page: string,
  viewport: string,
  category: string,
  severity: Finding["severity"],
  detail: string,
) {
  findings.push({ page, viewport, category, severity, detail });
}

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

async function auditPage(page: Page, pageName: string, viewportId: string) {
  const overflow = await page.evaluate(() => {
    const doc = document.documentElement;
    const body = document.body;
    const sw = Math.max(doc.scrollWidth, body.scrollWidth);
    const cw = doc.clientWidth;
    return { scrollWidth: sw, clientWidth: cw, hasOverflow: sw > cw + 2 };
  });
  if (overflow.hasOverflow) {
    record(
      pageName,
      viewportId,
      "overflow",
      viewportId === "mobile" ? "high" : "medium",
      `Horizontal overflow: scrollWidth ${overflow.scrollWidth}px > clientWidth ${overflow.clientWidth}px`,
    );
  }

  const clipped = await page.evaluate(() => {
    const main = document.querySelector(".app-main-content, .app-outlet-wrap, main");
    if (!main) return [];
    const rect = main.getBoundingClientRect();
    const issues: string[] = [];
    main.querySelectorAll("button, input, textarea, h1, h2").forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.right > window.innerWidth + 4) {
        issues.push(`${el.tagName}.${(el.className || "").toString().slice(0, 40)} right=${Math.round(r.right)}`);
      }
    });
    if (rect.width > window.innerWidth) {
      issues.push(`main content width ${Math.round(rect.width)} > viewport`);
    }
    return issues.slice(0, 5);
  });
  if (clipped.length) {
    record(pageName, viewportId, "alignment", "medium", `Elements past viewport edge: ${clipped.join("; ")}`);
  }

  const fonts = await page.evaluate(() => {
    const families = new Set<string>();
    document.querySelectorAll("h1, h2, .page-hero h1, .native-page h1, .sidebar, .nav-label").forEach((el) => {
      const f = getComputedStyle(el).fontFamily;
      if (f) families.add(f.split(",")[0].trim().replace(/['"]/g, ""));
    });
    return [...families];
  });
  if (fonts.length > 2) {
    record(pageName, viewportId, "font", "low", `Multiple heading/nav font stacks: ${fonts.join(", ")}`);
  }

  const paddingIssues = await page.evaluate(() => {
    const content = document.querySelector(".app-main-content");
    if (!content) return null;
    const cs = getComputedStyle(content);
    const pl = parseFloat(cs.paddingLeft) || 0;
    const pr = parseFloat(cs.paddingRight) || 0;
    if (pl < 8 && window.innerWidth < 500) return `main padding-left only ${pl}px on narrow viewport`;
    if (pr < 8 && window.innerWidth < 500) return `main padding-right only ${pr}px`;
    return null;
  });
  if (paddingIssues) {
    record(pageName, viewportId, "padding", "medium", paddingIssues);
  }

  const theme = await page.evaluate(() => {
    const root = getComputedStyle(document.documentElement);
    const body = getComputedStyle(document.body);
    const bg = root.getPropertyValue("--hx-bg") || body.backgroundColor;
    const isDark =
      body.backgroundColor === "rgba(0, 0, 0, 0)" ||
      body.backgroundColor.includes("12") ||
      body.backgroundColor.includes("rgb(8") ||
      body.backgroundColor.includes("rgb(10");
    const sidebar = document.querySelector(".sidebar");
    const sidebarBg = sidebar ? getComputedStyle(sidebar).backgroundColor : "";
    return { bg, isDark, sidebarBg };
  });
  if (!theme.isDark && !theme.bg.includes("#0")) {
    record(pageName, viewportId, "theme", "low", `Unexpected light body background: ${theme.bg}`);
  }
}

test.describe("Phase 2 — UI verification", () => {
  test.beforeAll(() => {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  });

  test("all product pages @ mobile / tablet / desktop", async ({ page }) => {
    await login(page);

    for (const vp of VIEWPORTS) {
      await page.setViewportSize({ width: vp.width, height: vp.height });

      for (const p of PAGES) {
        await page.goto(p.path);
        await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
        await page.waitForTimeout(400);

        const shotPath = path.join(SCREENSHOT_DIR, `${p.name}--${vp.id}.png`);
        await page.screenshot({ path: shotPath, fullPage: true });

        await auditPage(page, p.label, vp.id);

        const bodyVisible = await page.locator("body").isVisible();
        expect(bodyVisible).toBeTruthy();

        if (p.path === "/workspace" && vp.id === "mobile") {
          const chat = page.locator(".workspace-page, .ws-shell, [class*='workspace']").first();
          if ((await chat.count()) === 0) {
            record(p.label, vp.id, "layout", "medium", "Workspace shell selector not found for layout check");
          }
        }

        if (p.path === "/delivery-package" && vp.id === "mobile") {
          const sections = await page.locator("section, .dp-section, .package-section").count();
          if (sections === 0) {
            record(p.label, vp.id, "layout", "low", "No section elements detected on Delivery Package");
          }
        }
      }
    }

    fs.writeFileSync(
      path.join(SCREENSHOT_DIR, "findings.json"),
      JSON.stringify(findings, null, 2),
      "utf8",
    );
  });
});
