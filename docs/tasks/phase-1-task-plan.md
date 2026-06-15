# Phase 1 任务计划与进度

本文档记录 Phase 1 主题到股票池研究漏斗阶段的任务拆分、执行顺序和进度状态。

## 任务状态说明

- `not_started`：尚未开始。
- `in_progress`：正在执行。
- `blocked`：被外部条件、授权、依赖或设计问题阻塞。
- `done`：已完成并完成对应验证或交接。

## 当前状态

- 当前阶段：Phase 1 主题到股票池研究漏斗
- 当前任务：P1-T02 后端领域模型与固定样例数据
- 当前状态：done

## 任务列表

| ID | 任务 | 状态 | 目标 | 验证/完成标准 |
| --- | --- | --- | --- | --- |
| P1-T01 | 研究合同与样例数据规格 | done | 定义主题研究请求、股票池结果、研究报告和固定样例数据规格 | 文档落盘，明确输入输出、样例主题和验收口径 |
| P1-T02 | 后端领域模型与固定样例数据 | done | 实现主题研究相关领域模型和可复现 fixture 数据 | 单元测试通过，样例数据可被测试稳定加载 |
| P1-T03 | 候选股票召回模块 | not_started | 基于主题和样例数据召回候选 A 股公司 | 单元测试覆盖召回命中、无命中和去重逻辑 |
| P1-T04 | 证据补全模块 | not_started | 为候选公司补充概念、行业、基本面、财务和文本证据摘要 | 单元测试覆盖证据合并、缺失字段和来源保留 |
| P1-T05 | 粗排与精排基线 | not_started | 建立可解释的两段排序基线，输出分数、排名和理由 | 单元测试覆盖排序稳定性、并列分数和过滤规则 |
| P1-T06 | 研究报告生成基线 | not_started | 基于股票池和证据生成结构化研究报告 | 单元测试覆盖报告结构、风险提示和证据边界 |
| P1-T07 | 主题研究 API | not_started | 提供前端可调用的主题研究接口 | 集成测试覆盖成功、无结果和错误输入 |
| P1-T08 | 主题研究前端页面 | not_started | 支持输入主题、查看股票池、查看研究报告和错误状态 | 前端 lint/build 通过，页面状态可手工或自动验证 |
| P1-T09 | 主题研究端到端测试 | not_started | 使用 Playwright 验证完整主题研究流程 | E2E 覆盖输入主题、展示股票池、展示报告和错误状态 |
| P1-T10 | Phase 1 总验收 | not_started | 对照 Phase 1 验收标准收尾 | `make check` 通过并形成完成报告 |

## 执行原则

- 一次只推进一个任务，保持 WIP=1。
- 每个任务开始前先确认允许修改范围。
- 每个任务完成后更新本文件中的状态和执行记录。
- 如果任务发现阶段边界或验收标准不合理，应先讨论并更新文档，再继续实现。
- Phase 1 的最小验收依赖固定样例数据，不依赖不可控外部数据源。

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
