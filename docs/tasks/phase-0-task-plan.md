# Phase 0 任务计划与进度

本文档记录 Phase 0 Harness 初始化阶段的任务拆分、执行顺序和进度状态。

## 任务状态说明

- `not_started`：尚未开始。
- `in_progress`：正在执行。
- `blocked`：被外部条件、授权、依赖或设计问题阻塞。
- `done`：已完成并完成对应验证或交接。

## 当前状态

- 当前阶段：Phase 0 Harness 初始化
- 当前任务：P0-T07 Phase 0 总验收
- 当前状态：done

## 任务列表

| ID | 任务 | 状态 | 目标 | 验证/完成标准 |
| --- | --- | --- | --- | --- |
| P0-T01 | 仓库与环境只读预检 | done | 确认当前文件与本地工具状态 | 输出环境报告，不改变项目状态 |
| P0-T02 | 后端骨架初始化 | done | 建立 uv + FastAPI + pytest + ruff 后端基础 | pytest 与 ruff 通过 |
| P0-T03 | 前端骨架初始化 | done | 建立 Vite + React + TypeScript + eslint 前端基础 | 前端 lint 通过，页面能展示 health 状态 |
| P0-T04 | Playwright E2E 跑通 | done | 配置浏览器端到端测试 | Playwright 验证 ASTRA 页面和后端 ok 状态 |
| P0-T05 | 统一命令入口收敛 | done | 完成 Makefile 命令 | make test、make test-e2e、make check 可运行 |
| P0-T06 | 剩余 Harness 文档补齐 | done | 补齐 README、任务模板、ADR README 等 | 文档落盘并符合已确认边界 |
| P0-T07 | Phase 0 总验收 | done | 对照 Phase 0 验收标准收尾 | make check 通过并形成完成报告 |

## 执行记录

### P0-T01 仓库与环境只读预检

- 状态：done
- 开始时间：2026-06-14
- 完成时间：2026-06-14 15:59:25 CST
- 授权范围：只读预检；不修改文件、不安装依赖、不执行会改变项目状态的命令。
- 实际修改：无。
- 验证结果：
  - 当前目录为 `/Users/wuminxuan/ASTRA`。
  - 当前项目文件为 `AGENTS.md`、`docs/vision.md`、`docs/phases/phase-0-harness-init.md`、`docs/tasks/phase-0-task-plan.md`。
  - `python3` 可用，版本为 `3.9.6`；`python` 命令不可用。
  - `uv` 当前不可用。
  - Node 可用，版本为 `v23.11.0`。
  - npm 可用，版本为 `10.9.2`。
  - Make 可用，版本为 GNU Make `3.81`。
  - Git 可用，版本为 `2.50.1`。
  - 全局 `pytest`、`ruff`、`playwright`、`tsc`、`eslint` 当前不可用，后续应由项目依赖提供。
- 备注：P0-T02 需要处理后端骨架初始化；`uv` 当前未安装，后续执行依赖安装或锁文件生成时需要单独授权。

### P0-T02 后端骨架初始化

- 状态：done
- 开始时间：2026-06-14 16:00:55 CST
- 完成时间：2026-06-14 16:21:39 CST
- 授权范围：创建后端骨架、`pyproject.toml`、`src/astra/`、后端 health API、pytest/ruff 配置、后端测试和初版 `Makefile`；安装 `uv` 并同步后端依赖；不做前端、不提交 Git。
- 实际修改：
  - 新增 `.gitignore`。
  - 新增 `pyproject.toml`。
  - 新增 `Makefile`。
  - 新增 `uv.lock`。
  - 新增 `.venv/` 本地虚拟环境。
  - 新增 `src/astra/__init__.py`。
  - 新增 `src/astra/api/__init__.py`。
  - 新增 `src/astra/api/app.py`。
  - 新增 `tests/unit/test_health_response.py`。
  - 新增 `tests/integration/test_health_api.py`。
  - 安装 `uv` 到当前用户 Python 环境。
  - 更新 `~/.zprofile` 和 `~/.zshrc`，将 `/Users/wuminxuan/Library/Python/3.9/bin` 加入 PATH。
  - 更新 `Makefile`，使用通用的 `UV ?= uv`，并提供 `check-uv` 前置检查。
  - 更新 `Makefile`，将 `UV_CACHE_DIR` 默认设置为仓库内 `.uv-cache/`，避免依赖用户 home cache 权限。
- 验证结果：
  - `make setup` 通过，已创建 `.venv/` 并安装后端依赖。
  - `make test` 通过，2 个后端测试通过。
  - `make check` 通过，ruff 静态检查通过，2 个后端测试通过。
  - 新登录 zsh 可直接识别 `uv`：`uv 0.11.21`。
  - `make UV=/Users/wuminxuan/Library/Python/3.9/bin/uv test` 通过。
  - `make UV=/Users/wuminxuan/Library/Python/3.9/bin/uv check` 通过。
  - 新登录 zsh 中直接运行 `make test` 通过。
  - 新登录 zsh 中直接运行 `make check` 通过。
- 备注：已经为后续新终端配置 `uv` PATH；已打开的旧终端需要重新打开，或执行 `source ~/.zshrc` 后才能直接使用 `uv`。仓库 Makefile 不再写死当前机器的 Python 用户路径。

### P0-T03 前端骨架初始化

- 状态：done
- 开始时间：2026-06-14 16:23:30 CST
- 完成时间：2026-06-14 16:44:40 CST
- 授权范围：初始化 `frontend/` 的 Vite + React + TypeScript + eslint 骨架，做最小页面调用 `/api/health`，补齐 `make dev-frontend` 和前端 lint/build 命令；不配置 Playwright、不做端到端测试、不提交 Git。
- 实际修改：
  - 新增 `frontend/package.json`。
  - 新增 `frontend/package-lock.json`。
  - 新增 `frontend/index.html`。
  - 新增 `frontend/vite.config.ts`。
  - 新增 `frontend/tsconfig.json`。
  - 新增 `frontend/tsconfig.app.json`。
  - 新增 `frontend/tsconfig.node.json`。
  - 新增 `frontend/eslint.config.js`。
  - 新增 `frontend/src/main.tsx`。
  - 新增 `frontend/src/App.tsx`。
  - 新增 `frontend/src/styles.css`。
  - 新增 `frontend/src/vite-env.d.ts`。
  - 新增 `frontend/node_modules/` 本地依赖目录。
  - 更新 `Makefile`，增加 `test-frontend`，并让 `setup`、`check`、`dev-frontend` 接入前端命令。
- 验证结果：
  - `npm install` 通过，生成 `frontend/package-lock.json`。
  - `npm run lint` 通过。
  - `npm run build` 通过。
  - `make test-frontend` 通过。
  - `make UV=/Users/wuminxuan/Library/Python/3.9/bin/uv check` 通过。
  - 新登录 zsh 中直接运行 `make check` 通过。
  - `make dev-backend` 可启动后端开发服务。
  - `make dev-frontend` 可启动前端开发服务。
  - `curl http://127.0.0.1:5173/` 可返回前端 HTML。
  - `curl http://127.0.0.1:5173/api/health` 可通过 Vite proxy 返回 `{"status":"ok","service":"astra"}`。
  - `curl http://127.0.0.1:8000/api/health` 可直接返回 `{"status":"ok","service":"astra"}`。
- 备注：`npm install` 在 Node `v23.11.0` 下出现依赖 engine warning，但 lint、build 和开发链路验证均通过；浏览器自动化验证留到 P0-T04 使用 Playwright 完成。

### P0-T04 Playwright E2E 跑通

- 状态：done
- 开始时间：2026-06-14 17:27:15 CST
- 完成时间：2026-06-14 18:01:58 CST
- 授权范围：安装并配置 Playwright，新增浏览器端到端测试，更新 `make test-e2e`，让它自动启动后端和前端并验证页面展示 ASTRA 与后端 `ok` 状态；不做业务功能、不提交 Git。
- 实际修改：
  - 更新 `frontend/package.json`，新增 `test:e2e` 脚本和 `@playwright/test` 依赖。
  - 更新 `frontend/package-lock.json`。
  - 新增 `frontend/playwright.config.ts`。
  - 新增 `frontend/tests/e2e/health.spec.ts`。
  - 更新 `Makefile`，让 `test-e2e` 执行 Playwright 测试，并让 `check` 包含端到端测试。
  - 更新 `docs/phases/phase-0-harness-init.md`，将浏览器 E2E 测试目录调整为 `frontend/tests/e2e/`。
  - 安装 Playwright Chromium 浏览器到本机 Playwright 缓存。
  - 更新 `docs/tasks/phase-0-task-plan.md`。
- 验证结果：
  - `npm install --save-dev @playwright/test` 通过。
  - `npx playwright install chromium` 通过。
  - 首次 `make test-e2e` 发现后端 webServer 缺少 `PYTHONPATH=src`，已修正。
  - 第二次 `make test-e2e` 发现根目录 `tests/e2e` 无法解析前端包内 `@playwright/test`，已将测试移动到 `frontend/tests/e2e/`。
  - `make test-e2e` 通过，1 个 Chromium E2E 测试通过。
  - `make check` 通过，包含 ruff、pytest、前端 lint、前端 build 和 Playwright E2E。
- 备注：Playwright 测试会自动启动后端和前端。运行中会出现 Node `NO_COLOR`/`FORCE_COLOR` warning，不影响测试结果。

### P0-T05 统一命令入口收敛

- 状态：done
- 开始时间：2026-06-14 18:23:54 CST
- 完成时间：2026-06-14 18:25:59 CST
- 授权范围：整理并验证 `Makefile` 的 Phase 0 命令入口，让 `make setup`、`make test`、`make test-unit`、`make test-integration`、`make test-e2e`、`make check`、`make dev-backend`、`make dev-frontend` 语义清楚且可运行；不做业务功能、不提交 Git。
- 实际修改：
  - 更新 `Makefile`，新增 `help` 默认目标。
  - 更新 `Makefile`，新增 `check-npm` 前置检查。
  - 更新 `Makefile`，新增 `NPM` 和 `FRONTEND_DIR` 可覆盖变量。
  - 更新 `Makefile`，让 `setup`、`test-frontend`、`test-e2e`、`check`、`dev-frontend` 使用统一前置检查和变量。
- 验证结果：
  - `make help` 通过。
  - `make setup` 通过。
  - `make test` 通过，2 个后端测试通过。
  - `make test-unit` 通过，1 个单元测试通过。
  - `make test-integration` 通过，1 个集成测试通过。
  - `make test-frontend` 通过，前端 lint 和 build 通过。
  - `make test-e2e` 通过，1 个 Chromium E2E 测试通过。
  - `make check` 通过，包含 ruff、pytest、前端 lint、前端 build 和 Playwright E2E。
  - `make dev-backend` 可启动后端服务，`curl http://127.0.0.1:8000/api/health` 返回 `{"status":"ok","service":"astra"}`。
  - `make dev-frontend` 可启动前端服务，`curl http://127.0.0.1:5173/` 返回前端 HTML。
  - Vite proxy 可用，`curl http://127.0.0.1:5173/api/health` 返回 `{"status":"ok","service":"astra"}`。
- 备注：开发服务验证后已停止对应进程。运行中仍会出现 Node `NO_COLOR`/`FORCE_COLOR` warning，不影响测试结果。

### P0-T06 剩余 Harness 文档补齐

- 状态：done
- 开始时间：2026-06-14 18:28:24 CST
- 完成时间：2026-06-14 18:29:35 CST
- 授权范围：补齐 Phase 0 交付物中的 `README.md`、`docs/harness/task-template.md`、`docs/adr/README.md`，并按需要创建对应目录；不写 Phase 1 详细业务方案、不改代码、不提交 Git。
- 实际修改：
  - 新增 `README.md`。
  - 新增 `docs/harness/task-template.md`。
  - 新增 `docs/adr/README.md`。
  - 新增 `docs/modules/README.md`。
  - 新增 `docs/evaluation/README.md`。
- 验证结果：
  - 文档文件列表检查通过。
  - `make check` 通过，包含 ruff、pytest、前端 lint、前端 build 和 Playwright E2E。
- 备注：`docs/phases/phase-1-theme-to-pool.md` 尚未创建；Phase 1 详细内容需要单独讨论后落盘。

### P0-T07 Phase 0 总验收

- 状态：done
- 开始时间：2026-06-14 18:30:00 CST
- 完成时间：2026-06-14 18:56:12 CST
- 授权范围：执行 Phase 0 总验收；允许修复验收过程中暴露的 Phase 0 可启动性问题；创建 Phase 1 阶段文档和初始任务分解；不提交 Git。
- 实际修改：
  - 更新 `Makefile`，让 `uv` 优先从 PATH 查找，找不到时通过 `python3 -m site --user-base` 动态发现用户安装目录。
  - 更新 `Makefile`，让 `make test-e2e` 和 `make check` 将解析后的 `uv` 路径传给 Playwright。
  - 更新 `frontend/playwright.config.ts`，让 Playwright 后端 webServer 使用 `ASTRA_UV` 启动后端。
  - 新增 `docs/phases/phase-1-theme-to-pool.md`。
  - 新增 `docs/tasks/phase-1-task-plan.md`。
- 验证结果：
  - 交付物清点发现 `docs/phases/phase-1-theme-to-pool.md` 缺失。
  - 首次 `make setup` 失败，原因是当前 Codex 执行环境 PATH 中没有 `uv`。
  - 修复 `uv` 动态发现后，`make setup` 通过。
  - `make help` 通过。
  - `make test` 通过，2 个后端测试通过。
  - `make test-unit` 通过，1 个单元测试通过。
  - `make test-integration` 通过，1 个集成测试通过。
  - `make test-frontend` 通过，前端 lint 和 build 通过。
  - `make test-e2e` 通过，1 个 Chromium E2E 测试通过。
  - `make check` 通过，包含 ruff、pytest、前端 lint、前端 build 和 Playwright E2E。
  - `make dev-backend` 可启动后端服务，`GET /api/health` 返回 `{"status":"ok","service":"astra"}`。
  - `make dev-frontend` 可启动前端服务，Vite proxy 请求 `/api/health` 返回 `{"status":"ok","service":"astra"}`。
  - 端口 `8000` 和 `5173` 验证后无残留监听进程。
  - 创建 Phase 1 文档后复验，`docs/phases/phase-1-theme-to-pool.md` 和 `docs/tasks/phase-1-task-plan.md` 均已存在。
  - Phase 1 文档包含目标、范围、非范围和验收标准。
  - Phase 1 任务计划包含 P1-T01 到 P1-T10 的初始任务分解。
  - 复验 `make check` 通过，包含 ruff、pytest、前端 lint、前端 build 和 Playwright E2E。
- 备注：Phase 0 验收标准已经满足；后续可以从 `docs/tasks/phase-1-task-plan.md` 的 P1-T01 开始推进。
