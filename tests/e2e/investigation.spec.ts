import {
  test,
  expect,
} from "../../frontend/node_modules/@playwright/test/index.mjs";
test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:8788/__test/reset", {
    data: { scenario: "normal" },
  });
});
async function start(page) {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Start investigation", exact: true })
    .click();
  await page.getByLabel("Execution mode").selectOption("fixture");
  await page
    .getByRole("button", { name: "Start API run", exact: true })
    .click();
}
test("fixture evidence, task selection, policy and incomplete result", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByText("Fixture walkthrough", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".task-node")).toHaveCount(3);
  await expect(page.locator(".selected-label")).toContainText("attack-1a");
  await expect(page.locator(".verification-note")).toContainText(
    "have not run",
  );
  await expect(page.locator(".metric-verdict")).toHaveText("Incomplete");
  await page.locator(".task-node").first().click();
  await expect(
    page.getByText("No tool receipts for this task yet."),
  ).toBeVisible();
  await page.getByLabel("All tasks").check();
  await expect(page.locator(".receipt")).toHaveCount(2);
  await page.getByRole("tab", { name: "Policy patch" }).click();
  await expect(page.locator(".evidence-body .json")).toContainText(
    "reject_client_price",
  );
  await page.getByRole("tab", { name: "Event stream" }).click();
  await expect(page.locator(".events li")).toHaveCount(15);
});
test("API request, real HTTP SSE, deduplication and refresh recovery", async ({
  page,
  request,
}) => {
  await start(page);
  await expect(page.locator(".run-identity")).toContainText("http-fixture-1");
  await expect(page.locator(".run-identity")).toContainText("blocked");
  await expect(page.locator(".task-node")).toHaveCount(3);
  await page.getByRole("tab", { name: "Event stream" }).click();
  await expect(page.locator(".events li")).toHaveCount(4);
  await page.locator(".events li").last().locator("summary").click();
  await expect(page.locator(".events")).toContainText("budget_exhausted");
  const response = await request.get("http://127.0.0.1:8788/__test/request");
  expect(await response.json()).toMatchObject({
    mode: "fixture",
    target: "shop-demo",
    seed: 42,
    budget: {
      max_model_calls: 24,
      max_tool_calls: 64,
      max_depth: 2,
      max_concurrency: 4,
      deadline_seconds: 180,
    },
  });
  await page.reload();
  await expect(page.locator(".run-identity")).toContainText("blocked");
  await expect(page.locator(".task-node")).toHaveCount(3);
  await expect(page.locator(".connection")).toHaveText("Snapshot restored");
});
test("provider failure remains an error without a fake API run", async ({
  page,
  request,
}) => {
  await request.post("http://127.0.0.1:8788/__test/reset", {
    data: { scenario: "missing" },
  });
  await start(page);
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.locator(".modal-error")).toContainText("API 503");
  await expect(page.locator(".run-identity")).toContainText("fixture-run-1");
});
test("sequence gap pauses stream", async ({ page, request }) => {
  await request.post("http://127.0.0.1:8788/__test/reset", {
    data: { scenario: "gap" },
  });
  await start(page);
  await expect(page.getByRole("alert")).toContainText(
    "Missing event sequence 1",
  );
  await expect(page.locator(".task-node")).toHaveCount(1);
});
test("timeout remains visible with its cause", async ({ page, request }) => {
  await request.post("http://127.0.0.1:8788/__test/reset", {
    data: { scenario: "timeout" },
  });
  await start(page);
  await expect(page.locator(".run-identity")).toContainText("failed");
  await page.getByRole("tab", { name: "Event stream" }).click();
  await page.locator(".events li").last().locator("summary").click();
  await expect(page.locator(".events")).toContainText("deadline_exceeded");
});
test("cancellation waits for server confirmation", async ({
  page,
  request,
}) => {
  await request.post("http://127.0.0.1:8788/__test/reset", {
    data: { scenario: "running" },
  });
  await start(page);
  await expect(page.getByRole("button", { name: "Cancel run" })).toBeVisible();
  await page.getByRole("button", { name: "Cancel run" }).click();
  await expect(page.locator(".run-identity")).toContainText("canceled");
  await expect(page.getByRole("button", { name: "Cancel run" })).toHaveCount(0);
});
test("mobile fits the viewport and retains evaluation evidence", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await expect(
    page.getByRole("heading", { name: "Investigation tree" }),
  ).toBeVisible();
  await page
    .getByRole("heading", { name: "Repair verification" })
    .scrollIntoViewIfNeeded();
  await expect(page.locator(".verification-note")).toBeVisible();
});

test("active disconnect restores snapshot and resumes after last sequence", async ({
  page,
  request,
}) => {
  await request.post("http://127.0.0.1:8788/__test/reset", {
    data: { scenario: "disconnect" },
  });
  await start(page);
  await expect(page.locator(".connection")).toHaveText("Disconnected");
  await expect(page.getByRole("alert")).toContainText(
    "Event stream disconnected",
  );
  const resumed = page.waitForRequest((r) =>
    r.url().includes("/events?after_seq=3"),
  );
  await page.getByRole("button", { name: "Reconnect", exact: true }).click();
  await resumed;
  await expect(page.locator(".run-identity")).toContainText("blocked");
  await expect(page.locator(".task-node")).toHaveCount(3);
  await page.getByRole("tab", { name: "Event stream" }).click();
  await expect(page.locator(".events li")).toHaveCount(4);
});
test("dialog supports keyboard dismissal and restores focus", async ({
  page,
}) => {
  await page.goto("/");
  const trigger = page.getByRole("button", {
    name: "Start investigation",
    exact: true,
  });
  await trigger.click();
  await expect(page.getByLabel("Investigation goal")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(trigger).toBeFocused();
});


test("rejected and revised candidates persist without claiming final success", async ({ page, request }) => {
  await request.post("http://127.0.0.1:8788/__test/reset", {data: {scenario: "revision"}});
  await start(page);
  const history = page.getByLabel("Repair attempt history");
  await expect(history).toContainText("Candidate 1 · Rejected");
  await expect(history).toContainText("Candidate 2 · Public checks passed");
  await expect(history).toContainText("Normal purchases: 0/2");
  await expect(history).toContainText("Normal purchases: 2/2");
  await expect(page.locator(".metric-verdict")).not.toHaveText("Verified");
  await page.reload();
  await expect(history.locator(".repair-attempt")).toHaveCount(2);
  await expect(page.locator(".comparison").last()).toContainText("candidate-two");
  await expect(page.locator(".comparison").last()).toContainText("$500.00");
});


test("live recovery drill is explicitly labeled in request and persisted UI", async ({ page, request }) => {
  await page.goto("/");
  await page.getByRole("button", {name: "Start investigation", exact: true}).click();
  await page.getByLabel("Execution mode").selectOption("live");
  await page.getByLabel("Run scenario").selectOption("recovery_drill");
  await expect(page.locator(".modal-note").first()).toContainText("deliberately seeded");
  await page.getByRole("button", {name: "Start API run", exact: true}).click();
  await expect(page.getByRole("note")).toContainText("Recovery drill · seeded bad policy");
  const sent = await (await request.get("http://127.0.0.1:8788/__test/request")).json();
  expect(sent).toMatchObject({mode: "live", scenario: "recovery_drill", budget: {max_model_calls:24,max_concurrency:1}});
  await page.reload();
  await expect(page.getByRole("note")).toContainText("deliberately supplied");
});
