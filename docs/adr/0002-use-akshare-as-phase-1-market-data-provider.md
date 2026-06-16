# ADR 0002：Phase 1 使用 AKShare 作为首个市场数据 Provider

## 状态

已接受

## 背景

P1-T04 需要在 Phase 1 内明确真实股票数据 API、字段、许可边界、失败降级和测试替代数据。此前候选数据源包括 Tushare、RQData、Wind、同花顺 iFinD、东方财富 Choice、券商量化接口、AKShare 和 Baostock 等。

经过初步调研和用户衡量，Wind、iFinD、Choice、RQData、Tushare、QMT、PTrade 等更强的数据源或券商接口通常需要账号、申请、终端或授权。它们适合作为中长期接入对象，但会增加 Phase 1 的启动成本。

Phase 1 当前目标是验证 Theme-to-Pool Research Funnel 的最小真实数据接入能力，同时保持测试稳定、实现边界清晰，并为未来更强数据源接入保留扩展空间。因此需要选择一个低接入成本的数据源作为首个真实市场数据 provider。

AKShare 官方文档说明，AKShare 是基于 Python 的财经数据接口库，覆盖股票、期货、期权、基金、外汇、债券、指数、加密货币等金融产品的基本面数据、实时和历史行情数据、衍生数据，主要用于学术研究目的。AKShare 数据字典也包含 A 股、实时行情、历史行情、个股信息、板块和多类金融数据入口。

参考资料：

- [AKShare 项目概览](https://akshare.akfamily.xyz/introduction.html)
- [AKShare 数据字典](https://akshare.akfamily.xyz/data/index.html)
- [AKShare 股票数据](https://akshare.akfamily.xyz/data/stock/stock.html)

## 决策

Phase 1 选择 AKShare 作为首个真实市场数据 provider，用于完成最小真实股票数据 API 接入。

该选择只代表 Phase 1 的首个 provider 实现，不代表 ASTRA 的长期唯一数据源，也不代表 ASTRA 内部研究合同以 AKShare 字段为中心设计。

### Provider 边界

ASTRA 后续应采用以下依赖方向：

```text
ASTRA internal contracts
  <- market data adapter
    <- provider raw records
      <- AKShare / Tushare / Wind / iFinD / Choice / QMT / RQData
```

Phase 1 中，AKShare 原始返回字段必须先进入 provider raw record 或 provider-specific DTO，再通过 adapter 转换为 ASTRA 内部合同。召回、证据补全、模型粗排、模型精排和报告生成模块不得直接依赖 AKShare 函数名、字段名或 DataFrame 结构。

### Phase 1 最小接入能力

P1-T05 和 P1-T06 的最小实现应围绕以下能力设计：

| 能力 | Phase 1 用途 | 最小字段 |
| --- | --- | --- |
| A 股基础信息 | 规范化候选股票、展示名称、市场和交易所 | 股票代码、股票名称、交易所或可推导交易所、上市状态或可替代状态、数据来源 |
| 概念、板块或行业成分 | 从主题召回候选公司 | 概念/板块/行业名称、成分股代码、成分股名称、数据来源、获取时间 |
| 数据源元信息 | 支持证据边界和降级说明 | provider 名称、接口名称、获取时间、失败原因、是否降级 |

Phase 1 不要求 AKShare 一次性接入完整行情、完整财务、公告、研报、新闻或生产级数据同步。上述能力可作为后续 evidence enrichment、因子研究或回测阶段的扩展项。

P1-T04 只完成数据源选型和接入规格，不包含代码接入。AKShare provider、raw record、adapter 和 fixture fallback 的实现属于 P1-T05；真实候选召回使用 provider 的集成属于 P1-T06。

### 许可与使用边界

AKShare 在 Phase 1 中只用于研究原型和本地开发验证。系统输出必须说明数据来源和时间点，不得把 AKShare 返回数据包装成实时、完整、权威或生产级数据。

如果后续 ASTRA 进入生产级投研、团队共享、商业使用、真实交易或自动化交易阶段，必须重新评估数据源授权、稳定性、服务条款、频率限制、数据质量和审计要求。

### 真实接入、失败降级与测试策略

Phase 1 必须验证真实 AKShare 接入。AKShare provider 实现后，集成测试应真实访问 AKShare 并验证能拉取、规范化和校验 A 股市场数据。

Phase 1 测试策略：

- 单元测试使用 fixture 或 fake/mock provider，覆盖字段映射、缺失字段、异常处理和 fallback 行为。
- 集成测试必须包含真实 AKShare provider 调用，覆盖从互联网拉取真实市场数据并映射到 ASTRA 合同。
- `make check` 应运行真实 AKShare 集成测试；如果本地网络、AKShare 或上游公开接口不可用，应明确失败原因，而不是静默跳过。
- 当 AKShare 不可用、接口变化、网络失败、字段缺失或返回空数据时，运行时 provider 可以降级到固定样例数据，以保证用户流程有可解释的 fallback。
- fixture fallback 是运行时韧性机制，不是证明真实数据源已接入的测试替代。

### 长期扩展

后续接入 Tushare、Wind、iFinD、Choice、RQData、QMT 或 PTrade 时，应新增 provider adapter，而不是修改核心研究合同。

券商量化接口，如 QMT 和 PTrade，更适合作为后续行情、模拟盘或交易执行 adapter 候选，不作为 Phase 1 主市场数据 provider。

## 理由

选择 AKShare 的主要理由：

- 接入成本低，适合 Phase 1 快速验证最小真实数据闭环。
- Python 生态友好，适合当前后端实现。
- 覆盖 A 股、板块、行情、财务等多类数据，能支撑 Phase 1 原型和后续探索。
- 不需要在 Phase 1 引入账号、token、终端或券商环境。
- 与 fixture/mock 策略兼容，可以保持自动化测试稳定。

保留 provider adapter 边界的主要理由：

- 避免 AKShare 字段污染 ASTRA 内部模型。
- 为后续替换为更稳定、更专业或授权更清晰的数据源保留空间。
- 支持长期多 provider 组合，例如结构化市场数据源、券商执行接口和网页知识检索能力并存。

## 影响

P1-T05 应实现 AKShare provider raw model、adapter 和 fixture fallback。

P1-T06 应将真实候选召回接入 provider 抽象，而不是直接调用 AKShare。

P1-T06 不得假设单一 AKShare 概念成分接口一定可用。当前环境下手工调用东方财富概念成分接口 `stock_board_concept_cons_em` 遇到上游 `ProxyError`；P1-T06 必须评估可用的 AKShare 概念、行业或替代接口，并在接口不可用时提供明确错误、降级或替代路径。

文档、代码和测试中应避免把 AKShare 称为 ASTRA 的唯一数据源。更合适的命名是：

- `MarketDataProvider`
- `AkshareMarketDataProvider`
- `MarketDataAdapter`
- `ProviderMetadata`
- `ProviderSnapshot`

P1-T04 完成后，当前任务可以进入 P1-T05 股票数据源 adapter 与 fixture 降级。

## 替代方案

### 选择 Tushare 作为 Phase 1 主数据源

Tushare 覆盖面较强，接口更结构化，但需要 token、积分和权限评估。现阶段会增加接入和测试准备成本。

### 选择 Wind、iFinD、Choice 或 RQData

这些数据源更适合作为长期专业数据服务候选，但通常需要申请、授权、账号或商业使用条件确认。Phase 1 暂不以它们作为主实现。

### 选择 QMT 或 PTrade

券商量化接口对后续模拟盘和执行能力很有价值，但通常绑定券商、客户端、本地环境或交易权限。它们更适合作为后续 broker/execution adapter。

### 继续只使用 fixture

继续只使用 fixture 可以保持测试简单，但无法满足 Phase 1 必须实现真实股票数据 API 最小接入的要求。

## 重新评估条件

出现以下情况时，应重新评估本 ADR：

- AKShare 接口频繁变化，导致 adapter 维护成本过高。
- AKShare 无法稳定提供 A 股基础信息或概念/板块成分数据。
- 用户获得 Tushare、Wind、iFinD、Choice、RQData、QMT 或 PTrade 的可用账号和授权。
- ASTRA 进入团队共享、生产级投研、模拟盘或真实交易阶段。
- 数据许可、稳定性、频率限制或审计要求提高。
