import { expect, test } from "@playwright/test";

test("shows backend health status", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle("ASTRA");
  await expect(page.getByRole("heading", { name: "ASTRA" })).toBeVisible();
  await expect(page.getByText("Backend")).toBeVisible();
  await expect(page.getByText("ok")).toBeVisible();
  await expect(page.getByText("Service: astra")).toBeVisible();
});

