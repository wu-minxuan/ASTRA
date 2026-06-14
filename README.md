# ASTRA

ASTRA 是一个自适应策略研究与测试 Agent 系统，支持主题发现、股票池构建、基本面分析、研报分析、量化因子研究、策略回测、模拟盘和策略 A/B 实验。

当前项目处于 Phase 0：Harness 初始化。这个阶段的目标是让仓库具备可启动、可测试、可验证、可交接的基础环境。

## 技术栈

- 后端：Python、uv、FastAPI、pydantic
- 后端测试：pytest、ruff
- 前端：Vite、React、TypeScript
- 前端检查：eslint、TypeScript build
- 浏览器端到端测试：Playwright
- 命令入口：Makefile

## 环境要求

- Python 3.9+
- uv
- Node.js 和 npm

如果 `uv` 不在 PATH 中，先安装 uv 并确保新终端可以直接运行：

```bash
uv --version
```

## 常用命令

```bash
make setup
make test
make test-unit
make test-integration
make test-frontend
make test-e2e
make check
make dev-backend
make dev-frontend
```

查看命令说明：

```bash
make help
```

## 本地开发

启动后端：

```bash
make dev-backend
```

后端默认运行在：

```text
http://127.0.0.1:8000
```

启动前端：

```bash
make dev-frontend
```

前端默认运行在：

```text
http://127.0.0.1:5173
```

前端通过 Vite proxy 将 `/api` 请求转发到后端。

## 最小健康检查

后端接口：

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

## 文档入口

- `AGENTS.md`：Agent 协作入口和最高优先级规则
- `docs/vision.md`：项目愿景、长期边界和核心原则
- `docs/phases/`：阶段目标、范围、非范围和验收标准
- `docs/tasks/`：任务计划、任务规格和执行进度
- `docs/harness/`：任务模板、验证模板和 Harness 辅助材料
- `docs/adr/`：架构决策记录
- `docs/modules/`：模块级设计规格
- `docs/evaluation/`：评估标准和验收方法

## 当前阶段

当前阶段为 Phase 0。进入 Phase 1 之前，仓库需要通过 Phase 0 文档中定义的验收标准。

