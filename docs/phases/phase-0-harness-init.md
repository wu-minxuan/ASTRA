# Phase 0：Harness 初始化

Phase 0 的目标是在 ASTRA 进入业务功能开发前，完成仓库级初始化，让后续 Agent 会话能够只依赖仓库内容完成启动、理解、运行、测试和接手下一步。

Phase 0 不追求业务能力落地。它的产出是后续开发的执行前提：项目文档、可运行环境、测试框架、最小前后端闭环、统一命令入口和初始任务分解。

## 阶段目标

Phase 0 需要让 ASTRA 仓库满足以下条件：

- 能理解：新会话能从仓库中理解 ASTRA 是什么、当前阶段是什么、后续如何推进。
- 能启动：项目环境、依赖管理、开发服务和基础命令已经明确。
- 能测试：测试框架已经配置，至少有后端示例测试和浏览器端到端测试。
- 能验证：最小前后端闭环可以通过自动化测试验证。
- 能接手：后续任务可以按 WIP=1 从任务规格开始推进。

## 阶段范围

Phase 0 包括：

- 建立 Agent 协作入口与项目愿景文档。
- 建立 Phase 文档、任务模板和 ADR 记录方式。
- 初始化 Python 后端项目结构。
- 初始化 Vite React TypeScript 前端项目结构。
- 建立 FastAPI 最小服务。
- 建立前端最小页面。
- 建立前后端开发代理。
- 建立统一 Makefile 命令入口。
- 配置静态检查、单元测试、集成测试和端到端测试基础。
- 使用 Playwright 跑通浏览器端到端测试。
- 增加 README 作为人类开发入口。
- 拆分 Phase 1 的第一批原子任务。

## 非范围

Phase 0 不包括：

- 实现 Theme-to-Pool 业务功能。
- 接入真实行情、财务、公告、研报或新闻数据。
- 构建正式数据库、数据仓库或特征平台。
- 实现 Agent 调度框架。
- 实现回测、模拟盘或交易系统。
- 选择或部署生产模型。
- 构建完整 Web UI 或设计系统。
- 进行真实投资推荐或交易决策。

## 技术栈决策

Phase 0 采用以下技术栈：

- Python 后端优先。
- `uv` 作为 Python 项目与依赖管理工具。
- `FastAPI` 作为后端 API 框架。
- `pydantic` 作为数据模型基础。
- `pytest` 作为后端测试入口。
- `ruff` 作为 Python 静态检查工具。
- `Makefile` 作为统一命令入口。
- `Vite + React + TypeScript` 作为前端基础栈。
- `eslint` 作为 TypeScript 静态检查工具。
- `Playwright` 作为浏览器端到端测试工具。
- Codex Browser 插件作为真实浏览器交互验证补充。

## 项目结构

Phase 0 采用单仓库结构：

```text
AGENTS.md
README.md
Makefile
pyproject.toml
uv.lock
docs/
  vision.md
  phases/
  harness/
  adr/
  modules/
  evaluation/
  tasks/
src/
  astra/
    __init__.py
    api/
      app.py
tests/
  unit/
  integration/
frontend/
  package.json
  vite.config.ts
  playwright.config.ts
  src/
  tests/
    e2e/
```

该结构是 Phase 0 的初始化目标。后续可以根据实际演进调整，但调整需要通过任务规格或 ADR 记录。

## 最小前后端闭环

Phase 0 需要实现最小前后端功能闭环。

后端提供：

```text
GET /api/health
```

返回：

```json
{
  "status": "ok",
  "service": "astra"
}
```

前端页面需要：

- 显示 `ASTRA`
- 请求 `/api/health`
- 展示后端状态
- 在请求失败时展示错误状态

前后端开发模式采用分开启动：

- 后端运行在 `http://127.0.0.1:8000`
- 前端运行在 `http://127.0.0.1:5173`
- Vite 通过 proxy 将 `/api` 请求转发到 FastAPI 后端

## 命令入口

Phase 0 需要提供以下 Makefile 命令：

```text
make setup
make test
make test-unit
make test-integration
make test-e2e
make check
make dev-backend
make dev-frontend
```

命令含义：

- `make setup`：安装后端和前端依赖，包括 Playwright 浏览器。
- `make test`：运行后端测试。
- `make test-unit`：运行后端单元测试。
- `make test-integration`：运行后端集成测试。
- `make test-e2e`：运行 Playwright 浏览器端到端测试。
- `make check`：运行静态检查、后端测试和端到端测试。
- `make dev-backend`：启动 FastAPI 后端开发服务。
- `make dev-frontend`：启动 Vite 前端开发服务。

## 测试与验证

ASTRA 项目的验证类型固定为：

- 静态检查
- 单元测试
- 集成测试
- 端到端测试

Phase 0 的测试要求：

- `pytest` 能运行后端测试。
- 后端至少有一个单元测试。
- 后端至少有一个 API 集成测试。
- `ruff` 能完成 Python 静态检查。
- `eslint` 能完成前端静态检查。
- `Playwright` 能完成浏览器端到端测试。
- 浏览器端到端测试应验证前端能打开，并能展示后端 `/api/health` 的状态。

## 交付物

Phase 0 的交付物包括：

- `AGENTS.md`
- `README.md`
- `docs/vision.md`
- `docs/phases/phase-0-harness-init.md`
- `docs/phases/phase-1-theme-to-pool.md`
- `docs/harness/task-template.md`
- `docs/adr/README.md`
- Python 后端项目骨架
- Vite React TypeScript 前端项目骨架
- FastAPI `/api/health`
- 前端 health 页面
- Makefile 统一命令入口
- pytest 测试框架
- ruff 静态检查配置
- eslint 静态检查配置
- Playwright 浏览器端到端测试框架
- Phase 1 初始任务分解

## 验收标准

Phase 0 完成时，必须满足：

- 新 Agent 能从仓库中理解项目愿景、当前阶段和协作规则。
- 新开发者能从 README 中知道如何安装、启动和测试项目。
- `make setup` 能完成依赖安装。
- `make dev-backend` 能启动后端服务。
- `make dev-frontend` 能启动前端服务。
- `make test` 能通过后端测试。
- `make test-e2e` 能通过浏览器端到端测试。
- `make check` 能完成静态检查、后端测试和端到端测试。
- 前端页面能通过 `/api/health` 展示后端状态。
- Phase 1 的目标、范围、非范围和初始任务已经明确。
- 后续任务可以按照 WIP=1 从任务规格开始推进。

## 进入 Phase 1 的条件

只有在 Phase 0 验收标准满足后，项目才进入 Phase 1。

进入 Phase 1 时，应已经明确：

- Phase 1 要解决的具体研究闭环。
- Phase 1 不解决哪些问题。
- Phase 1 的核心模块边界。
- Phase 1 的最小端到端验证方式。
- Phase 1 的第一批原子任务。
