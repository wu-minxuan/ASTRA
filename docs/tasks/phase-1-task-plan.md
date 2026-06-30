# Phase 1 任务计划与进度

本文档记录 Phase 1 主题到股票池研究漏斗阶段的任务拆分、执行顺序和进度状态。

## 任务状态说明

- `not_started`：尚未开始。
- `in_progress`：正在执行。
- `blocked`：被外部条件、授权、依赖或设计问题阻塞。
- `done`：已完成并完成对应验证或交接。

## 当前状态

- 当前阶段：Phase 1 主题到股票池研究漏斗
- 当前任务：P1-T14 Phase 1 总验收
- 当前状态：blocked

## 任务列表

| ID | 任务 | 状态 | 目标 | 验证/完成标准 |
| --- | --- | --- | --- | --- |
| P1-T01 | 研究合同与样例数据规格 | done | 定义主题研究请求、股票池结果、研究报告和固定样例数据规格 | 文档落盘，明确输入输出、样例主题和验收口径 |
| P1-T02 | 后端领域模型与固定样例数据 | done | 实现主题研究相关领域模型和可复现 fixture 数据 | 单元测试通过，样例数据可被测试稳定加载 |
| P1-T03 | 候选股票召回模块 | done | 基于主题和样例数据召回候选 A 股公司 | 单元测试覆盖召回命中、无命中和去重逻辑 |
| P1-T04 | 股票数据 API 选型与数据源规格 | done | 在 Phase 1 内明确真实股票数据 API、字段、许可边界、失败降级和测试替代数据 | 数据源规格或 ADR 落盘，明确选型结论和最小接入字段 |
| P1-T05 | 股票数据源 adapter 与 fixture 降级 | done | 实现真实数据源原始记录到 ASTRA 内部合同的 adapter，并保留 fixture 降级路径 | 单元测试覆盖字段映射、缺失字段、API 失败和 fixture 降级，集成测试覆盖真实 AKShare 数据拉取 |
| P1-T06 | 真实候选召回接入 | done | 将真实数据源接入候选召回模块，评估可用的 AKShare 概念、行业或替代接口，支持从真实主题/概念/板块成分召回 A 股候选 | 单元测试或集成测试覆盖真实数据源成功路径、接口不可用路径、无结果、降级、去重和不假设 `stock_board_concept_cons_em` 一定可用 |
| P1-T07 | 证据补全模块 | done | 为候选公司补充概念、行业、基本面、财务和文本证据摘要 | 单元测试覆盖证据合并、缺失字段和来源保留 |
| P1-T08 | 模型粗排基线 | done | 接入低成本模型规格完成候选初筛、评分、保留/过滤判断和理由生成 | 单元测试覆盖 fake model client、结构化输出、schema 校验和过滤规则 |
| P1-T09 | 模型精排基线 | done | 接入更高质量模型规格完成最终排序、解释、风险判断和不确定性说明 | 单元测试覆盖 fake model client、最终排序、证据引用、风险输出和交易指令拦截 |
| P1-T10 | 研究报告生成基线 | done | 基于股票池、证据和模型排序结果生成结构化研究报告 | 单元测试覆盖报告结构、风险提示、证据边界和非投资建议说明 |
| P1-T11 | 主题研究 API | done | 提供前端可调用的主题研究接口 | 集成测试覆盖成功、无结果和错误输入 |
| P1-T12 | 主题研究前端页面 | done | 支持输入主题、查看股票池、查看研究报告和错误状态 | 前端 lint/build 通过，页面状态可手工或自动验证 |
| P1-T13 | 主题研究端到端测试 | done | 使用 Playwright 验证完整主题研究流程 | E2E 覆盖输入主题、展示股票池、展示报告和错误状态 |
| P1-T14 | Phase 1 总验收 | blocked | 对照 Phase 1 验收标准收尾 | `make check` 通过并形成完成报告 |

## 执行原则

- 一次只推进一个任务，保持 WIP=1。
- 每个任务开始前先确认允许修改范围。
- 每个任务完成后更新本文件中的状态和执行记录。
- 如果任务发现阶段边界或验收标准不合理，应先讨论并更新文档，再继续实现。
- Phase 1 的自动化验收必须保留固定样例数据作为稳定替代数据。
- Phase 1 必须明确并实现一个真实股票数据 API 的最小接入，真实外部数据源不得成为自动化验收的唯一依赖。
- Phase 1 的 Theme-to-Pool 是完整漏斗，不是单纯召回；粗排和精排必须通过模型接口实现，并使用 fake/mock model client 保证自动化测试稳定。

## 初始样例主题

Phase 1 的首个固定样例主题为：

```text
低空经济
```

该主题用于验证完整研究闭环，不代表系统只支持该主题。

## 执行记录

### P1-T01 研究合同与样例数据规格

- 状态：done
- 开始时间：2026-06-15 22:07:54 CST
- 完成时间：2026-06-15 22:10:20 CST
- 授权范围：继续推进 Phase 1；本任务仅落盘研究合同与样例数据规格文档，并更新 Phase 1 任务进度记录；不写业务代码、不改依赖、不提交 Git。
- 实际修改：
  - 新增 `docs/modules/theme-research-contract.md`，定义 Phase 1 主题研究请求、响应、错误、候选股票、证据、评分、报告、流程追踪和固定样例数据规格。
  - 更新 `docs/tasks/phase-1-task-plan.md`，记录 P1-T01 启动、完成、授权范围和验证结果。
- 验证结果：
  - `test -f docs/modules/theme-research-contract.md` 通过，规格文档已落盘。
  - `rg` 检查通过，规格文档包含请求合同、响应合同、核心数据结构、固定样例数据规格和最小验收口径。
  - `rg -n "[ \t]+$" docs/modules/theme-research-contract.md docs/tasks/phase-1-task-plan.md` 未发现尾随空白。
  - `git diff --check` 通过，已跟踪文件 diff 无空白错误。
  - `git status --short` 显示仅修改 `docs/tasks/phase-1-task-plan.md`，新增 `docs/modules/theme-research-contract.md`。
- 备注：P1-T01 已完成；下一步应从 P1-T02 后端领域模型与固定样例数据开始，继续保持 WIP=1。

### P1-T02 后端领域模型与固定样例数据

- 状态：done
- 开始时间：2026-06-15 22:14:03 CST
- 完成时间：2026-06-15 22:29:02 CST
- 授权范围：继续推进 P1-T02；允许补充实现级设计，新增后端主题研究领域模型、固定样例数据、fixture loader 和单元测试，并更新 Phase 1 任务进度记录；不实现召回、证据补全、排序、报告生成、API 或前端；不改依赖、不提交 Git。
- 实际修改：
  - 更新 `docs/modules/theme-research-contract.md`，补充 P1-T02 的职责、非职责、建议包结构、模型边界、fixture loader 边界、样例数据取舍、错误处理策略和测试策略。
  - 新增 `src/astra/theme_research/__init__.py`。
  - 新增 `src/astra/theme_research/contracts.py`，定义 Phase 1 主题研究请求、响应、错误、候选股票、证据、评分、报告、流程追踪和 fixture 数据模型。
  - 新增 `src/astra/theme_research/fixtures.py`，提供 `load_low_altitude_economy_fixture()` 固定样例加载入口。
  - 新增 `src/astra/theme_research/fixtures/low_altitude_economy.json`，提供 `低空经济` 固定样例数据。
  - 新增 `tests/unit/theme_research/test_contracts.py`。
  - 新增 `tests/unit/theme_research/test_fixtures.py`。
  - 更新 `docs/tasks/phase-1-task-plan.md`，记录 P1-T02 启动、完成、授权范围、实际修改和验证结果。
- 验证结果：
  - `rg` 检查通过，确认 `docs/modules/theme-research-contract.md` 包含 P1-T02 实现设计、建议包结构、模型边界、fixture loader 边界、错误处理策略和测试策略。
  - `rg -n "[ \t]+$" docs/modules/theme-research-contract.md docs/tasks/phase-1-task-plan.md` 未发现尾随空白。
  - 首次 `make test-unit` 失败，原因是 `fixtures.py` loader 模块与 `fixtures/` 数据包同名；已删除数据目录的 `__init__.py`，改用标准库 `pathlib` 读取 JSON 文件。
  - 第二次 `make test-unit` 通过，15 个单元测试通过。
  - `make check` 通过，包含 ruff、16 个后端单元/集成测试、前端 lint、前端 build 和 1 个 Playwright Chromium E2E 测试。
- 备注：P1-T02 已完成；下一步应从 P1-T03 候选股票召回模块开始，继续保持 WIP=1。

### P1-T03 候选股票召回模块

- 状态：done
- 开始时间：2026-06-15 22:32:17 CST
- 完成时间：2026-06-15 22:35:07 CST
- 授权范围：继续推进 P1-T03；允许补充召回模块设计，新增候选召回模型、召回实现和单元测试，并更新 Phase 1 任务进度记录；不实现证据补全、粗排、精排、报告生成、API 或前端；不改依赖、不提交 Git。
- 实际修改：
  - 提交 P1-T02 当前变更，commit 为 `2026cd4 Implement Phase 1 theme fixtures`。
  - 更新 `docs/modules/theme-research-contract.md`，补充 P1-T03 的职责、非职责、建议包结构、召回规则、输出模型和测试策略。
  - 补充 `docs/modules/theme-research-contract.md` 中的 fixture 与真实数据源边界，明确 fixture 不是未来真实股票数据 API 标准，真实数据接入必须通过 adapter 或 mapper 转换为内部研究合同。
  - 更新 `src/astra/theme_research/contracts.py`，新增 `RecallMatch`、`RecalledCandidate` 和 `CandidateRecallResult`。
  - 更新 `src/astra/theme_research/__init__.py`，导出召回模型与召回函数。
  - 新增 `src/astra/theme_research/recall.py`，实现主题查询归一化、fixture 候选召回、来源合并、去重、稳定排序和数量限制。
  - 新增 `tests/unit/theme_research/test_recall.py`，覆盖召回命中、别名命中、无命中、去重和数量限制。
  - 更新 `docs/tasks/phase-1-task-plan.md`，记录 P1-T03 启动、完成、授权范围、实际修改和验证结果。
- 验证结果：
  - `make test-unit` 通过，21 个单元测试通过。
  - 首次 `make check` 失败，原因是新增 import block 未按 ruff 规则排序；已用 ruff 修复。
  - 第二次 `make check` 通过，包含 ruff、22 个后端单元/集成测试、前端 lint、前端 build 和 1 个 Playwright Chromium E2E 测试。
  - `rg` 检查通过，确认 `docs/modules/theme-research-contract.md` 包含 fixture 与真实数据源边界、adapter/mapper 约束和未来数据源规格要求。
  - `rg -n "[ \t]+$" docs/modules/theme-research-contract.md docs/tasks/phase-1-task-plan.md` 未发现尾随空白。
  - `git diff --check` 通过。
- 备注：P1-T03 已完成；下一步应从 P1-T04 股票数据 API 选型与数据源规格开始，继续保持 WIP=1。

### Phase 1 真实股票数据 API 范围调整

- 状态：done
- 开始时间：2026-06-15 22:46:01 CST
- 完成时间：2026-06-15 22:46:01 CST
- 授权范围：用户明确要求真实股票数据 API 应在 Phase 1 中明确并实现，而不是后置到 Phase 2；允许修改 Phase 1 文档、主题研究模块合同和 Phase 1 任务计划；不改代码、不改依赖、不提交 Git。
- 实际修改：
  - 更新 `docs/phases/phase-1-theme-to-pool.md`，将真实股票数据 API 最小接入纳入 Phase 1 阶段目标、范围、数据原则和验收标准。
  - 更新 `docs/modules/theme-research-contract.md`，明确真实股票数据 API 是 Phase 1 必做项，补充最小接入目标、最小字段、候选数据源和 adapter/fixture 降级要求。
  - 更新 `docs/tasks/phase-1-task-plan.md`，新增 P1-T04 到 P1-T06 的数据源选型、adapter 和真实候选召回接入任务，并将原后续任务顺延到 P1-T13。
- 验证结果：
  - `rg` 检查通过，确认 Phase 1 文档、模块合同和任务计划均包含真实股票数据 API、adapter、fixture 降级、P1-T04、P1-T05 和 P1-T06 相关约束。
  - `rg -n "[ \t]+$" docs/phases/phase-1-theme-to-pool.md docs/modules/theme-research-contract.md docs/tasks/phase-1-task-plan.md` 未发现尾随空白。
  - `git diff --check` 通过。
- 备注：该调整不代表 P1-T04 已开始；当前任务为 P1-T04，状态为 not_started。

### Phase 1 模型漏斗范围调整

- 状态：done
- 开始时间：2026-06-15 23:03:44 CST
- 完成时间：2026-06-15 23:03:44 CST
- 授权范围：用户明确要求 Theme-to-Pool 是完整漏斗，不只是召回；粗排和精排必须接大模型且模型规格可以不同；允许修改 Phase 1 文档、主题研究模块合同和 Phase 1 任务计划；不改代码、不改依赖、不提交 Git。
- 实际修改：
  - 更新 `docs/phases/phase-1-theme-to-pool.md`，明确召回是低成本规则/数据源匹配，粗排和精排必须通过模型接口完成，并补充模型原则和验收标准。
  - 更新 `docs/modules/theme-research-contract.md`，补充模型调用边界、`coarse_rank_model_spec`、`deep_rank_model_spec`、`report_generation_model_spec`、结构化输出和 fake/mock model client 测试要求。
  - 更新 `docs/tasks/phase-1-task-plan.md`，将原粗排/精排任务拆为 P1-T08 模型粗排基线和 P1-T09 模型精排基线，并将报告、API、前端、E2E 和总验收顺延到 P1-T14。
- 验证结果：
  - `rg` 检查通过，确认 Phase 1 文档、模块合同和任务计划均包含模型粗排、模型精排、统一模型接口、不同模型规格、结构化输出和 fake/mock model client 测试要求。
  - `rg` 检查通过，确认 P1-T08、P1-T09 和 P1-T14 编号调整已同步到任务计划和模块合同。
  - `rg -n "[ \t]+$" docs/phases/phase-1-theme-to-pool.md docs/modules/theme-research-contract.md docs/tasks/phase-1-task-plan.md` 未发现尾随空白。
  - `git diff --check` 通过。
- 备注：该调整不代表 P1-T08 或 P1-T09 已开始；当前任务仍为 P1-T04，状态为 not_started。

### P1-T04 股票数据 API 选型与数据源规格

- 状态：done
- 开始时间：2026-06-16 22:22:27 CST
- 完成时间：2026-06-16 22:24:26 CST
- 授权范围：进入 P1-T04；用户确认 Phase 1 现阶段使用 AKShare 作为首个真实市场数据源，同时要求为后续其他数据源开放，并确认网页/网络知识搜索应作为独立 evidence provider 方向落 ADR；允许新增 ADR 和更新相关文档；不写业务代码、不改依赖、不提交 Git。
- 实际修改：
  - 新增 `docs/adr/0002-use-akshare-as-phase-1-market-data-provider.md`，确认 Phase 1 使用 AKShare 作为首个 `MarketDataProvider`，并记录最小接入字段、adapter 边界、许可边界、失败降级和测试策略。
  - 新增 `docs/adr/0003-separate-web-knowledge-provider.md`，确认网页与网络知识搜索是独立 `WebKnowledgeProvider` / evidence provider 方向，不混入市场数据 provider。
  - 更新 `docs/modules/theme-research-contract.md`，引用 ADR 0002 和 ADR 0003，并将 AKShare 从候选数据源调整为 Phase 1 首个真实市场数据 provider。
  - 更新 `docs/tasks/phase-1-task-plan.md`，记录 P1-T04 完成，并将当前任务推进到 P1-T05。
- 验证结果：
  - `rg` 检查通过，确认 ADR 0002、ADR 0003、模块合同和任务计划均包含 AKShare、MarketDataProvider、adapter、fixture、P1-T05、WebKnowledgeProvider 和 evidence provider 相关约束。
  - `rg` 检查通过，确认 P1-T04 已标记为 done，当前任务已推进到 P1-T05。
  - `rg -n "[ \t]+$" docs/adr/0002-use-akshare-as-phase-1-market-data-provider.md docs/adr/0003-separate-web-knowledge-provider.md docs/modules/theme-research-contract.md docs/tasks/phase-1-task-plan.md` 未发现尾随空白。
  - `git diff --check` 通过。
- 备注：P1-T04 已完成；下一步应从 P1-T05 股票数据源 adapter 与 fixture 降级开始，继续保持 WIP=1。
  P1-T04 只完成数据源选型和接入规格，不包含代码接入；AKShare provider、raw record、adapter 和 fixture fallback 的实现属于 P1-T05，真实候选召回集成属于 P1-T06。

### P1-T05 股票数据源 adapter 与 fixture 降级

- 状态：done
- 开始时间：2026-06-16 22:29:56 CST
- 完成时间：2026-06-16 22:45:40 CST
- 授权范围：用户要求 commit/push P1-T04 后进入 P1-T05；允许实现市场数据 provider 合同、AKShare provider、provider raw record、adapter、fixture fallback 和单元测试，并更新任务记录；不提前将真实数据源接入候选召回，不实现证据补全、模型粗排、模型精排、报告生成、API 或前端；不提交 Git，除非用户后续明确要求。
- 实际修改：
  - 使用 `uv add 'akshare>=1.16.0'` 将 AKShare 加入项目依赖，当前解析版本为 `akshare==1.18.64`，并更新 `pyproject.toml` 和 `uv.lock`。
  - 更新 `src/astra/theme_research/contracts.py`，新增 `ProviderMetadata`、`StockSourceRecord`、`ConceptConstituentRecord` 和 `MarketDataCompany`，作为 provider 原始记录和内部规范化公司记录。
  - 新增 `src/astra/theme_research/market_data.py`，实现 `MarketDataProvider` 协议、`AkshareMarketDataProvider` 懒加载 provider、`FixtureMarketDataProvider`、`FallbackMarketDataProvider`、字段映射、A 股代码规范化和 provider record 到内部记录的 adapter。
  - 更新 `src/astra/theme_research/__init__.py`，导出 P1-T05 新增合同、provider、adapter 和错误类型。
  - 新增 `tests/unit/theme_research/test_market_data.py`，覆盖 AKShare fake client、字段映射、缺失字段、unsupported exchange、fixture provider 和 primary provider 失败/空结果降级。
  - 新增 `tests/integration/test_akshare_market_data_provider.py`，真实访问 AKShare 并验证 A 股基础数据可拉取、规范化和映射为 ASTRA provider record。
  - 更新 `docs/adr/0002-use-akshare-as-phase-1-market-data-provider.md`，修正测试策略：P1-T05 集成测试必须真实访问 AKShare；fixture fallback 是运行时韧性机制，不是证明真实数据源已接入的测试替代。
  - 更新 `docs/tasks/phase-1-task-plan.md`，记录 P1-T05 启动、完成、授权范围、实际修改和验证结果，并将当前任务推进到 P1-T06。
- 验证结果：
  - 首次 `make test-unit` 失败，原因是 `AkshareMarketDataProvider` 默认参数引用的 `_utc_retrieved_at` 定义顺序晚于类定义；已前移函数定义修复。
  - 第二次 `make test-unit` 通过，30 个单元测试通过。
  - 首次 `uv run ruff check .` 失败，原因是 ruff `UP045` 要求使用 `X | None` 标注；已更新 `market_data.py` 类型标注。
  - 第二次 `uv run ruff check .` 通过。
  - 手工真实调用 `AkshareMarketDataProvider().list_stock_source_records()` 成功，从 AKShare 拉取并映射 5207 条 A 股基础记录，包括 `000001.SZ 平安银行`。
  - `uv run pytest tests/integration/test_akshare_market_data_provider.py -vv` 通过，真实访问 AKShare 并验证 A 股基础数据拉取、代码规范化和 provider 元信息。
  - `make check` 通过，包含 ruff、32 个后端单元/集成测试、前端 lint、前端 build 和 1 个 Playwright Chromium E2E 测试；其中 1 个集成测试真实访问 AKShare。
- 备注：P1-T05 已完成；真实候选召回集成留给 P1-T06。当前环境下手工调用 AKShare 东方财富概念成分接口 `stock_board_concept_cons_em` 遇到上游 `ProxyError`，P1-T06 需要为真实主题/概念召回评估可用的 AKShare 概念、行业或替代接口。

### P1-T06 真实候选召回接入

- 状态：done
- 开始时间：2026-06-29
- 完成时间：2026-06-29 11:36:12 CST
- 授权范围：用户确认进入 P1-T06；允许实现真实数据源接入候选召回模块、统一召回候选模型、AKShare 概念板块发现、fixture fallback、单元测试和真实 AKShare 集成测试，并更新任务记录；不实现证据补全、模型粗排、模型精排、报告生成、API 或前端；不提交 Git，除非用户后续明确要求。
- 已确认取舍：
  - P1-T06 只做确定性真实数据源候选召回，不做主题语义扩展。
  - 统一 fixture 与真实 provider 的召回候选输出形态。
  - 真实召回主路径采用 AKShare 概念板块，不把行业接口作为第一优先级。
  - 行业接口未作为 P1-T06 主路径的原因：`低空经济`、`飞行汽车(eVTOL)`、`无人机` 更符合概念/主题板块语义，而不是标准行业分类；本轮真实探测中概念列表和概念成分接口可匹配并返回真实成分股，行业成分接口对这些主题基本返回 `IndexError`，东方财富行业列表还出现过 `RemoteDisconnected`；行业字段更适合留到 P1-T07 证据补全或后续明确的主题到行业映射层中使用。
- 实际修改：
  - 更新 `src/astra/theme_research/contracts.py`，新增 `ConceptBoardRecord`，将 `RecalledCandidate.company` 调整为统一的 `MarketDataCompany`，并保留 `fixture_company` 作为 fixture 证据接力字段。
  - 更新 `src/astra/theme_research/market_data.py`，新增 provider 概念板块发现接口 `list_concept_boards()`，实现 AKShare、fixture 和 fallback provider 的概念板块记录映射。
  - 更新 `src/astra/theme_research/recall.py`，新增 `recall_candidates_from_provider()`，支持概念板块发现、真实概念成分召回、去重、排序、`max_candidates` 和 fixture fallback。
  - 更新 `src/astra/theme_research/__init__.py`，导出 P1-T06 新增合同、adapter 和召回入口。
  - 更新 `tests/unit/theme_research/test_market_data.py`，覆盖概念板块字段映射、fake AKShare、fixture provider 和 fallback provider。
  - 更新 `tests/unit/theme_research/test_recall.py`，覆盖真实 provider 召回成功、概念板块匹配、去重、数量限制、provider 失败 fallback 和无 fallback 空结果。
  - 更新 `tests/integration/test_akshare_market_data_provider.py`，新增真实 AKShare `低空经济` 概念板块召回集成测试。
  - 更新 `docs/tasks/phase-1-task-plan.md`，记录 P1-T06 启动、完成、授权范围、实际修改和验证结果，并将当前任务推进到 P1-T07。
- 验证结果：
  - `uv run pytest tests/unit/theme_research -q` 通过，34 个主题研究单元测试通过。
  - `uv run ruff check .` 通过。
  - `uv run pytest tests/integration/test_akshare_market_data_provider.py -vv` 通过，2 个真实 AKShare 集成测试通过；其中新增测试真实访问 AKShare 概念板块和成分股接口，验证 `低空经济` provider-backed recall 返回真实 provider 候选，不使用 fixture fallback。
  - `make check` 通过，包含 ruff、38 个后端单元/集成测试、前端 lint、前端 build 和 1 个 Playwright Chromium E2E 测试；其中 2 个集成测试真实访问 AKShare。
- 备注：P1-T06 已完成；真实召回主路径依赖 AKShare 东方财富概念板块接口。该接口本轮验证可用，但仍可能受网络、上游公开接口变更或临时断连影响。行业接口本轮未作为主路径接入。
  行业接口不进入主路径不代表永久放弃；它后续可用于候选公司的行业字段补充、证据交叉验证或更明确的行业映射能力。

### P1-T07 证据补全模块

- 状态：done
- 开始时间：2026-06-30 11:26:52 CST
- 完成时间：2026-06-30 14:20:49 CST
- 授权范围：用户确认进入 P1-T07；允许实现候选公司证据补全合同、MarketDataProvider + fixture 主路径、AKShare 可用字段探测与窄路径真实集成测试，并更新任务记录；不接入真实网页、新闻、公告搜索主路径，不实现模型粗排、模型精排、报告生成、API 或前端；不提交 Git，除非用户后续明确要求。
- 已确认取舍：
  - P1-T07 不把真实网页、新闻、公告搜索作为主路径，只为后续 `WebKnowledgeProvider` 预留扩展口。
  - 主路径使用 `MarketDataProvider` 与 fixture 证据补全；AKShare 能稳定获取的字段才接入，无法获取的字段必须显式记录缺失、失败或边界，不编造摘要。
  - 行业数据只作为证据补全字段和交叉验证，不参与候选召回。
  - 新增证据补全中间合同，避免在 P1-T07 强行填充 P1-T08/P1-T09 才产生的分数、排名和最终入选理由。
  - 证据来源类型需要支持结构化市场数据来源，避免把 AKShare 数据误标为公告、新闻或研报。
  - 单元测试使用 fake/fixture 保持稳定；真实 AKShare 集成测试仅覆盖窄路径 smoke test，并明确 live network 风险。
- 实际修改：
  - 更新 `src/astra/theme_research/contracts.py`，新增 `BusinessProfileRecord`、`FinancialSnapshotRecord`、`EvidencePackage`、`EnrichedCandidate` 和 `EvidenceEnrichmentResult`，并新增 `market_data_provider` 证据来源类型。
  - 更新 `src/astra/theme_research/market_data.py`，为 `MarketDataProvider` 增加主营业务资料和财务摘要快照接口，实现 AKShare、fixture 和 fallback provider 映射；AKShare 主营业务使用 `stock_zyjs_ths`，财务摘要使用 `stock_financial_abstract`。
  - 新增 `src/astra/theme_research/evidence.py`，实现 `enrich_recalled_candidate()` 和 `enrich_recalled_candidates()`，支持 fixture 证据合并、provider 证据生成、缺失证据记录、数据边界和 warning。
  - 更新 `src/astra/theme_research/__init__.py`，导出 P1-T07 新增合同、adapter 和证据补全入口。
  - 更新 `tests/unit/theme_research/test_market_data.py`，覆盖主营业务资料、财务摘要、fixture provider 和 fallback provider 映射。
  - 新增 `tests/unit/theme_research/test_evidence.py`，覆盖 fixture 完整证据包、provider 证据来源、provider 失败和缺失证据记录。
  - 更新 `tests/integration/test_akshare_market_data_provider.py`，新增真实 AKShare 证据补全 smoke test，验证 `stock_zyjs_ths` 和 `stock_financial_abstract` 能生成业务与财务证据。
  - 更新 `docs/modules/theme-research-contract.md` 和 `docs/adr/0002-use-akshare-as-phase-1-market-data-provider.md`，记录 P1-T07 的合同、边界、AKShare 接口取舍和缺失证据处理。
- 验证结果：
  - `uv run ruff check .` 通过。
  - `uv run pytest tests/unit/theme_research -q` 通过，39 个主题研究单元测试通过。
  - `uv run pytest tests/unit -q` 通过，40 个后端单元测试通过。
  - `uv run pytest tests/integration/test_akshare_market_data_provider.py::test_live_akshare_provider_evidence_enrichment_returns_core_evidence -vv` 通过，真实访问 AKShare `stock_zyjs_ths` 和 `stock_financial_abstract`，验证 P1-T07 主营业务与财务摘要证据补全路径可用。
  - `uv run pytest tests/integration/test_akshare_market_data_provider.py -vv` 失败：3 个集成用例中 2 个通过，既有 P1-T06 `test_live_akshare_low_altitude_concept_recall_returns_candidates` 失败。失败原因是 AKShare 东方财富概念接口 `stock_board_concept_name_em` 和 `stock_board_concept_cons_em` 当前真实返回 `RemoteDisconnected`，候选召回走了 fixture fallback，因此未满足该用例要求的真实概念板块命中。
  - `make check` 失败：ruff 通过，43 个后端测试通过，1 个集成测试失败，1 个 `StarletteDeprecationWarning`；前端 lint/build/Playwright 未执行到，因为后端 pytest 阶段已失败。
- 后续验收风险：用户确认 AKShare 东方财富概念接口断连问题先搁置，继续后续任务执行。P1-T07 自身实现、单元测试和新增真实 AKShare 证据补全 smoke test 已完成；但 Phase 级 `make check` 仍可能被既有 P1-T06 真实概念召回集成测试阻塞。直接真实探测确认 `stock_board_concept_name_em` 和 `stock_board_concept_cons_em("低空经济")` 当前均返回 `RemoteDisconnected`。

### P1-T08 模型粗排基线

- 状态：done
- 开始时间：2026-06-30 14:20:49 CST
- 完成时间：2026-06-30 14:27:19 CST
- 授权范围：用户确认后续任务由 Agent 持续执行，仅在遇到卡点或需要用户确认时暂停；允许实现 P1-T08 模型粗排合同、fake model client、结构化输出校验、过滤规则和单元测试，并更新任务记录；不实现模型精排、报告生成、API 或前端；不调用真实模型 API；不提交 Git，除非用户后续明确要求。
- 实际修改：
  - 更新 `src/astra/theme_research/contracts.py`，新增 `ModelSpec`、`CoarseRankDecision`、`CoarseRankedCandidate` 和 `CoarseRankResult`。
  - 新增 `src/astra/theme_research/coarse_rank.py`，实现统一 `ModelClient.generate_structured()` 协议、`FakeCoarseRankModelClient`、粗排执行、结构化输出校验、证据 ID 引用校验、交易指令拦截和最小保留阈值过滤。
  - 更新 `src/astra/theme_research/__init__.py`，导出 P1-T08 新增合同、fake model client、错误类型和粗排入口。
  - 新增 `tests/unit/theme_research/test_coarse_rank.py`，覆盖 fake model client、强/弱候选保留过滤、schema 校验失败、未知证据引用、交易指令拦截和低分阈值过滤。
  - 更新 `docs/modules/theme-research-contract.md`，记录 P1-T08 的职责、非职责、输出模型、fake model client、过滤与安全规则和测试策略。
- 验证结果：
  - `uv run pytest tests/unit/theme_research -q` 通过，45 个主题研究单元测试通过。
  - `uv run pytest tests/unit -q` 通过，46 个后端单元测试通过。
  - `uv run ruff check .` 通过。
- 后续验收风险：P1-T08 未调用真实模型 API，自动化测试使用固定 fake model client，符合 Phase 1 模型测试边界。Phase 级 `make check` 仍可能被 P1-T06 真实 AKShare 东方财富概念接口 `RemoteDisconnected` 问题阻塞。

### P1-T09 模型精排基线

- 状态：done
- 开始时间：2026-06-30 14:27:19 CST
- 完成时间：2026-06-30 14:32:06 CST
- 授权范围：用户确认后续任务由 Agent 持续执行，仅在遇到卡点或需要用户确认时暂停；允许实现 P1-T09 模型精排合同、fake model client、最终排序、证据引用、风险输出、交易指令拦截和单元测试，并更新任务记录；不实现报告生成、API 或前端；不调用真实模型 API；不提交 Git，除非用户后续明确要求。
- 实际修改：
  - 更新 `src/astra/theme_research/contracts.py`，新增 `DeepRankDecision`、`DeepRankedCandidate` 和 `DeepRankResult`。
  - 新增 `src/astra/theme_research/deep_rank.py`，实现 `FakeDeepRankModelClient`、精排执行、仅精排粗排保留候选、最终排序、rank 分配、结构化输出校验、证据 ID 引用校验和交易指令拦截。
  - 更新 `src/astra/theme_research/__init__.py`，导出 P1-T09 新增合同、fake model client 和精排入口。
  - 新增 `tests/unit/theme_research/test_deep_rank.py`，覆盖 fake deep rank、最终排序、过滤候选排除、`max_results`、schema 校验失败、未知证据引用和交易指令拦截。
  - 更新 `docs/modules/theme-research-contract.md`，记录 P1-T09 的职责、非职责、输出模型、fake model client、排序与安全规则和测试策略。
- 验证结果：
  - `uv run pytest tests/unit/theme_research -q` 通过，51 个主题研究单元测试通过。
  - `uv run pytest tests/unit -q` 通过，52 个后端单元测试通过。
  - `uv run ruff check .` 通过。
- 后续验收风险：P1-T09 未调用真实模型 API，自动化测试使用固定 fake model client，符合 Phase 1 模型测试边界。Phase 级 `make check` 仍可能被 P1-T06 真实 AKShare 东方财富概念接口 `RemoteDisconnected` 问题阻塞。

### P1-T10 研究报告生成基线

- 状态：done
- 开始时间：2026-06-30 14:32:06 CST
- 完成时间：2026-06-30 14:38:13 CST
- 授权范围：用户确认后续任务由 Agent 持续执行，仅在遇到卡点或需要用户确认时暂停；允许实现 P1-T10 研究报告生成合同映射、基于精排结果的结构化报告、风险提示、证据边界、非投资建议说明和单元测试，并更新任务记录；不实现 API 或前端；不调用真实模型 API；不提交 Git，除非用户后续明确要求。
- 实际修改：
  - 新增 `src/astra/theme_research/report.py`，实现 `REPORT_GENERATION_MODEL_SPEC`、报告 schema 名称、`FakeReportGenerationModelClient`、`generate_theme_research_result()`、股票池映射、结构化报告校验、证据 ID 引用校验和交易指令拦截。
  - 更新 `src/astra/theme_research/__init__.py`，导出 P1-T10 报告生成规格、fake model client 和报告生成入口。
  - 新增 `tests/unit/theme_research/test_report.py`，覆盖报告生成、股票池映射、重点公司证据引用、schema 校验失败、未知证据引用和交易指令拦截。
  - 更新 `docs/modules/theme-research-contract.md`，记录 P1-T10 的职责、非职责、输出与安全规则、fake model client 和测试策略。
- 验证结果：
  - 首次 `uv run ruff check .` 失败，原因是 `src/astra/theme_research/report.py` import block 未排序；已用 ruff 自动修复。
  - `uv run pytest tests/unit/theme_research -q` 通过，56 个主题研究单元测试通过。
  - `uv run pytest tests/unit -q` 通过，57 个后端单元测试通过。
  - `uv run ruff check .` 通过。
- 后续验收风险：P1-T10 未调用真实模型 API，自动化测试使用固定 fake model client，符合 Phase 1 模型测试边界。Phase 级 `make check` 仍可能被 P1-T06 真实 AKShare 东方财富概念接口 `RemoteDisconnected` 问题阻塞。

### P1-T11 主题研究 API

- 状态：done
- 开始时间：2026-06-30 14:38:13 CST
- 完成时间：2026-06-30 14:42:29 CST
- 授权范围：用户确认后续任务由 Agent 持续执行，仅在遇到卡点或需要用户确认时暂停；允许实现 P1-T11 主题研究后端 API、请求校验、成功响应、无结果和错误输入路径、集成测试，并更新任务记录；不实现前端页面或 Playwright E2E；不调用真实模型 API；真实 AKShare 概念接口断连问题本轮先搁置，不作为 P1-T11 主路径阻塞；不提交 Git，除非用户后续明确要求。
- 实际修改：
  - 新增 `src/astra/theme_research/service.py`，实现 fixture-backed `run_theme_research()` 应用服务，串联候选召回、证据补全、粗排、精排和报告生成，并支持 `include_report=false`。
  - 更新 `src/astra/theme_research/report.py`，暴露 `candidate_stock_from_deep_ranked()`，供无报告响应复用股票池映射。
  - 更新 `src/astra/theme_research/__init__.py`，导出 P1-T11 应用服务和股票池映射入口。
  - 更新 `src/astra/api/app.py`，新增 `POST /api/theme-research`，返回 `ThemeResearchResponse` 或结构化 `ThemeResearchErrorResponse`。
  - 新增 `tests/integration/test_theme_research_api.py`，覆盖成功响应、`include_report=false`、无候选、空主题和非 `cn_a` 市场错误。
  - 更新 `docs/modules/theme-research-contract.md`，记录 P1-T11 的职责、非职责、API 行为和测试策略。
- 验证结果：
  - `uv run pytest tests/integration/test_theme_research_api.py -q` 通过，5 个 P1-T11 API 集成测试通过；出现 1 个既有 `StarletteDeprecationWarning`。
  - `uv run pytest tests/integration/test_theme_research_api.py tests/integration/test_health_api.py -q` 通过，6 个 API 集成测试通过；出现 1 个既有 `StarletteDeprecationWarning`。
  - `uv run pytest tests/unit/theme_research -q` 通过，56 个主题研究单元测试通过。
  - `uv run pytest tests/unit -q` 通过，57 个后端单元测试通过。
  - `uv run ruff check .` 通过。
- 后续验收风险：P1-T11 主路径没有访问真实 AKShare，也没有调用真实模型 API，使用固定 fixture 和 fake model client 保障 API 集成测试稳定。Phase 级 `make check` 仍可能被 P1-T06 真实 AKShare 东方财富概念接口 `RemoteDisconnected` 问题阻塞。

### P1-T12 主题研究前端页面

- 状态：done
- 开始时间：2026-06-30 14:42:29 CST
- 完成时间：2026-06-30 14:46:18 CST
- 授权范围：用户确认后续任务由 Agent 持续执行，仅在遇到卡点或需要用户确认时暂停；允许实现 P1-T12 前端主题研究页面、API 调用、股票池展示、报告展示、加载状态和错误状态，并更新任务记录；不实现 Playwright E2E；不调用真实模型 API；真实 AKShare 概念接口断连问题本轮先搁置，不作为 P1-T12 主路径阻塞；不提交 Git，除非用户后续明确要求。
- 实际修改：
  - 更新 `frontend/src/App.tsx`，将前端首屏从健康检查页改为主题研究工作台，支持主题输入、结果数、报告开关、API 调用、加载状态、错误状态、股票池展示、研究报告展示和 pipeline 展示。
  - 更新 `frontend/src/styles.css`，实现响应式工作台布局、查询表单、股票卡片、报告区域、pipeline 和错误/加载状态样式。
  - 更新 `docs/modules/theme-research-contract.md`，记录 P1-T12 的职责、非职责、前端状态和测试策略。
- 验证结果：
  - `cd frontend && npm run lint` 通过。
  - `cd frontend && npm run build` 通过，Vite production build 成功。
  - 构建产物 `frontend/dist/` 已被 `.gitignore` 忽略。
- 后续验收风险：P1-T12 前端只调用 P1-T11 fixture-backed API，不直接访问真实 AKShare，也不调用真实模型 API。Phase 级 `make check` 仍可能被 P1-T06 真实 AKShare 东方财富概念接口 `RemoteDisconnected` 问题阻塞。

### P1-T13 主题研究端到端测试

- 状态：done
- 开始时间：2026-06-30 14:46:18 CST
- 完成时间：2026-06-30 14:50:14 CST
- 授权范围：用户确认后续任务由 Agent 持续执行，仅在遇到卡点或需要用户确认时暂停；允许实现 P1-T13 Playwright 端到端测试，覆盖成功主题研究、股票池展示、研究报告展示和错误状态，并更新任务记录；不修复 P1-T06 真实 AKShare 概念接口断连问题；不提交 Git，除非用户后续明确要求。
- 实际修改：
  - 删除旧的 `frontend/tests/e2e/health.spec.ts` health-only smoke test。
  - 新增 `frontend/tests/e2e/theme-research.spec.ts`，覆盖 `低空经济` 成功主题研究流程、股票池展示、研究报告展示、非投资建议说明、`report_generation` pipeline 和无候选错误状态。
  - 更新 `frontend/playwright.config.ts`，后端 webServer 启动优先使用本地 `.venv/bin/python -m uvicorn`，无本地 venv 时回退到 `uv run uvicorn`。
  - 更新 `docs/modules/theme-research-contract.md`，记录 P1-T13 的职责、非职责和测试策略。
- 验证结果：
  - 首次 `cd frontend && npm run test:e2e` 失败，后端 webServer 启动时 `uv` 在 `system-configuration` 依赖中 panic，测试未进入浏览器断言；已调整 Playwright 后端启动命令优先使用本地 `.venv/bin/python -m uvicorn`。
  - 第二次 `cd frontend && npm run test:e2e` 失败，原因是沙盒禁止绑定 `127.0.0.1:8000`；随后使用提升权限复跑。
  - 提升权限后首次 E2E 进入浏览器断言，但失败于 Playwright selector 过宽；已收紧为 role/exact selector。
  - 最终 `cd frontend && npm run test:e2e` 通过，2 个 Chromium E2E 测试通过，覆盖成功主题研究和无候选错误状态；命令输出包含 Node `NO_COLOR`/`FORCE_COLOR` warning，不影响结果。
  - `cd frontend && npm run lint` 通过。
  - `cd frontend && npm run build` 通过。
- 后续验收风险：P1-T13 E2E 使用本地 fixture-backed API 和 fake model client，没有访问真实 AKShare，也没有调用真实模型 API。Phase 级 `make check` 仍可能被 P1-T06 真实 AKShare 东方财富概念接口 `RemoteDisconnected` 问题阻塞。

### P1-T14 Phase 1 总验收

- 状态：blocked
- 开始时间：2026-06-30 14:50:14 CST
- 授权范围：用户确认后续任务由 Agent 持续执行，仅在遇到卡点或需要用户确认时暂停；允许执行 Phase 1 总验收、运行 `make check` 和必要的分项验证、记录验收结果与未解决风险；不修复已明确搁置的 P1-T06 真实 AKShare 概念接口断连问题，除非用户重新授权；不提交 Git，除非用户后续明确要求。
- 阻塞时间：2026-06-30 14:52:02 CST
- 已完成分项验证：
  - P1-T10：`uv run pytest tests/unit/theme_research -q` 通过，56 个主题研究单元测试通过。
  - P1-T10/P1-T11：`uv run pytest tests/unit -q` 通过，57 个后端单元测试通过。
  - P1-T11：`uv run pytest tests/integration/test_theme_research_api.py tests/integration/test_health_api.py -q` 通过，6 个 API 集成测试通过；出现 1 个既有 `StarletteDeprecationWarning`。
  - P1-T12/P1-T13：`cd frontend && npm run lint` 通过。
  - P1-T12/P1-T13：`cd frontend && npm run build` 通过。
  - P1-T13：`cd frontend && npm run test:e2e` 通过，2 个 Chromium E2E 测试通过；命令输出包含 Node `NO_COLOR`/`FORCE_COLOR` warning，不影响结果。
- 总验收结果：
  - `make check` 失败，未达到 Phase 1 完成标准。
  - `make check` 中 `uv run ruff check .` 通过。
  - `make check` 中后端 pytest 收集 66 个测试，结果为 65 passed、1 failed、1 warning。
  - 失败用例为 `tests/integration/test_akshare_market_data_provider.py::test_live_akshare_low_altitude_concept_recall_returns_candidates`。
  - 失败原因：真实 AKShare 东方财富概念接口当前返回 `RemoteDisconnected('Remote end closed connection without response')`，真实概念板块召回未命中 `低空经济`，运行时进入 fixture fallback，因此未满足该 live test 对真实 provider-backed recall 的断言。
  - 因后端 pytest 阶段失败，`make check` 未继续执行前端 lint/build/Playwright；这些前端分项已在 P1-T12/P1-T13 单独通过。
- 当前 blocker：用户已确认 AKShare 概念接口问题本轮先搁置；在该 blocker 未解除或验收策略未重新授权调整前，P1-T14 不能标记为 done，Phase 1 也不能声明完成。
