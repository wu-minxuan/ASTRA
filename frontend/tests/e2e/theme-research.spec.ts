import { expect, Page, test } from "@playwright/test";

const successPayload = {
  contract_version: "phase1.v1",
  request: {
    theme: "低空经济",
    normalized_query: "低空经济",
    market: "cn_a",
    max_results: 3,
    include_report: true,
  },
  result: {
    as_of: "2026-06-30",
    pool: [
      {
        symbol: "300001.SZ",
        name: "真实低空一号",
        exchange: "SZSE",
        industry: "航空装备",
        concepts: ["低空经济", "飞行汽车"],
        recall_sources: ["真实概念板块成分命中：低空经济"],
        evidence: [
          {
            id: "evidence-300001-concept",
            kind: "concept",
            stance: "fact",
            summary: "候选公司出现在 AKShare 低空经济概念板块成分中。",
            source_name: "akshare:stock_board_concept_cons_em",
            source_type: "market_data_provider",
            confidence: "medium",
          },
          {
            id: "evidence-300001-business",
            kind: "business_summary",
            stance: "fact",
            summary: "主营业务包含低空飞行器核心部件和系统集成。",
            source_name: "akshare:stock_zyjs_ths",
            source_type: "market_data_provider",
            confidence: "medium",
          },
        ],
        scores: {
          recall_score: 70,
          coarse_score: 76,
          final_score: 72.3,
        },
        rank: 1,
        selection_reason: "精排结论：证据链、召回依据和粗排分共同支持该候选排序。",
        key_risks: ["真实 AKShare 证据覆盖有限，需要人工复核。"],
      },
      {
        symbol: "600001.SH",
        name: "真实低空二号",
        exchange: "SSE",
        industry: "通用设备",
        concepts: ["低空经济"],
        recall_sources: ["真实概念板块成分命中：低空经济"],
        evidence: [
          {
            id: "evidence-600001-concept",
            kind: "concept",
            stance: "fact",
            summary: "候选公司出现在 AKShare 低空经济概念板块成分中。",
            source_name: "akshare:stock_board_concept_cons_em",
            source_type: "market_data_provider",
            confidence: "medium",
          },
        ],
        scores: {
          recall_score: 70,
          coarse_score: 70,
          final_score: 68.5,
        },
        rank: 2,
        selection_reason: "精排结论：候选与主题存在结构化概念关系。",
        key_risks: ["财务和文本证据覆盖有限。"],
      },
    ],
    report: {
      title: "低空经济主题股票池研究报告",
      summary: "基于 2 个候选的召回、证据补全和模型排序结果生成。",
      theme_overview: "低空经济主题关系来自 AKShare 概念板块成分和结构化证据包。",
      pool_summary: "股票池按精排分数和稳定排序规则生成，后续仍需人工复核。",
      focus_companies: [
        {
          symbol: "300001.SZ",
          name: "真实低空一号",
          reason: "精排结论：证据链、召回依据和粗排分共同支持该候选排序。",
          supporting_evidence_ids: ["evidence-300001-concept"],
          risks: ["真实 AKShare 证据覆盖有限，需要人工复核。"],
        },
      ],
      risks: ["证据覆盖、数据时点和模型判断均存在不确定性。"],
      data_boundary: "候选召回来自 AKShare cached snapshot；模型排序仍使用 fake model。",
      not_investment_advice: "本报告仅用于研究流程验证，不构成任何交易建议。",
    },
    pipeline: [
      {
        stage: "candidate_recall",
        input_count: 1,
        output_count: 2,
        notes: ["concept_queries=低空经济"],
      },
      {
        stage: "evidence_enrichment",
        input_count: 2,
        output_count: 2,
        notes: ["web knowledge provider was not used"],
      },
      {
        stage: "coarse_rank",
        input_count: 2,
        output_count: 2,
        notes: ["model_spec=fake:fake-coarse-ranker-v1"],
      },
      {
        stage: "deep_rank",
        input_count: 2,
        output_count: 2,
        notes: ["model_spec=fake:fake-deep-ranker-v1"],
      },
      {
        stage: "report_generation",
        input_count: 2,
        output_count: 1,
        notes: ["model_spec=fake:fake-report-generator-v1"],
      },
    ],
    data_boundary: [
      "Candidate evidence uses akshare cached market metadata snapshot from market_metadata_cache:stock_board_concept_cons_em:BK1166; retrieved_at=2026-06-30T00:00:00+08:00; live_failure=RemoteDisconnected.",
      "P1-O03 E2E uses a mocked HTTP response and does not access live AKShare.",
    ],
    warnings: ["模型排序仍使用 fake model client。"],
  },
};

const providerErrorPayload = {
  contract_version: "phase1.v1",
  error: {
    code: "provider_unavailable",
    message: "AKShare 候选召回接口不可用，无法为主题 `低空经济` 生成真实股票池。",
    details: {
      provider: "akshare",
      stage: "candidate_recall",
      normalized_query: "低空经济",
      error_message:
        "concept board discovery unavailable: AKShare call failed: stock_board_concept_name_em: RemoteDisconnected",
      warnings: [
        "concept board discovery unavailable: AKShare call failed: stock_board_concept_name_em: RemoteDisconnected",
      ],
    },
  },
};

test("runs theme research and shows pool plus report", async ({ page }) => {
  await mockThemeResearchSuccess(page);
  await page.goto("/");

  await expect(page).toHaveTitle("ASTRA");
  await expect(page.getByRole("heading", { name: "ASTRA" })).toBeVisible();
  await expect(page.getByText("Backend")).toBeVisible();
  await expect(page.getByText("ok")).toBeVisible();
  await expect(page.getByText("Market data")).toBeVisible();
  await expect(page.getByText("Fake model")).toBeVisible();

  await page.getByRole("textbox", { name: "主题" }).fill("低空经济");
  await page.getByRole("spinbutton", { name: "结果数" }).fill("3");
  await page.getByRole("button", { name: "运行研究" }).click();

  await expect(page.getByRole("heading", { name: "股票池", exact: true })).toBeVisible();
  await expect(page.getByText("AKShare cached")).toBeVisible();
  await expect(page.getByRole("row", { name: /真实低空一号/ })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "低空经济主题股票池研究报告" }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "流程" }).click();
  await expect(page.getByText("report_generation")).toBeVisible();
  await page.getByRole("tab", { name: "证据" }).click();
  await expect(page.getByText("akshare:stock_board_concept_cons_em")).toBeVisible();
});

test("shows provider error details when AKShare is unavailable", async ({ page }) => {
  await mockThemeResearchProviderError(page);
  await page.goto("/");

  await page.getByRole("textbox", { name: "主题" }).fill("低空经济");
  await page.getByRole("button", { name: "运行研究" }).click();

  await expect(page.getByRole("alert")).toContainText("provider_unavailable");
  await expect(page.getByRole("alert")).toContainText("AKShare 候选召回接口不可用");
  await expect(page.getByRole("alert")).toContainText("stock_board_concept_name_em");
  await expect(page.getByRole("alert")).toContainText("RemoteDisconnected");
});

async function mockThemeResearchSuccess(page: Page) {
  await page.route("**/api/theme-research", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(successPayload),
    });
  });
}

async function mockThemeResearchProviderError(page: Page) {
  await page.route("**/api/theme-research", async (route) => {
    await route.fulfill({
      status: 502,
      contentType: "application/json",
      body: JSON.stringify(providerErrorPayload),
    });
  });
}
