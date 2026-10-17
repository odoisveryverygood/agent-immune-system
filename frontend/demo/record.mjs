// Records the real local UI; captions exist only in this browser capture.
import { chromium } from "@playwright/test";
import { rename } from "node:fs/promises";
import { fileURLToPath } from "node:url";
const dir = fileURLToPath(new URL(".", import.meta.url));
const browser = await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  recordVideo: { dir, size: { width: 1440, height: 1000 } },
  reducedMotion: "reduce",
});
const page = await context.newPage();
await page.goto(process.env.DEMO_URL || "http://127.0.0.1:5173");
await page.getByText("Fixture walkthrough", { exact: true }).waitFor();
await page.evaluate(() => document.fonts.ready);
const start = Date.now();
async function until(seconds) {
  const remaining = start + seconds * 1000 - Date.now();
  if (remaining > 0) await page.waitForTimeout(remaining);
}
async function caption(text) {
  await page.evaluate((text) => {
    let el = document.getElementById("capture-caption");
    if (!el) {
      el = document.createElement("div");
      el.id = "capture-caption";
      Object.assign(el.style, {
        position: "fixed",
        left: "50%",
        bottom: "22px",
        transform: "translateX(-50%)",
        width: "max-content",
        maxWidth: "1050px",
        padding: "16px 25px",
        background: "#142f29f5",
        color: "#f0f6e7",
        border: "1px solid #6f8c61",
        borderRadius: "9px",
        font: "500 19px/1.6 system-ui",
        textAlign: "center",
        whiteSpace: "pre-line",
        zIndex: "1000",
        boxShadow: "0 8px 40px #142f2933",
        pointerEvents: "none",
      });
      document.body.append(el);
    }
    el.textContent = text;
  }, text);
}
await caption(
  "Agent Immune System · fixture walkthrough\nIllustrative evidence. No models or sandbox execution.",
);
await until(8);
await page.locator(".task-node").first().click();
await page.locator(".tree-panel").scrollIntoViewIfNeeded();
await caption(
  "Follow root → child → grandchild.\nEach task preserves its ID, parent, depth and spawn reason.",
);
await until(12);
await page.locator(".task-node").nth(1).click();
await until(15);
await page.locator(".task-node").nth(2).click();
await until(18);
await caption(
  "An accepted $0 order violates the trusted $450 minimum.\nInspect the receipt; a model’s claim alone is insufficient.",
);
await page.locator(".receipt").first().locator("summary").click();
await until(25);
await page.locator(".receipt").first().locator("summary").click();
await until(29);
await page.getByRole("tab", { name: "Policy patch" }).click();
await caption(
  "A constrained patch changes only approved policy fields.\nPolicy versions and evidence references stay visible.",
);
await until(39);
await page
  .getByRole("heading", { name: "Repair verification" })
  .scrollIntoViewIfNeeded();
await caption(
  "Illustrative replay: denied. Repair verification: incomplete.\nHeld-out attacks, legitimate purchases and review have not run.",
);
await until(49);
await page
  .getByRole("button", { name: "Start investigation", exact: true })
  .click();
await caption(
  "Real API start, shared budget and explicit failures.\nBackend and live sponsor integrations still need verification.",
);
await until(60);
await context.close();
const video = await page.video().path();
await rename(video, `${dir}/walkthrough.webm`);
await browser.close();
console.log(
  "Saved captioned real-browser fixture recording: demo/walkthrough.webm",
);
