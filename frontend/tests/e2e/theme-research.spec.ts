import { expect, test } from "@playwright/test";

test("runs theme research and shows pool plus report", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle("ASTRA");
  await expect(page.getByRole("heading", { name: "ASTRA" })).toBeVisible();
  await expect(page.getByText("Backend")).toBeVisible();
  await expect(page.getByText("ok")).toBeVisible();

  await page.getByRole("textbox", { name: "主题" }).fill("低空经济");
  await page.getByRole("spinbutton", { name: "结果数" }).fill("3");
  await page.getByRole("button", { name: "运行研究" }).click();

  await expect(page.getByRole("heading", { name: "股票池", exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "低空样例一号", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "低空经济主题股票池研究报告" }),
  ).toBeVisible();
  await expect(page.getByText("report_generation")).toBeVisible();
  await expect(page.getByText("本报告仅用于研究流程验证")).toBeVisible();
});

test("shows structured error state for an unmatched theme", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("textbox", { name: "主题" }).fill("完全不存在的主题");
  await page.getByRole("button", { name: "运行研究" }).click();

  await expect(page.getByRole("alert")).toContainText("no_candidates");
  await expect(page.getByRole("alert")).toContainText("未找到");
});
