import { test, expect } from "@playwright/test";

test("Open examples page and click to a new example", async ({ page }) => {
  // Go to http://localhost:3000/examples/
  await page.goto("http://localhost:3000/examples/");
  // Click text=App with plot
  await page.locator("text=App with plot").click();
  await expect(page).toHaveURL("http://localhost:3000/examples/#app-with-plot");
});

test("Add a new non-app script, type in it, and run code", async ({ page }) => {
  await page.goto("http://localhost:3000/examples/");

  // Wait for initialization to complete
  await page.waitForSelector(`text=">>>"`, { timeout: 10000 });
  await page.locator(`[aria-label="Add a file"]`).click();
  await page.locator('[aria-label="Name current file"]').fill("my_app.py");

  await page.locator(".cm-editor [role=textbox]").type(`print("hello world")`);

  await page.locator(".cm-editor [role=textbox]").press(`Meta+Enter`);

  // Make sure that hello world exists in the terminal output
  await page.locator(`text=hello world >> nth=2`);
});