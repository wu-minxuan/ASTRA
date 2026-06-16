# ADR 0003：网页与网络知识搜索作为独立 Evidence Provider

## 状态

已接受

## 背景

ASTRA 的长期目标不仅是处理结构化市场数据，还要支持 Agent 发掘财务数据之外的信息，例如政策变化、产业链线索、公司官网资料、交易所公告、新闻、研报摘要、行业资料、互动问答和网页材料。

P1-T04 明确 Phase 1 的首个市场数据 provider 使用 AKShare，但 AKShare 这类结构化或半结构化市场数据源不能覆盖所有研究证据。把网页搜索、网页抓取、新闻检索、公告解析和 RAG 能力混入 MarketDataProvider，会让市场数据接口承担过多职责，也会污染候选召回、证据补全和后续 Agent 编排边界。

因此需要明确：网页与网络知识搜索是独立 evidence provider 方向，不属于市场数据 provider。

## 决策

ASTRA 将结构化市场数据源和网页/网络知识搜索源拆分为不同 provider 类型。

```text
candidate_recall
  -> MarketDataProvider

evidence_enrichment
  -> MarketDataProvider
  -> WebKnowledgeProvider
  -> DocumentProvider
  -> SearchProvider
  -> Future RAG providers

coarse_rank / deep_rank / report_generation
  -> structured evidence package
```

### MarketDataProvider

MarketDataProvider 负责结构化或半结构化市场数据，例如：

- 股票基础信息。
- 交易所、市场和上市状态。
- 概念、板块、行业和成分股。
- 行情、复权、交易日历。
- 财务、估值和基础指标。

MarketDataProvider 的输出应优先服务候选召回、证券标识规范化、基础证据和后续因子/回测能力。

### WebKnowledgeProvider

WebKnowledgeProvider 负责网页和网络知识来源，例如：

- 搜索引擎结果。
- 公司官网页面。
- 交易所公告网页。
- 政策文件和监管机构网页。
- 新闻网页。
- 行业协会、产业链资料和公开报告页面。
- 券商研报摘要或可合法访问的研究材料。
- 社交媒体、互动问答和社区内容，前提是明确来源和可信度边界。

WebKnowledgeProvider 不直接输出股票池或投资建议，而是输出可追踪证据候选。

### Evidence 输出边界

网页和网络知识搜索结果必须经过证据标准化后才能进入模型粗排、模型精排或报告生成。

最小证据字段应包括：

| 字段 | 用途 |
| --- | --- |
| `source_url` | 原始网页地址 |
| `source_name` | 来源名称 |
| `source_type` | 新闻、公告、官网、政策、研报摘要、网页搜索等 |
| `retrieved_at` | 抓取或检索时间 |
| `published_at` | 来源发布时间，如果可得 |
| `title` | 来源标题 |
| `summary` | 证据摘要 |
| `stance` | 事实、推断或假设 |
| `confidence` | 来源和内容可信度 |
| `related_symbols` | 关联股票代码，如果可解析 |
| `related_theme` | 关联主题 |

进入模型前，证据包必须保留来源、时间点和可信度边界。模型可以总结、归纳和比较证据，但不得把网页内容包装成未经验证的事实。

### Agent 使用边界

Agent 可以使用 WebKnowledgeProvider 来：

- 为主题扩展背景和产业链上下文。
- 为候选公司补充新闻、公告、政策和官网证据。
- 发现结构化市场数据之外的主题催化和风险。
- 交叉验证 MarketDataProvider 提供的概念或行业关系。
- 为粗排、精排和报告生成提供更多证据。

Agent 不得直接基于搜索结果生成确定性交易建议。网页证据必须经过来源标注、可信度判断、时间点记录和结构化证据转换。

### Phase 1 范围

Phase 1 可以先不实现 WebKnowledgeProvider，但 P1-T07 证据补全、P1-T08 模型粗排、P1-T09 模型精排和 P1-T10 报告生成的设计应为该 provider 预留扩展点。

若 Phase 1 后续实现最小网页证据能力，应优先采用 mock/search fixture 测试，不让默认自动化测试依赖真实搜索引擎、实时网页或不稳定网络。

## 理由

拆分 provider 类型有以下好处：

- 防止 MarketDataProvider 变成所有数据能力的杂糅入口。
- 让结构化市场数据和非结构化网页证据分别演进。
- 支持 Agent 在不同证据类型之间做交叉验证。
- 为后续公告、新闻、研报、网页搜索和 RAG 能力预留清晰边界。
- 保持模型输入是结构化 evidence package，而不是自由网页文本。
- 降低测试不稳定性，避免默认测试依赖实时网页结果。

## 影响

后续模块设计应遵守以下影响：

- P1-T05 和 P1-T06 聚焦 MarketDataProvider，不实现网页搜索。
- P1-T07 证据补全模块应预留多个 evidence provider 合并能力。
- P1-T08 和 P1-T09 的模型输入应依赖标准化证据包，而不是直接接收网页原文。
- P1-T10 报告生成必须保留网页证据的来源、时间和可信度边界。
- 后续如引入搜索 API、浏览器抓取、公告解析、研报解析或 RAG，应新增 provider 或 adapter，而不是修改 MarketDataProvider。

## 替代方案

### 把网页搜索并入 MarketDataProvider

这种方案短期简单，但会混淆结构化市场数据和非结构化网页证据，使候选召回、证据补全和报告生成难以保持清晰边界。

### 让模型直接联网搜索并生成结论

这种方案看起来更智能，但会削弱可追溯性、测试稳定性和证据边界。ASTRA 需要的是可记录、可复盘、可评估的证据流，而不是不可控的自由搜索输出。

### Phase 1 完全不考虑网页证据

这种方案可以缩小当前范围，但会让后续证据补全、模型粗排和报告生成重新调整边界。提前定义 provider 类型成本很低，收益较高。

## 重新评估条件

出现以下情况时，应重新评估本 ADR：

- ASTRA 引入统一数据湖或统一知识库，需要重新组织 provider 类型。
- WebKnowledgeProvider 与 DocumentProvider、SearchProvider 或 RAG provider 的边界变得模糊。
- 默认自动化测试需要覆盖真实网页搜索。
- 网页来源许可、版权、合规或隐私要求提高。
- 系统开始使用网络证据影响模拟盘或真实交易决策。
