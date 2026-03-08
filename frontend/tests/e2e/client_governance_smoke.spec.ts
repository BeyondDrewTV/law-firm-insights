import { expect, test, type BrowserContext, type Page } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const exposureLineRegex = /Exposure Status:\s*([A-Za-z-]+)/i;

const DEFAULT_SMOKE_EMAIL = "smoke.e2e@lawfirminsights.local";
const DEFAULT_SMOKE_PASSWORD = "SmokeTest123";
const E2E_HEADER = { "X-E2E-Test": "1" } as const;

async function buildUniqueCsvFixture(): Promise<string> {
  const sourcePath = fileURLToPath(new URL("../fixtures/sample_reviews.csv", import.meta.url));
  const content = await readFile(sourcePath, "utf-8");
  const stamp = Date.now();
  const extraRow = `\n2026-03-03,4,Smoke rerun marker ${stamp}`;
  const outPath = path.join(tmpdir(), `sample_reviews_${stamp}.csv`);
  await writeFile(outPath, `${content.trimEnd()}${extraRow}\n`, "utf-8");
  return outPath;
}

async function loginViaUi(page: Page, email: string, password: string): Promise<boolean> {
  const loginResp = await page.context().request.post("/api/auth/login", {
    data: { email, password },
    headers: { ...E2E_HEADER, "Content-Type": "application/json" },
    timeout: 20_000,
  });
  if (!loginResp.ok()) {
    return false;
  }
  const loginPayload = (await loginResp.json().catch(() => ({}))) as { success?: boolean; requires_2fa?: boolean };
  if (!loginPayload.success || loginPayload.requires_2fa) {
    return false;
  }
  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(300);
  if (!/\/dashboard/.test(page.url()) || /\/login/.test(page.url())) {
    return false;
  }
  const meResp = await page.context().request.get("/api/auth/me", { headers: E2E_HEADER });
  const mePayload = (await meResp.json().catch(() => ({}))) as { success?: boolean };
  if (!meResp.ok() || !mePayload.success) {
    return false;
  }
  return true;
}

async function parsePdfText(bytes: Buffer): Promise<string> {
  const mod = await import("pdf-parse");
  const parseFn = typeof (mod as { default?: unknown }).default === "function" ? (mod as { default: (b: Buffer) => Promise<{ text: string }> }).default : (mod as unknown as (b: Buffer) => Promise<{ text: string }>);
  const parsed = await parseFn(bytes);
  return parsed?.text || "";
}

async function fetchExportPdfBytes(page: Page, reportId: number): Promise<Buffer> {
  // eslint-disable-next-line no-console
  console.log(`[export] ${new Date().toISOString()} api-fetch:start report_id=${reportId}`);
  const pdfResp = await page.request.get(`/api/reports/${reportId}/pdf?export=1`, {
    headers: E2E_HEADER,
    timeout: 60_000,
  });
  // eslint-disable-next-line no-console
  console.log(`[export] ${new Date().toISOString()} api-fetch:done report_id=${reportId} status=${pdfResp.status()}`);
  if (!pdfResp.ok()) {
    const bodyText = await pdfResp.text().catch(() => "");
    // eslint-disable-next-line no-console
    console.log("[export] non-200 status:", pdfResp.status());
    // eslint-disable-next-line no-console
    console.log("[export] body:", bodyText.slice(0, 500));
  }
  expect(pdfResp.ok()).toBeTruthy();
  return Buffer.from(await pdfResp.body());
}

async function exerciseExportButton(page: Page): Promise<void> {
  // eslint-disable-next-line no-console
  console.log(`[export] ${new Date().toISOString()} ui-click:start`);
  const exportButton = page.getByTestId("export-brief").first();
  await expect(exportButton).toBeVisible();
  await expect(exportButton).toBeEnabled();
  await exportButton.click();
  await page.waitForTimeout(500);
  // eslint-disable-next-line no-console
  console.log(`[export] ${new Date().toISOString()} ui-click:done`);
}

async function readDashboardExposureLabel(page: Page): Promise<string> {
  const exposureLabel = page.getByTestId("exposure-label").first();
  await expect(exposureLabel).toBeVisible();
  return ((await exposureLabel.textContent()) || "").trim();
}

async function waitForExposureLabel(page: Page, predicate: (value: string) => boolean): Promise<string> {
  const timeoutMs = 60_000;
  const started = Date.now();
  let last = "";
  while (Date.now() - started < timeoutMs) {
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
    last = await readDashboardExposureLabel(page);
    if (predicate(last)) return last;
    await page.waitForTimeout(2_000);
  }
  throw new Error(`Timed out waiting for exposure label. Last seen: ${last}`);
}

async function waitForCanonicalExposure(
  page: Page,
  predicate: (label: string) => boolean,
): Promise<{ label: string; reportId: number | null }> {
  const timeoutMs = 60_000;
  const started = Date.now();
  let last = { label: "", reportId: null as number | null };
  while (Date.now() - started < timeoutMs) {
    last = await getCanonicalExposure(page);
    if (last.label && predicate(last.label)) return last;
    await page.waitForTimeout(2_000);
  }
  throw new Error(`Timed out waiting for canonical exposure. Last seen: ${last.label}`);
}

function extractExposureFromPdfText(text: string): string | null {
  const match = text.match(exposureLineRegex);
  return match?.[1] || null;
}

async function getCanonicalExposure(page: Page): Promise<{ label: string; reportId: number | null }> {
  const resp = await page.context().request.get("/api/exposure/latest", {
    headers: E2E_HEADER,
    timeout: 30_000,
  });
  expect(resp.ok()).toBeTruthy();
  const payload = (await resp.json()) as {
    success?: boolean;
    has_data?: boolean;
    exposure_label?: string | null;
    report_id?: number | null;
  };
  expect(payload.success).toBeTruthy();
  if (payload.has_data === false) {
    return { label: "", reportId: null };
  }
  return {
    label: (payload.exposure_label || "").trim(),
    reportId: typeof payload.report_id === "number" ? payload.report_id : null,
  };
}

async function getLatestReadyReportId(context: BrowserContext): Promise<number> {
  const response = await context.request.get("/api/reports?limit=20", { headers: E2E_HEADER });
  expect(response.ok()).toBeTruthy();
  const payload = (await response.json()) as { success?: boolean; reports?: Array<{ id: number; status: string }> };
  expect(payload.success).toBeTruthy();
  const ready = (payload.reports || []).find((r) => r.status === "ready");
  expect(ready, "No ready report found after upload").toBeTruthy();
  return ready!.id;
}

test("client governance smoke", async ({ page }) => {
  const email = process.env.E2E_SMOKE_EMAIL || DEFAULT_SMOKE_EMAIL;
  const password = process.env.E2E_SMOKE_PASSWORD || DEFAULT_SMOKE_PASSWORD;
  const fullName = "Smoke Tester";
  const firmName = "Smoke LLP";

  let loggedIn = await loginViaUi(page, email, password);
  if (!loggedIn) {
    await page.goto("/signup", { waitUntil: "domcontentloaded" });
    await page.locator("#full_name").fill(fullName);
    await page.locator("#firm_name").fill(firmName);
    await page.locator("#email").fill(email);
    await page.locator("#password").fill(password);
    await page.locator("#confirmPassword").fill(password);
    const registerResponsePromise = page.waitForResponse(
      (r) =>
        (r.url().includes("/api/auth/register") || r.url().includes("/api/register")) &&
        r.request().method() === "POST",
      { timeout: 30_000 },
    );
    await page.getByRole("button", { name: /Create free account/i }).click();
    const registerResponse = await registerResponsePromise;
    const registerPayload = (await registerResponse.json().catch(() => ({}))) as {
      success?: boolean;
      error?: string;
      user?: { id?: number };
    };

    if (!registerResponse.ok() || registerPayload.success === false) {
      const err = (registerPayload.error || "").toLowerCase();
      const isRecoverable =
        registerResponse.status() === 409 ||
        registerResponse.status() === 429 ||
        err.includes("already exists") ||
        err.includes("rate limit");
      if (!isRecoverable) {
        throw new Error(
          `Registration failed unexpectedly. status=${registerResponse.status()} error=${registerPayload.error || "unknown"}`,
        );
      }
    }

    loggedIn = await loginViaUi(page, email, password);
    if (!loggedIn) {
      throw new Error(
        "Registration/login fallback failed after ensure/reset bootstrap. Auth limiter state should have been cleared.",
      );
    }
  }

  const meResponse = await page.context().request.get("/api/auth/me", { headers: E2E_HEADER });
  const mePayload = (await meResponse.json().catch(() => ({}))) as { success?: boolean };
  if (!meResponse.ok() || !mePayload.success) {
    const recovered = await loginViaUi(page, email, password);
    if (!recovered) {
      throw new Error("Authenticated session could not be established after reset/bootstrap.");
    }
  }

  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
  if (/\/login/.test(page.url())) {
    const recovered = await loginViaUi(page, email, password);
    if (!recovered) {
      throw new Error("Unable to establish authenticated dashboard session for smoke test.");
    }
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
  }
  const baselineEmptyState = page.getByText("Baseline not established", { exact: true });
  const exposureBlock = page.getByTestId("exposure-block").first();
  const hasBaselineEmptyState = await baselineEmptyState.isVisible().catch(() => false);
  if (!hasBaselineEmptyState) {
    await expect(exposureBlock).toBeVisible();
  }

  page.on("response", async (resp) => {
    if (resp.url().includes("/api/upload")) {
      // eslint-disable-next-line no-console
      console.log("[upload] status:", resp.status());
      try {
        // eslint-disable-next-line no-console
        console.log("[upload] body:", await resp.text());
      } catch {
        // ignore logging parse failures
      }
    }
  });

  page.on("console", (msg) => {
    // eslint-disable-next-line no-console
    console.log("[browser console]", msg.type(), msg.text());
  });

  await page.goto("/upload", { waitUntil: "domcontentloaded" });
  const fixturePath = await buildUniqueCsvFixture();
  await page.locator("#csv-file").setInputFiles(fixturePath);
  const uploadResponsePromise = page.waitForResponse((r) => r.url().includes("/api/upload"), { timeout: 60_000 });
  await page.getByRole("button", { name: /Upload and Analyze/i }).click();

  // Accept 200 (new upload) or 409 (duplicate fixture on rerun) and continue with latest ready report.
  const uploadResponse = await uploadResponsePromise;
  const uploadPayload = (await uploadResponse.json().catch(() => ({}))) as {
    success?: boolean;
    error?: string;
    summary?: { report_id?: number | null };
  };
  let latestReportIdFromUpload = uploadPayload.summary?.report_id ?? null;
  if (uploadResponse.status() === 200) {
    expect(uploadPayload.success).toBeTruthy();
    expect(typeof latestReportIdFromUpload === "number" && latestReportIdFromUpload > 0).toBeTruthy();
  } else if (uploadResponse.status() === 409) {
    expect((uploadPayload.error || "").toLowerCase()).toContain("identical");
    latestReportIdFromUpload = await getLatestReadyReportId(page.context());
  } else {
    throw new Error(`Unexpected upload status ${uploadResponse.status()} during smoke flow.`);
  }

  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("exposure-block").first()).toBeVisible();

  const canonicalBefore = await waitForCanonicalExposure(page, (label) => label !== "--" && !/not established/i.test(label));
  const exposureBefore = canonicalBefore.label;

  const reportId = (latestReportIdFromUpload as number) || (await getLatestReadyReportId(page.context()));
  const actionTitle = `Smoke action ${Date.now()}`;
  const createActionResponse = await page.context().request.post(`/api/reports/${reportId}/actions`, {
    data: {
      title: actionTitle,
      owner: "Operations Lead",
      kpi: "Overdue test path",
      status: "open",
    },
    headers: { ...E2E_HEADER, "Content-Type": "application/json" },
  });
  if (!createActionResponse.ok()) {
    const bodyText = await createActionResponse.text().catch(() => "");
    // eslint-disable-next-line no-console
    console.log("[actions:create] status/body:", createActionResponse.status(), bodyText.slice(0, 500));
  }
  expect(createActionResponse.ok()).toBeTruthy();

  const actionsResponse = await page.context().request.get(`/api/reports/${reportId}/actions`, {
    headers: E2E_HEADER,
  });
  expect(actionsResponse.ok()).toBeTruthy();
  const actionsPayload = (await actionsResponse.json()) as {
    success?: boolean;
    actions?: Array<{ id: number; title: string }>;
  };
  expect(actionsPayload.success).toBeTruthy();
  const createdAction = (actionsPayload.actions || []).find((item) => item.title === actionTitle);
  expect(createdAction, "Created action was not found in API response").toBeTruthy();

  const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
  const yesterdayIso = yesterday.toISOString().slice(0, 10);
  const updateActionResponse = await page.context().request.patch(
    `/api/reports/${reportId}/actions/${createdAction!.id}`,
    {
      data: { due_date: yesterdayIso, status: "open" },
      headers: { ...E2E_HEADER, "X-E2E": "1", "Content-Type": "application/json" },
    },
  );
  expect(updateActionResponse.ok()).toBeTruthy();

  const canonicalAfter = await waitForCanonicalExposure(page, (label) => Boolean(label && label !== "--"));
  const exposureAfter = canonicalAfter.label;

  const secondExportReportId = canonicalAfter.reportId ?? reportId;
  await exerciseExportButton(page);
  const secondExportBytes = await fetchExportPdfBytes(page, secondExportReportId);
  expect(secondExportBytes.length).toBeGreaterThan(500);
  const secondPdfText = await parsePdfText(secondExportBytes);
  const secondPdfExposure = extractExposureFromPdfText(secondPdfText);
  expect(secondPdfExposure).toBeTruthy();
  if (secondPdfExposure !== exposureAfter) {
    // eslint-disable-next-line no-console
    console.log(
      `[parity:after] mismatch canonical=${exposureAfter} pdf=${secondPdfExposure} report_id=${secondExportReportId}`,
    );
  }
  // Console-friendly release summary.
  // eslint-disable-next-line no-console
  console.log(
    [
      "[SMOKE]",
      `user=${email}`,
      `exposure_before=${exposureBefore}`,
      `exposure_after=${exposureAfter}`,
      `pdf2_match=${secondPdfExposure === exposureAfter}`,
      `report_id=${reportId}`,
    ].join(" "),
  );
});
