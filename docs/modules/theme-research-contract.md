# 主题研究合同与样例数据规格

本文档定义 Phase 1 Theme-to-Pool Research Funnel 的最小研究合同、固定样例数据规格和真实数据源接入边界。它是 P1-T02 到 P1-T14 的实现依据。

## 状态

- 阶段：Phase 1
- 合同版本：`phase1.v1`
- 首个样例主题：`低空经济`
- 数据模式：固定样例数据保证可复现；Phase 1 必须实现真实股票数据 API 的最小接入

## 职责

本规格负责定义：

- 主题研究请求的输入合同。
- 主题研究结果的输出合同。
- 候选股票、证据项、评分结果、研究报告和流程追踪的数据结构。
- 固定样例数据的文件边界、字段要求和验收口径。
- Phase 1 各后续任务共享的错误形态与验证目标。

## 非职责

本规格不负责：

- 实现完整行情、完整财务、公告、研报、新闻或生产级概念数据源接入。
- 定义生产级数据库、数据仓库或特征平台。
- 生成买入、卖出、持仓、目标价或交易时机建议。
- 评估真实股票投资价值。
- 定义复杂 Agent 调度框架。
- 取代 P1-T04 真实股票数据 API 选型与数据源规格。

## 研究边界

Phase 1 输出是研究辅助材料，不是投资建议。

实现必须遵守以下边界：

- 输出必须区分事实、推断和假设。
- 输出必须说明数据来源、时间点和样例数据边界。
- 输出不得包含确定性买入、卖出、持仓、目标价或交易指令。
- 固定样例数据只用于验证流程可复现，不代表实时市场事实。
- 引入或扩展真实数据时，必须记录数据来源、字段、更新时间、许可边界、失败处理方式和测试替代数据。

## Fixture 与真实数据源边界

固定样例数据是 Phase 1 的测试输入和显式测试替代数据，不是真实股票数据 API 的标准模型，也不是正常 Web/API 主路径的静默 fallback。

实现必须遵守以下分层：

- `FixtureThemeDataset` 和 `FixtureCompany` 只表示固定样例数据格式。
- `CandidateStock`、`EvidenceItem`、`ResearchReport` 等模型表示 ASTRA 内部研究合同。
- Phase 1 接入真实数据源时，应新增数据源原始模型，例如 `StockSourceRecord`、`ConceptConstituentRecord` 或 provider-specific DTO。
- 真实数据源原始模型必须通过 adapter 或 mapper 转换为 ASTRA 内部研究合同。
- 召回、证据补全、排序和报告模块不应直接依赖某个外部 API 的原始字段名或响应结构。

当前 fixture 中的以下字段是样例便利字段，不应被视为真实数据源必备字段：

- `recall_keywords`：fixture-only 召回辅助字段。真实接入时应由概念标签、行业分类、公司简介、公告、新闻、研报等材料派生。
- `business_summary`、`financial_summary`、`text_summary`：fixture 中的预整理摘要。真实接入时应由原始公司资料、财务字段和文本材料经证据补全模块生成。
- `concepts`：样例概念标签。真实接入时必须保留概念体系来源和更新时间，不能假设不同供应商标签语义一致。
- `evidence`：fixture 中的已整理证据项。真实接入时更可能先获得原始资料，再映射或生成 `EvidenceItem`。

Phase 1 引入真实数据源前必须补充数据源规格或 ADR，至少说明：

- 数据提供方和许可边界。
- 原始字段与内部研究合同的映射关系。
- 概念、行业和文本材料的来源体系。
- 更新时间、失败处理方式和测试替代数据。
- 如何避免为了适配某个供应商而污染核心研究模型。

Phase 1 的首个真实市场数据 provider 选型见 `docs/adr/0002-use-akshare-as-phase-1-market-data-provider.md`。
网页与网络知识搜索 provider 边界见 `docs/adr/0003-separate-web-knowledge-provider.md`。

## Phase 1 真实股票数据 API 最小接入

真实股票数据 API 接入是 Phase 1 的必做项，不后置到 Phase 2。

Phase 1 最小接入目标：

- 选定一个主要数据源，用于 A 股股票基础信息和主题、概念、板块或行业成分数据。
- 记录候选数据源比较、选择理由、许可边界和字段可用性。
- 实现一个 adapter，将外部 API 原始记录转换为 ASTRA 内部研究合同或候选召回输入。
- 在外部 API 不可用、限流、缺字段或测试环境无网络时，正常 Web/API 返回结构化 provider 错误。
- 自动化测试默认依赖 fixture、fake provider 或 mocked HTTP response，不依赖真实网络请求。
- 对变化频率低但上游发现接口不稳定的市场元数据，可以维护真实来源的只读本地快照；使用该快照时必须保留 provider、接口、获取时间、失败原因和缓存标识，不能伪装成实时 live 数据。

最小字段需求：

| 数据能力 | 最小字段 | 用途 |
| --- | --- | --- |
| 股票基础信息 | 股票代码、名称、交易所、上市状态、行业分类中的可得字段 | 展示、过滤和候选记录规范化 |
| 主题/概念成分 | 主题或概念名称、成分股代码、成分股名称、数据更新时间中的可得字段 | 将用户主题映射到候选公司 |
| 数据源元信息 | 数据源名称、更新时间、许可边界、失败原因 | 证据边界和失败说明 |

候选数据源应在 Phase 1 内比较并选择，初始候选包括：

- AkShare：Phase 1 首个真实市场数据 provider，用于快速原型和公开数据探索；需通过 adapter 接入，并明确字段稳定性与使用边界。
- Tushare：结构化能力较强，需确认 token、积分、字段权限和许可边界。
- Baostock：基础证券信息较稳，但主题/概念成分能力可能不足。
- 东方财富或同花顺概念相关公开数据：主题召回价值高，但必须谨慎评估接口稳定性、许可和使用边界。

Phase 1 不要求一次性接入完整行情、完整财务、公告、新闻或研报数据。它们可以作为证据补全质量提升项继续扩展，但不能阻塞真实候选召回的最小接入。

## 漏斗阶段

Phase 1 的最小研究流程保持以下阶段名称。后续代码、日志、测试和 API 输出应优先复用这些名称。

```text
theme_parse
candidate_recall
evidence_enrichment
coarse_rank
deep_rank
report_generation
```

各阶段最小职责：

- `theme_parse`：清洗用户输入，生成规范化查询和别名匹配信息。
- `candidate_recall`：从固定样例数据或真实数据源 adapter 中召回候选 A 股公司。
- `evidence_enrichment`：合并候选公司的概念、行业、业务、财务、文本摘要和风险证据。
- `coarse_rank`：通过低成本模型规格生成初筛分数、保留/过滤判断和过滤理由。
- `deep_rank`：通过更高质量模型规格生成最终排序、入选理由、关键证据、主要风险和不确定性。
- `report_generation`：基于结构化证据、粗排结果和精排结果生成研究报告摘要和边界说明。

## 模型调用边界

Phase 1 的粗排和精排必须接模型。召回阶段可以使用规则和数据源标签完成低成本候选覆盖，但不能把 Theme-to-Pool 降级为单纯召回工具。

模型接入必须通过统一 model client interface，业务模块不得直接依赖具体模型供应商 SDK 或 HTTP 响应结构。

建议抽象：

```text
ModelClient
  -> generate_structured(request: ModelRequest, schema: ModelOutputSchema) -> ModelResponse
```

模型规格至少拆分为：

| 规格 | 目标 | 输入 | 输出 |
| --- | --- | --- | --- |
| `coarse_rank_model_spec` | 低成本初筛、评分和过滤 | 压缩候选摘要、主题、关键证据、召回来源 | 粗排分数、保留/过滤判断、理由、风险摘要 |
| `deep_rank_model_spec` | 高质量最终排序和解释 | 候选证据包、粗排结果、主题边界、数据边界 | 最终分数、排序理由、关键证据引用、主要风险、不确定性 |
| `report_generation_model_spec` | 生成结构化研究报告 | 精排结果、证据引用、风险和数据边界 | 报告摘要、重点公司解释、风险提示、非投资建议说明 |

模型输出必须满足：

- 使用结构化 JSON 或可校验对象。
- 能映射回 `ScoreBreakdown`、`CandidateStock`、`ResearchReport` 等内部合同。
- 引用证据时必须使用 `EvidenceItem.id` 或等价证据引用。
- 明确区分事实、推断和假设。
- 不包含买入、卖出、持仓、目标价、仓位建议或交易时机。

自动化测试要求：

- 单元测试和集成测试默认使用 fake/mock model client。
- fake/mock 输出必须固定，避免真实模型随机性破坏 CI。
- 必须测试结构化输出 schema 校验失败时的错误处理。
- 必须测试模型输出包含交易指令时会被拒绝或标记为非法。
- 真实模型调用只允许在显式授权或专门的手工验证任务中运行。

## 请求合同

### `ThemeResearchRequest`

```json
{
  "theme": "低空经济",
  "market": "cn_a",
  "max_results": 5,
  "include_report": true
}
```

字段要求：

| 字段 | 类型 | 必填 | 默认值 | 规则 |
| --- | --- | --- | --- | --- |
| `theme` | string | 是 | 无 | 去除首尾空白后不能为空；建议长度 2 到 40 个字符 |
| `market` | string | 否 | `cn_a` | Phase 1 仅支持 `cn_a` |
| `max_results` | integer | 否 | `5` | 最小 `1`，最大 `10` |
| `include_report` | boolean | 否 | `true` | 为 `false` 时仍返回股票池和流程追踪 |

输入归一化规则：

- `theme` 需要去除首尾空白。
- 空字符串或纯空白输入返回 `invalid_request`。
- Phase 1 不做复杂分词或语义扩展，别名匹配依赖固定样例数据。
- `market` 不是 `cn_a` 时返回 `unsupported_market`。
- `max_results` 超出范围时返回 `invalid_request`。

## 成功响应合同

### `ThemeResearchResponse`

```json
{
  "contract_version": "phase1.v1",
  "request": {
    "theme": "低空经济",
    "normalized_query": "低空经济",
    "market": "cn_a",
    "max_results": 5,
    "include_report": true
  },
  "result": {
    "as_of": "2026-06-15",
    "pool": [],
    "report": {},
    "pipeline": [],
    "data_boundary": [],
    "warnings": []
  }
}
```

顶层字段：

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `contract_version` | string | 固定为 `phase1.v1` |
| `request` | object | 回显规范化后的请求 |
| `result` | object | 研究结果主体 |

`result` 字段：

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `as_of` | string | 样例数据时间点，使用 `YYYY-MM-DD` |
| `pool` | array | 最终股票池，按 `rank` 升序排列 |
| `report` | object or null | `include_report=true` 时返回 |
| `pipeline` | array | 每个漏斗阶段的输入、输出和关键理由 |
| `data_boundary` | array | 数据来源、时间点、缺失项和样例限制说明 |
| `warnings` | array | 非阻塞风险或降级说明 |

## 核心数据结构

### `CandidateStock`

候选股票用于承载召回、证据、评分和最终解释。

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `symbol` | string | 是 | A 股代码，建议形如 `000000.SZ` 或 `600000.SH` |
| `name` | string | 是 | 公司简称 |
| `market` | string | 是 | Phase 1 固定为 `cn_a` |
| `exchange` | string | 是 | `SZSE` 或 `SSE` |
| `industry` | string | 是 | 行业或申万/中信等样例行业标签 |
| `concepts` | array | 是 | 概念标签，至少包含一个与主题相关的标签 |
| `recall_sources` | array | 是 | 召回来源说明 |
| `evidence` | array | 是 | 证据项列表 |
| `scores` | object | 是 | 评分拆解 |
| `rank` | integer or null | 是 | 最终入选后从 `1` 开始；未入选为 `null` |
| `selection_reason` | string | 是 | 入选或未入选理由 |
| `key_risks` | array | 是 | 主要风险 |

### `EvidenceItem`

证据项必须保留来源和性质，避免把推断包装成事实。

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `id` | string | 是 | 在样例数据内唯一 |
| `kind` | string | 是 | 见证据类型枚举 |
| `stance` | string | 是 | `fact`、`inference` 或 `assumption` |
| `summary` | string | 是 | 简短证据摘要 |
| `source_name` | string | 是 | 来源名称 |
| `source_type` | string | 是 | 见来源类型枚举 |
| `source_date` | string or null | 是 | `YYYY-MM-DD`；未知时为 `null` 并说明原因 |
| `source_url` | string or null | 是 | 样例数据可为 `null` |
| `confidence` | string | 是 | `low`、`medium` 或 `high` |

证据类型枚举：

```text
concept
industry
business_summary
financial_summary
text_summary
risk
theme_relationship
```

来源类型枚举：

```text
fixture
market_data_provider
manual_research_note
public_disclosure
news
research_report
```

Phase 1 当前已实现 `fixture` 与 `market_data_provider` 来源。网页、公告、新闻和研报等来源留给后续 evidence provider，并必须通过 `data_boundary` 说明来源边界。

### `ScoreBreakdown`

评分用于支持排序解释，不用于表达投资收益预期。

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `recall_score` | number | 是 | 召回相关性，范围 `0` 到 `100` |
| `coarse_score` | number | 是 | 粗排分数，范围 `0` 到 `100` |
| `final_score` | number | 是 | 精排最终分数，范围 `0` 到 `100` |
| `factors` | array | 是 | 分数因子说明 |

`factors` 子项：

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `name` | string | 是 | 因子名称 |
| `value` | number | 是 | 因子值或贡献分 |
| `reason` | string | 是 | 解释文本 |

排序规则：

- `final_score` 高者优先。
- `final_score` 相同则 `coarse_score` 高者优先。
- 仍相同则按 `symbol` 字典序升序，保证测试稳定。

### `ResearchReport`

研究报告是结构化结果，不是自然语言长文的唯一载体。

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `title` | string | 是 | 报告标题 |
| `summary` | string | 是 | 一段式摘要 |
| `theme_overview` | string | 是 | 主题概述 |
| `pool_summary` | string | 是 | 股票池汇总 |
| `focus_companies` | array | 是 | 重点公司解释 |
| `risks` | array | 是 | 主题和股票池层面的风险提示 |
| `data_boundary` | string | 是 | 数据边界说明 |
| `not_investment_advice` | string | 是 | 明确非投资建议 |

`focus_companies` 子项：

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `symbol` | string | 是 | 对应股票代码 |
| `name` | string | 是 | 对应公司简称 |
| `reason` | string | 是 | 入选解释 |
| `supporting_evidence_ids` | array | 是 | 引用的证据 ID |
| `risks` | array | 是 | 公司层面风险 |

### `PipelineStageTrace`

流程追踪用于复盘和测试。

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `stage` | string | 是 | 使用固定漏斗阶段名称 |
| `input_count` | integer | 是 | 阶段输入数量 |
| `output_count` | integer | 是 | 阶段输出数量 |
| `notes` | array | 是 | 关键规则、过滤或降级说明 |

## 错误响应合同

错误响应保持稳定，便于前端和测试使用。

```json
{
  "contract_version": "phase1.v1",
  "error": {
    "code": "invalid_request",
    "message": "theme must not be empty",
    "details": {}
  }
}
```

错误码：

| 错误码 | 触发条件 | HTTP 建议 |
| --- | --- | --- |
| `invalid_request` | 请求字段为空、类型错误或超出范围 | `400` |
| `unsupported_market` | `market` 不是 `cn_a` | `400` |
| `no_candidates` | 请求合法，且数据源可访问但无可召回候选 | `404` |
| `provider_unavailable` | 真实市场数据 provider 不可访问、断连、超时、函数缺失或概念板块发现失败 | `502` |
| `internal_error` | 未预期错误 | `500` |

`no_candidates` 不是系统失败。前端应展示可理解的无结果状态。
`provider_unavailable` 是上游数据源失败。前端应展示 provider、stage、error_message 和 warnings 等细节，不能把它伪装成空结果或 fixture 成功结果。

## 固定样例数据规格

P1-T02 应基于本规格实现固定样例数据。除非后续任务规格另有说明，建议文件位置为：

```text
src/astra/theme_research/fixtures/low_altitude_economy.json
```

样例数据只用于流程验证。它应稳定、可复现、可被单元测试直接加载。

### 顶层结构

```json
{
  "fixture_id": "low_altitude_economy",
  "display_name": "低空经济",
  "market": "cn_a",
  "as_of": "2026-06-15",
  "aliases": ["低空经济", "低空", "eVTOL", "无人机", "通航"],
  "description": "固定样例主题，用于验证主题到股票池研究漏斗。",
  "companies": [],
  "data_boundary": []
}
```

字段要求：

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `fixture_id` | string | 固定为 `low_altitude_economy` |
| `display_name` | string | 固定为 `低空经济` |
| `market` | string | 固定为 `cn_a` |
| `as_of` | string | 固定样例数据时间点 |
| `aliases` | array | 至少包含 `低空经济` |
| `description` | string | 说明样例用途 |
| `companies` | array | 至少 6 个候选公司记录 |
| `data_boundary` | array | 说明样例数据非实时、非投资建议 |

### 公司样例记录

每个公司记录应能转换为 `CandidateStock`。

```json
{
  "symbol": "000000.SZ",
  "name": "样例公司",
  "market": "cn_a",
  "exchange": "SZSE",
  "industry": "航空装备",
  "concepts": ["低空经济", "无人机"],
  "recall_keywords": ["低空经济", "无人机"],
  "business_summary": "样例业务摘要。",
  "financial_summary": "样例财务摘要。",
  "text_summary": "样例文本资料摘要。",
  "risks": ["样例风险"],
  "evidence": []
}
```

公司记录要求：

- 至少 6 条候选记录，便于测试召回、过滤、排序和 `max_results`。
- 至少 3 条记录应与 `低空经济` 高相关。
- 至少 1 条记录应为弱相关候选，用于验证粗排过滤。
- 至少 1 条记录应包含缺失或低置信度证据，用于验证证据边界。
- 每条记录必须包含至少 3 个 `EvidenceItem`。
- 每条记录必须包含至少 1 个风险项。
- 如果使用真实 A 股公司名称和代码，必须在证据中保留来源、日期和样例边界说明。

## P1-T02 实现设计

P1-T02 的目标是把本文档中的合同变成后端可导入、可验证的领域模型和固定样例数据。它只建立数据层基础，不实现研究漏斗业务逻辑。

### 职责

P1-T02 负责：

- 创建主题研究后端包结构。
- 定义合同对应的 Pydantic 模型。
- 定义固定样例数据模型。
- 落盘 `低空经济` 固定样例 JSON。
- 提供 fixture 加载函数。
- 用单元测试验证模型校验、默认值、样例加载和关键边界。

### 非职责

P1-T02 不负责：

- 实现候选召回算法。
- 实现证据补全、粗排、精排或报告生成。
- 暴露主题研究 API。
- 修改前端页面。
- 接入外部真实数据源。
- 引入新的运行时依赖。

### 建议包结构

P1-T02 建议新增以下后端结构：

```text
src/astra/theme_research/
  __init__.py
  contracts.py
  fixtures.py
  fixtures/
    low_altitude_economy.json
tests/unit/theme_research/
  test_contracts.py
  test_fixtures.py
```

文件职责：

| 文件 | 职责 |
| --- | --- |
| `contracts.py` | 定义 Phase 1 主题研究请求、响应、错误、候选股票、证据、评分、报告和流程追踪模型 |
| `fixtures.py` | 定义固定样例数据加载入口，不包含召回、排序或报告逻辑 |
| `fixtures/low_altitude_economy.json` | 保存 `低空经济` 固定样例数据 |
| `test_contracts.py` | 验证模型默认值、枚举边界、字段约束和 JSON 序列化 |
| `test_fixtures.py` | 验证 fixture 文件存在、可加载、字段完整、样例数量和数据边界 |

### 模型边界

`contracts.py` 应优先定义以下模型：

- `ThemeResearchRequest`
- `NormalizedThemeRequest`
- `ThemeResearchResponse`
- `ThemeResearchResult`
- `ThemeResearchErrorResponse`
- `ThemeResearchError`
- `CandidateStock`
- `EvidenceItem`
- `ScoreBreakdown`
- `ScoreFactor`
- `ResearchReport`
- `FocusCompany`
- `PipelineStageTrace`
- `FixtureThemeDataset`
- `FixtureCompany`

建议使用 `Literal` 或 `Enum` 固定以下值域：

- `market`: `cn_a`
- `exchange`: `SZSE`、`SSE`
- `evidence.kind`
- `evidence.stance`
- `evidence.source_type`
- `evidence.confidence`
- `pipeline.stage`
- `error.code`

P1-T02 只需要模型能表达合同并校验固定样例数据。复杂校验可以留到后续任务，但以下校验应在 P1-T02 覆盖：

- `theme` 去除首尾空白后不能为空。
- `max_results` 范围为 `1` 到 `10`。
- 分数范围为 `0` 到 `100`。
- `rank` 允许为 `null`，非空时必须大于等于 `1`。
- `FixtureThemeDataset.companies` 至少包含 6 条记录。
- 每个 `FixtureCompany.evidence` 至少包含 3 条证据。
- 每个 `FixtureCompany.risks` 至少包含 1 条风险。

### Fixture Loader 边界

`fixtures.py` 应提供一个稳定、低魔法的加载入口：

```python
def load_low_altitude_economy_fixture() -> FixtureThemeDataset:
    ...
```

加载规则：

- 使用标准库读取包内 JSON 文件。
- 返回 `FixtureThemeDataset` 模型实例。
- 加载失败时抛出明确异常，测试中应能定位到缺失文件或数据结构错误。
- 不在 loader 中做召回、过滤、排序或证据加工。
- 不访问网络、数据库、缓存或用户目录。

### 样例数据取舍

P1-T02 可以使用真实 A 股公司代码与名称，也可以使用明确标识的样例公司。无论选择哪种，都必须满足：

- 数据用于流程验证，不代表实时市场事实。
- 所有证据来源在 Phase 1 最小实现中可标记为 `fixture`。
- `data_boundary` 必须说明样例数据的非实时、非投资建议和可复现用途。
- 不写入收益预测、目标价或交易动作。

### 错误处理策略

P1-T02 只定义错误模型，不需要把错误映射为 HTTP 响应。

错误边界：

- 请求校验错误由 Pydantic 模型负责。
- fixture 缺失或结构错误应作为开发期错误暴露。
- `no_candidates` 的业务错误只定义模型和错误码，不在 P1-T02 触发。
- HTTP 状态码映射留给 P1-T11 API 任务实现。

### 测试策略

P1-T02 只需要单元测试和静态检查。

必须覆盖：

- `ThemeResearchRequest` 默认值和输入归一化。
- 空主题、非法 `market`、非法 `max_results` 校验失败。
- `EvidenceItem`、`ScoreBreakdown`、`PipelineStageTrace` 的枚举和范围校验。
- `load_low_altitude_economy_fixture()` 可以稳定加载样例数据。
- 样例数据包含至少 6 个候选公司。
- 样例数据包含 `低空经济`、`低空`、`eVTOL`、`无人机` 中的别名。
- 每个候选公司至少 3 条证据、1 条风险。
- `data_boundary` 包含非实时、固定样例和非投资建议说明。

建议验证命令：

```bash
make test-unit
make check
```

如果 P1-T02 只改后端模型和 fixture，Playwright 失败才需要专项排查；正常情况下仍以 `make check` 作为任务完成验证。

## P1-T03 实现设计

P1-T03 的目标是基于固定样例数据实现候选股票召回。召回阶段追求覆盖，允许噪声进入后续粗排，但必须保留匹配来源，保证可解释和可测试。

### 职责

P1-T03 负责：

- 规范化主题查询文本。
- 基于主题别名、公司概念和召回关键词召回候选公司。
- 为每个候选记录匹配来源、匹配词和召回分数。
- 对多来源命中的同一家公司去重。
- 返回稳定排序的召回结果和 `candidate_recall` 阶段追踪。
- 用单元测试覆盖命中、别名、无命中、去重和数量限制。

### 非职责

P1-T03 不负责：

- 补充或改写证据内容。
- 执行粗排、精排或最终排名。
- 生成研究报告。
- 暴露后端 API。
- 修改前端页面。
- 接入外部数据源。

### 建议包结构

P1-T03 建议新增或更新：

```text
src/astra/theme_research/
  contracts.py
  recall.py
tests/unit/theme_research/
  test_recall.py
```

文件职责：

| 文件 | 职责 |
| --- | --- |
| `contracts.py` | 增加 `RecallMatch`、`RecalledCandidate` 和 `CandidateRecallResult` 模型 |
| `recall.py` | 实现查询归一化和固定样例候选召回 |
| `test_recall.py` | 验证召回命中、无命中、去重、排序和限制数量 |

### 召回规则

最小召回规则：

- 查询先执行 `strip` 和 `casefold`，用于稳定匹配。
- 当查询命中主题 `aliases` 中任意别名时，召回整个 fixture 主题内的候选公司，以保证召回阶段覆盖和保留噪声。
- 公司级匹配来源包括 `concepts` 和 `recall_keywords`。
- 如果公司没有命中具体概念或关键词，但查询命中了主题别名，仍可以通过 `theme_alias` 召回，分数较低，交给后续粗排处理。
- 同一 `symbol` 多来源命中时只返回一条候选，并合并匹配来源。
- 排序规则为 `recall_score` 降序，然后 `symbol` 字典序升序，保证测试稳定。

### 输出模型

`RecallMatch` 字段：

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `source` | string | `theme_alias`、`concept` 或 `recall_keyword` |
| `term` | string | 命中的主题别名、概念或关键词 |
| `reason` | string | 简短匹配说明 |

`RecalledCandidate` 字段：

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `company` | object | 对应 `FixtureCompany` |
| `matches` | array | 至少 1 条 `RecallMatch` |
| `recall_score` | number | `0` 到 `100` |

`CandidateRecallResult` 字段：

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `normalized_query` | string | 归一化查询 |
| `matched_aliases` | array | 命中的主题别名 |
| `candidates` | array | 稳定排序后的召回候选 |
| `pipeline` | object | `candidate_recall` 阶段追踪 |

### 测试策略

P1-T03 至少覆盖：

- `低空经济` 可以召回固定样例主题内的候选公司。
- `无人机` 作为主题别名可以触发同一 fixture 主题召回。
- 未知主题返回空候选和 `output_count=0`。
- 多来源命中的公司只出现一次，且保留多个匹配来源。
- `max_candidates` 可以限制返回数量。
- 召回结果排序稳定。

建议验证命令：

```bash
make test-unit
make check
```

## P1-T07 实现设计

P1-T07 的目标是在候选召回之后、模型粗排之前，为候选公司生成结构化证据包。该阶段追求证据结构化、来源保留和缺失边界透明，不生成最终排序、模型评分或报告文案。

### 职责

P1-T07 负责：

- 接收 `CandidateRecallResult` 和其中的 `RecalledCandidate`。
- 合并 fixture 已有证据，并补充 fixture 中的业务、财务、文本和风险摘要。
- 将真实 `MarketDataProvider` 的概念、行业、主营业务和财务摘要字段转换为 `EvidenceItem`。
- 输出 `EvidencePackage`、`EnrichedCandidate` 和 `EvidenceEnrichmentResult` 中间合同。
- 保留缺失证据类型、数据边界、provider 来源、获取时间和 warning。
- 为后续 `WebKnowledgeProvider`、公告、新闻、研报或 RAG provider 预留扩展口。

### 非职责

P1-T07 不负责：

- 将真实网页、新闻、公告或研报搜索接入主路径。
- 生成粗排分数、精排分数、最终排名或入选结论。
- 调用模型归纳证据。
- 生成研究报告。
- 暴露后端 API 或修改前端页面。
- 用行业接口参与候选召回。

### 输出模型

P1-T07 新增以下中间合同：

| 模型 | 用途 |
| --- | --- |
| `BusinessProfileRecord` | 表示 provider 归一化后的主营业务、产品类型、产品名称和经营范围 |
| `FinancialSnapshotRecord` | 表示 provider 归一化后的最新财务摘要指标 |
| `EvidencePackage` | 承载单个候选的证据列表、缺失证据类型、数据边界和 warning |
| `EnrichedCandidate` | 承载候选公司、召回来源、召回分数和证据包 |
| `EvidenceEnrichmentResult` | 承载证据补全阶段的候选列表、pipeline trace、边界和 warning |

`EvidencePackage` 不包含 `rank`、`coarse_score`、`final_score` 或 `selection_reason`。这些字段属于 P1-T08/P1-T09 的模型排序阶段。

### 数据源策略

P1-T07 主路径采用：

- `MarketDataProvider`：概念、行业、主营业务和财务摘要等结构化或半结构化市场数据。
- fixture：稳定测试替代数据和固定样例证据；正常 Web/API 主路径不静默使用 fixture fallback。

P1-T07 不把真实网页、新闻、公告或研报搜索作为主路径。真实网页材料后续应通过独立 `WebKnowledgeProvider` 或其他 evidence provider 接入。

AKShare 探测结果：

- `stock_zyjs_ths` 可作为主营业务资料来源，返回主营业务、产品类型、产品名称和经营范围。
- `stock_financial_abstract` 可作为财务摘要来源，提取最新报告期中的营业总收入、归母净利润、净利润和扣非净利润等可得指标。
- `stock_individual_info_em` 本轮探测遇到 `RemoteDisconnected`，不作为 P1-T07 依赖。
- 东方财富概念接口仍可能临时失败；正常 Web/API 失败时必须返回结构化 provider 错误，测试替代或显式 fallback 状态必须透明标注。

### 缺失证据处理

证据补全不得编造无法从 provider 或 fixture 取得的证据。

当真实 provider 候选缺少文本摘要、风险证据、业务资料或财务资料时：

- 保留候选。
- 在 `missing_kinds` 中记录缺失的 `EvidenceKind`。
- 在 `warnings` 中记录 provider 未配置、接口失败或字段不可用。
- 在 `data_boundary` 中说明 P1-T07 未使用 `WebKnowledgeProvider`，因此不包含真实网页、新闻、公告或研报文本证据。

### 测试策略

P1-T07 至少覆盖：

- fixture 候选可以生成完整证据包。
- provider 候选可以把概念、行业、主营业务和财务摘要映射为 `market_data_provider` 来源的 `EvidenceItem`。
- provider 失败时保留候选，并记录缺失证据和 warning。
- 真实 AKShare 集成测试窄路径验证 `stock_zyjs_ths` 和 `stock_financial_abstract` 可以生成业务与财务证据。

建议验证命令：

```bash
uv run pytest tests/unit/theme_research -q
uv run pytest tests/integration/test_akshare_market_data_provider.py -vv
make check
```

## P1-O03 市场元数据缓存与 AKShare 概念接口韧性

P1-O03 的目标是在不恢复 fixture 静默 fallback 的前提下，提高 AKShare 概念板块召回的可用性。它解决的是 `stock_board_concept_name_em` 概念发现接口和 `stock_board_concept_cons_em` 成分接口临时断连导致正常 Web/API 无法研究 `低空经济` 的问题。

### 职责

P1-O03 负责：

- 定义只读 `MarketMetadataSnapshot`，记录变化频率较低的市场元数据。
- 提供 `MarketMetadataStore`，支持按主题 canonical name、别名、provider 板块名或板块代码查找概念板块。
- 提供 `MarketMetadataBackedProvider`，默认包裹 `AkshareMarketDataProvider`。
- 候选召回时先使用本地元数据解析 AKShare 板块代码，再调用真实 AKShare 概念成分接口。
- 当真实成分接口失败或返回空结果时，允许返回 seed 快照中的缓存成分，但必须标记 `ProviderMetadata.is_fallback=true` 并保留 live 失败原因。
- 在证据边界和 WebUI 中区分 `AKShare live` 与 `AKShare cached`。

### 非职责

P1-O03 不负责：

- 建立完整股票、行业、主题或概念数据库。
- 自动刷新市场元数据、定期巡检、过期淘汰或后台同步。
- 接入新的商业数据源。
- 把固定样例 fixture 恢复为正常 Web/API 主路径 fallback。
- 保证缓存成分完整、实时或权威。

### 快照字段

市场元数据 seed 至少包含：

| 字段 | 用途 |
| --- | --- |
| `snapshot_id` | 标识快照来源和版本 |
| `as_of` | 快照日期 |
| `canonical_name` | ASTRA 内部主题/概念标准名 |
| `aliases` | 用户输入别名和常见同义表达 |
| `provider_name` | 原始数据 provider，例如 `akshare` |
| `provider_interface` | 原始接口，例如 `stock_board_concept_cons_em` |
| `board_code` | provider 板块代码，例如 `BK1166` |
| `provider_board_name` | provider 中的板块展示名 |
| `retrieved_at` | 快照获取时间 |
| `constituents` | 少量真实来源缓存成分，用于接口失败时的透明 fallback |

缓存成分必须继续映射为 `ConceptConstituentRecord`，并把 `provider_interface` 写成 `market_metadata_cache:<original_interface>:<board_code>` 形式，方便 API、报告和前端识别。

### Web/API 行为

默认主题研究路径使用：

```text
MarketMetadataBackedProvider(AkshareMarketDataProvider())
```

行为顺序：

1. `list_concept_boards()` 返回本地元数据中的 canonical name 和 aliases，避免每次请求依赖 AKShare 概念发现接口。
2. 命中本地板块后，`list_concept_constituents()` 使用 `board_code` 调用真实 AKShare 成分接口。
3. 如果真实成分接口成功，候选来源仍是 `AKShare live`。
4. 如果真实成分接口失败或为空，且 seed 有缓存成分，候选来源是 `AKShare cached`，并在 `data_boundary`、`warnings` 或错误 details 中保留 live 失败原因。
5. 如果本地元数据未覆盖该主题，或缓存也无可用成分，仍按 provider 不可用或无候选处理，不能静默返回 fixture 股票池。

### 测试策略

P1-O03 至少覆盖：

- seed 快照可以加载，并能通过 `低空经济`、`低空`、`飞行汽车`、`eVTOL` 等名称命中板块代码。
- wrapper 对命中的概念使用板块代码调用 primary provider，而不是调用 live 概念发现接口。
- primary 成分接口失败时返回缓存成分，并保留 `is_fallback` 和 `failure_reason`。
- 默认主题研究服务可以在 AKShare 概念成分接口失败时返回缓存股票池，并在数据边界中标注缓存来源。
- 前端成功流能展示 `AKShare cached`，E2E 使用 mocked HTTP response，不代表真实 AKShare 通过。
- live 巡检需要说明结果是 live 成分接口成功，还是 metadata-backed cached fallback。

建议验证命令：

```bash
uv run pytest tests/unit/theme_research/test_market_metadata.py tests/unit/theme_research/test_service.py -q
make check
make test-live-akshare
```

## P1-T08 实现设计

P1-T08 的目标是在证据补全之后、模型精排之前，通过低成本模型规格完成候选初筛、粗排评分、保留/过滤判断和理由生成。

### 职责

P1-T08 负责：

- 定义模型规格合同 `ModelSpec`，记录 provider、模型名、用途、提示词版本、温度和输出长度边界。
- 定义粗排输出合同 `CoarseRankDecision`、`CoarseRankedCandidate` 和 `CoarseRankResult`。
- 定义统一 `ModelClient.generate_structured()` 接口，业务逻辑不直接依赖任何真实模型供应商 SDK 或 HTTP 响应。
- 将 `EvidenceEnrichmentResult` 压缩为模型输入 payload。
- 校验模型结构化输出 schema、股票代码一致性和证据 ID 引用。
- 拦截买入、卖出、持仓、目标价、仓位和交易时机等交易指令。
- 应用最小粗排保留阈值，输出保留/过滤结果和 `coarse_rank` pipeline trace。

### 非职责

P1-T08 不负责：

- 调用真实模型 API。
- 生成精排最终分数、最终排序、入选结论或报告。
- 修改候选召回或证据补全逻辑。
- 暴露后端 API 或修改前端页面。
- 绕过结构化输出校验接受自由文本模型结果。

### 输出模型

P1-T08 新增以下模型：

| 模型 | 用途 |
| --- | --- |
| `ModelSpec` | 记录模型供应商、模型名、用途和提示词版本 |
| `CoarseRankDecision` | 表示单个候选的粗排分数、保留/过滤判断、理由、风险摘要和证据引用 |
| `CoarseRankedCandidate` | 绑定证据补全候选和粗排决策 |
| `CoarseRankResult` | 表示粗排阶段整体输出、模型规格、pipeline trace、边界和 warning |

`CoarseRankDecision.supporting_evidence_ids` 必须引用候选证据包中真实存在的 `EvidenceItem.id`。P1-T08 不生成 `rank` 或 `final_score`，这些留给 P1-T09。

### Fake Model Client

P1-T08 默认只实现 `FakeCoarseRankModelClient`：

- 不访问网络。
- 不调用真实模型 API。
- 对相同输入返回固定结构化结果。
- 根据召回分、缺失证据和证据文本中的弱相关线索生成粗排分和保留/过滤判断。
- 用于单元测试和后续本地端到端流程的稳定替代。

真实模型 client 只能在后续显式授权或专门任务中接入。

### 过滤与安全规则

P1-T08 的粗排保留需要同时满足：

- 模型结构化输出 `keep=true`。
- `coarse_score` 不低于 `min_keep_score`，默认 `60`。
- 输出未包含交易指令或确定性投资建议。

如果模型输出引用不存在的证据 ID、股票代码与输入候选不一致、分数越界或缺少必填字段，应抛出结构化输出校验错误。如果输出包含交易指令，应抛出安全错误。

### 测试策略

P1-T08 至少覆盖：

- fake model client 可以稳定保留强相关候选并过滤弱相关候选。
- fake model client 使用正确 schema 名称。
- 结构化输出 schema 校验失败时拒绝结果。
- 模型输出引用不存在的证据 ID 时拒绝结果。
- 模型输出包含交易指令时拒绝结果。
- 低于保留阈值时，即使模型返回 `keep=true` 也会被过滤。

建议验证命令：

```bash
uv run pytest tests/unit/theme_research -q
uv run ruff check .
```

## P1-T09 实现设计

P1-T09 的目标是在粗排之后、报告生成之前，通过更高质量模型规格完成最终排序、解释、风险判断和不确定性说明。Phase 1 自动化测试仍使用 fake model client，不调用真实模型 API。

### 职责

P1-T09 负责：

- 定义 `DeepRankDecision`、`DeepRankedCandidate` 和 `DeepRankResult`。
- 复用统一 `ModelClient.generate_structured()` 接口，保持模型供应商无关。
- 只对 P1-T08 中 `keep=true` 的候选执行精排，过滤候选不进入最终排序。
- 将粗排结果、候选证据包、召回分、粗排分、缺失证据和数据边界压缩为模型输入 payload。
- 校验模型结构化输出 schema、股票代码一致性和证据 ID 引用。
- 生成最终分数、稳定 rank、最终排序理由、风险判断、不确定性和关键风险。
- 拦截买入、卖出、持仓、目标价、仓位和交易时机等交易指令。

### 非职责

P1-T09 不负责：

- 调用真实模型 API。
- 生成研究报告。
- 暴露后端 API 或修改前端页面。
- 重新召回候选或补充证据。
- 输出确定性投资建议或交易动作。

### 输出模型

P1-T09 新增以下模型：

| 模型 | 用途 |
| --- | --- |
| `DeepRankDecision` | 表示最终分、rank、排序理由、风险判断、不确定性、证据引用和关键风险 |
| `DeepRankedCandidate` | 绑定粗排候选和精排决策 |
| `DeepRankResult` | 表示精排阶段整体输出、模型规格、pipeline trace、边界和 warning |

`DeepRankDecision.rank` 由 ASTRA 在模型输出校验和排序后稳定分配，不依赖模型自行给出的名次。

### Fake Model Client

P1-T09 默认只实现 `FakeDeepRankModelClient`：

- 不访问网络。
- 不调用真实模型 API。
- 对相同输入返回固定结构化结果。
- 根据召回分、粗排分、缺失证据和风险证据生成最终分数、风险判断和不确定性说明。
- 用于单元测试和后续本地端到端流程的稳定替代。

### 排序与安全规则

精排排序规则：

- 仅 `keep=true` 的粗排候选进入精排。
- 按 `final_score` 降序排序。
- `final_score` 相同时按 `coarse_score` 降序。
- 仍相同时按 `symbol` 字典序升序，保证测试稳定。
- 排序后从 `1` 开始分配 `rank`。

如果模型输出引用不存在的证据 ID、股票代码与输入候选不一致、分数越界、缺少必填字段或包含交易指令，应拒绝结果。

### 测试策略

P1-T09 至少覆盖：

- fake model client 只精排粗排保留候选，并排除过滤候选。
- 最终排序和 rank 稳定。
- `max_results` 可以限制精排输出数量。
- fake model client 使用正确 schema 名称。
- 结构化输出 schema 校验失败时拒绝结果。
- 模型输出引用不存在的证据 ID 时拒绝结果。
- 模型输出包含交易指令时拒绝结果。

建议验证命令：

```bash
uv run pytest tests/unit/theme_research -q
uv run ruff check .
```

## P1-T10 实现设计

P1-T10 的目标是在精排之后、API 暴露之前，基于结构化证据、粗排结果和精排结果生成 `ThemeResearchResult` 中的股票池和研究报告。Phase 1 自动化测试仍使用 fake model client，不调用真实模型 API。

### 职责

P1-T10 负责：

- 定义 `report_generation_model_spec` 和报告生成 schema 名称。
- 复用统一 `ModelClient.generate_structured()` 接口，保持模型供应商无关。
- 将 `DeepRankResult` 映射为最终 `CandidateStock` 列表，保留召回来源、证据、分数、rank、入选理由和主要风险。
- 基于精排结果、证据引用、风险和数据边界生成结构化 `ResearchReport`。
- 校验报告结构化输出 schema、重点公司代码和证据 ID 引用。
- 输出非投资建议说明，并拦截报告正文中的买入、卖出、持仓、目标价、仓位和交易时机等交易指令。
- 生成 `report_generation` pipeline trace，并透传前序数据边界和 warning。

### 非职责

P1-T10 不负责：

- 调用真实模型 API。
- 暴露后端 API 或修改前端页面。
- 重新召回候选、补充证据、粗排或精排。
- 生成确定性投资建议、交易动作或收益承诺。
- 解决真实 AKShare 概念接口临时断连问题。

### 输出与安全规则

报告生成输出必须满足：

- `pool` 按精排结果顺序生成，候选包含完整分数拆解、证据、rank、入选理由和风险。
- `ResearchReport.focus_companies[].supporting_evidence_ids` 只能引用对应股票池候选已有的 `EvidenceItem.id`。
- `data_boundary` 必须来自前序流程记录或报告 payload，不能伪装成已验证的实时事实。
- `not_investment_advice` 必须明确说明报告仅用于研究流程验证和信息整理，不构成投资建议、收益承诺或操作依据。
- 报告标题、摘要、主题概述、股票池摘要、重点公司理由和风险提示不得包含交易指令。

### Fake Model Client

P1-T10 默认只实现 `FakeReportGenerationModelClient`：

- 不访问网络。
- 不调用真实模型 API。
- 对相同输入返回固定结构化结果。
- 直接使用上游 payload 中的重点公司、风险和数据边界，避免在测试中引入模型随机性。
- 用于单元测试和后续本地端到端流程的稳定替代。

### 测试策略

P1-T10 至少覆盖：

- 可以从 `DeepRankResult` 生成非空股票池和结构化报告。
- 重点公司引用的证据 ID 均存在于对应股票的证据列表。
- 结构化输出 schema 校验失败时拒绝结果。
- 报告引用不存在的证据 ID 时拒绝结果。
- 报告输出包含交易指令时拒绝结果。

建议验证命令：

```bash
uv run pytest tests/unit/theme_research -q
uv run pytest tests/unit -q
uv run ruff check .
```

## P1-T11 实现设计

P1-T11 的目标是把 Phase 1 主题研究漏斗暴露为后端 API，供前端在 P1-T12 调用。API 主路径使用固定样例数据和 fake model client 串起召回、证据补全、粗排、精排和报告生成，不主动访问真实 AKShare，也不调用真实模型 API。

### 职责

P1-T11 负责：

- 在 FastAPI 应用中新增 `POST /api/theme-research`。
- 接收主题研究请求 payload，映射为 `ThemeResearchRequest`。
- 调用应用服务 `run_theme_research()`，返回 `ThemeResearchResponse`。
- 覆盖成功、无候选、空主题和非 `cn_a` 市场错误路径。
- 返回结构化 `ThemeResearchErrorResponse`，保持 Phase 1 错误合同一致。
- 保留完整 pipeline trace，让前端能展示研究流程状态。

### 非职责

P1-T11 不负责：

- 构建前端页面。
- 使用 Playwright 做浏览器端到端测试。
- 访问真实 AKShare 概念接口或修复其临时断连。
- 调用真实模型 API。
- 引入认证、限流、异步任务队列、数据库或生产级任务状态管理。

### API 行为

`POST /api/theme-research` 的最小行为：

- 合法请求返回 `200` 和 `ThemeResearchResponse`。
- `include_report=false` 时仍返回股票池和 pipeline，但 `report=null`，且不追加 `report_generation` stage。
- 无候选返回 `404` 和 `ThemeResearchErrorResponse(code=no_candidates)`。
- 空主题、超出 `max_results` 范围或非 object 请求返回 `400` 和 `ThemeResearchErrorResponse(code=invalid_request)`。
- 非 `cn_a` 市场返回 `400` 和 `ThemeResearchErrorResponse(code=unsupported_market)`。

### 测试策略

P1-T11 至少覆盖：

- 成功请求返回股票池、报告和完整 pipeline。
- `include_report=false` 返回股票池但不返回报告。
- 无候选主题返回结构化 `no_candidates` 错误。
- 空主题返回结构化 `invalid_request` 错误。
- 非 `cn_a` 市场返回结构化 `unsupported_market` 错误。

建议验证命令：

```bash
uv run pytest tests/integration/test_theme_research_api.py tests/integration/test_health_api.py -q
uv run pytest tests/unit -q
uv run ruff check .
```

## P1-T12 实现设计

P1-T12 的目标是提供最小可用的主题研究前端页面，让用户可以提交主题、查看股票池、查看研究报告和错误状态。页面只调用 P1-T11 的 `POST /api/theme-research`，不直接访问 AKShare 或模型 API。

### 职责

P1-T12 负责：

- 将前端首屏改为主题研究工作台。
- 保留紧凑的后端健康状态展示。
- 提供主题、结果数和是否生成报告的输入控件。
- 展示加载中、成功和错误状态。
- 展示股票池候选、rank、最终分、召回/粗排分、行业、概念、证据数、入选理由和主要风险。
- 展示研究报告摘要、主题概述、股票池摘要、重点公司、数据边界和非投资建议说明。
- 展示 pipeline stage，方便后续端到端测试定位流程。

### 非职责

P1-T12 不负责：

- 编写 Playwright 端到端测试。
- 实现完整设计系统。
- 实现认证、历史记录、异步任务状态或多主题批处理。
- 直接访问真实 AKShare 或真实模型 API。
- 修复 P1-T06 真实 AKShare 概念接口临时断连。

### 前端状态

页面最小状态包括：

- `idle`：尚未提交请求。
- `loading`：请求正在执行。
- `ready`：展示 `ThemeResearchResponse`。
- `error`：展示 `ThemeResearchErrorResponse` 的 code 和 message。

### 测试策略

P1-T12 至少覆盖：

- `npm run lint` 通过。
- `npm run build` 通过。
- 构建过程不依赖真实 AKShare 或真实模型 API。

建议验证命令：

```bash
cd frontend && npm run lint
cd frontend && npm run build
```

## P1-T13 实现设计

P1-T13 的目标是使用 Playwright 验证最小主题研究端到端流程。测试启动本地 FastAPI 后端和 Vite 前端，并在 Chromium 中执行真实浏览器交互；后端仍使用 P1-T11 fixture-backed API，不访问真实 AKShare 或真实模型 API。

### 职责

P1-T13 负责：

- 覆盖用户在前端输入主题并提交研究请求。
- 验证页面展示股票池结果。
- 验证页面展示研究报告摘要和非投资建议说明。
- 验证页面展示完整 `report_generation` pipeline stage。
- 覆盖无候选主题的错误状态。
- 让 E2E 启动后端时优先使用本地 `.venv/bin/python -m uvicorn`，避免本地 `uv` 在 Playwright webServer 中的不稳定启动问题；无本地 venv 时仍回退到 `uv run`。

### 非职责

P1-T13 不负责：

- 新增业务功能。
- 修复真实 AKShare 概念接口临时断连。
- 调用真实模型 API。
- 覆盖复杂移动端、浏览器矩阵或可视回归。

### 测试策略

P1-T13 至少覆盖：

- `低空经济` 成功流程展示股票池和报告。
- 无匹配主题展示结构化错误状态。
- `npm run test:e2e` 通过。

建议验证命令：

```bash
cd frontend && npm run test:e2e
```

## P1-O01 Web 研究工作台优化

P1-O01 的目标是在不改变后端 API 合同和数据边界的前提下，将 Phase 1 前端从 MVP 调试面板优化为单页研究工作台。页面继续调用 P1-T11 的 fixture-backed API，不直接访问真实 AKShare，也不调用真实模型 API。

### 职责

P1-O01 负责：

- 保持单页工作台方向。
- 优化页面信息架构，让输入、研究摘要、股票池、重点公司、报告、证据边界和 pipeline 各自有清晰位置。
- 将股票池展示从卡片流改为更便于扫描的表格。
- 提供报告、证据和流程的分段视图。
- 在页面顶部保留 `Fixture data` 和 `Fake model` 状态标识。
- 更新 Playwright E2E 断言，覆盖成功流和错误流。

### 非职责

P1-O01 不负责：

- 改变后端 API 合同。
- 处理 AKShare live 测试分层或真实接口不稳定问题。
- 调用真实模型 API。
- 引入认证、历史记录、多主题批处理或完整设计系统。

### 测试策略

P1-O01 至少覆盖：

- `npm run lint` 通过。
- `npm run build` 通过。
- `npm run test:e2e` 通过。

建议验证命令：

```bash
cd frontend && npm run lint
cd frontend && npm run build
cd frontend && npm run test:e2e
```

## P1-O02 AKShare live 测试分层与降级透明化

P1-O02 的目标是修正 Phase 1 正常 Web/API 路径的数据真实性边界：正常系统不再静默使用 fixture 生成研究结果，而是默认通过 `AkshareMarketDataProvider` 访问真实 AKShare；当 AKShare 不可用时，API 返回结构化错误，前端展示接口问题。

### 职责

P1-O02 负责：

- 将 `run_theme_research()` 默认主路径切换为 `AkshareMarketDataProvider`。
- 正常 `/api/theme-research` 不传入 fixture fallback；固定样例数据仅作为测试替代或显式注入的 provider 使用。
- 新增 `provider_unavailable` 错误码，HTTP 映射为 `502`。
- 在 provider 失败时返回 `provider`、`stage`、`normalized_query`、`warnings` 和 `error_message`。
- 保持 `no_candidates` 与 provider 失败分离：数据源可访问但没有候选时返回 `404 no_candidates`。
- Web 页面顶部展示 `AKShare live` 和 `Fake model`，错误状态展示 provider 失败详情。
- 将真实 AKShare 网络测试标记为 `pytest.mark.live`，从默认 `make check` 中拆出。
- 新增 `make test-live-akshare`，作为真实 AKShare 网络巡检入口。

### 非职责

P1-O02 不负责：

- 修复 AKShare/东方财富概念接口自身的 `RemoteDisconnected` 或上游可用性问题。
- 接入真实模型 API；粗排、精排和报告生成仍使用 fake model client。
- 接入行业接口、新闻、公告、研报或 WebKnowledgeProvider。
- 构建定时巡检任务。定时巡检属于后续独立任务，应复用 `make test-live-akshare` 或封装同等检查。

### 测试策略

P1-O02 至少覆盖：

- `make check` 通过，且不访问真实 AKShare。
- `make test-live-akshare` 真实访问 AKShare，并如实报告成功或失败。
- API 集成测试使用注入 runner/provider，避免默认测试触网。
- Playwright E2E 使用 mocked `/api/theme-research` 响应验证 UI 成功流和 provider 错误流，不代表真实 AKShare 已通过。
- 直接访问默认 API 路径时，如果 AKShare 概念接口失败，应返回 `502 provider_unavailable`，不得返回 fixture 股票池。

建议验证命令：

```bash
make check
make test-live-akshare
```

## 最小验收口径

后续实现应满足以下可测试行为：

- 使用测试 provider 或 fixture 的合法请求 `theme=低空经济`、`market=cn_a` 可以稳定返回非空股票池。
- 真实 AKShare 可用时，合法请求 `theme=低空经济`、`market=cn_a` 应返回 provider-backed 股票池；AKShare 不可用时返回 `provider_unavailable`。
- `低空经济`、`低空`、`eVTOL`、`无人机` 至少一个别名能在测试替代数据中召回同一个样例主题。
- 返回结果按 `rank` 升序排列，且排序稳定。
- `max_results` 能限制最终 `pool` 数量。
- 每个入选股票都有代码、名称、召回来源、分数、排名、入选理由、关键证据和主要风险。
- 研究报告包含主题概述、股票池汇总、重点公司解释、风险提示和数据边界说明。
- 空主题返回 `invalid_request`。
- 非 `cn_a` 市场返回 `unsupported_market`。
- 合法但无候选的主题返回 `no_candidates`。
- 真实市场数据 provider 断连、超时或概念板块发现失败时返回 `provider_unavailable`。
- 输出文本不得包含确定性投资建议或交易指令。

## 后续任务映射

- P1-T02：根据本合同实现领域模型和固定样例数据加载。
- P1-T03：基于 `aliases`、`recall_keywords` 和 `concepts` 实现候选召回。
- P1-T04：完成股票数据 API 选型与数据源规格，明确真实数据源、字段、许可边界和降级方式。
- P1-T05：实现股票数据源 adapter 与 fixture 降级路径。
- P1-T06：将真实数据源接入候选召回模块，保留 fixture 作为测试替代。
- P1-T07：基于候选记录和 `EvidenceItem` 实现证据补全。
- P1-T08：实现模型粗排基线，定义 `coarse_rank_model_spec`、模型输入输出 schema 和 fake model client 测试。
- P1-T09：实现模型精排基线，定义 `deep_rank_model_spec`、最终排序解释和风险判断。
- P1-T10：根据 `ResearchReport` 结构生成报告，必要时定义 `report_generation_model_spec`。
- P1-T11：将请求、成功响应和错误响应暴露为后端 API。
- P1-T12：在前端展示请求输入、股票池、报告和错误状态。
- P1-T13：用 Playwright 覆盖成功、无结果和错误状态。
- P1-T14：对照 Phase 1 验收标准收尾。

## P1-T01 验收检查

P1-T01 完成时应确认：

- 本文档已落盘。
- 本文档明确了输入、输出、样例主题、样例数据和验收口径。
- Phase 1 任务记录已更新。
- 未修改业务代码、依赖或 Git 状态。
