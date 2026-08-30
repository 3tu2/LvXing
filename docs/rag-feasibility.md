# 智能旅行助手 RAG 功能可行性方案

> **⚠️ 方案已变更(2025):本方案描述的"公开攻略知识库检索"已废弃**,
> 现改为「对话记忆 + 个性化问答」系统,详见 **[memory-system-design.md](memory-system-design.md)**。
> 本文档保留作为 RAG 概念的背景参考。

> 本文档是给「智能旅行助手」项目添加 RAG(检索增强生成)能力的可行性分析与实施方案,不包含代码。
> 适用于后端 FastAPI + LangChain/LangGraph + 高德 MCP,前端 Vue3 + TypeScript 的当前架构。

---

## 〇、已确认的决策

| 决策项 | 结论 |
|---|---|
| 功能优先级 | **① 增强行程规划(主链路)→ ② 独立问答 → ③ 用户历史行程记忆** |
| Embedding 方案 | **千问 Embedding API**(阿里云百炼 `text-embedding-v3`,OpenAI 兼容模式) |
| 知识库来源 | **公开旅游攻略**(马蜂窝、穷游等,注意版权合规) |
| 知识库范围 | **首批只做上海、广州两个城市**的旅游攻略 |

以下方案均基于上述决策展开。

---

## 一、结论先行

**高度可行,且是「低成本、高收益」的增强方向。** 三个关键理由:

1. 项目已经使用 LangChain,而 RAG 是 LangChain 的原生能力(`Retriever`、`VectorStore`、`Document Loader`、`TextSplitter` 都是现成组件),不需要更换框架。
2. 后端已经分层清晰(`services` / `agents` / `api` / `models`),插入点非常明确——不需要改动现有架构,只需「加模块 + 加一个节点 + 加一组接口」。
3. 数据源天然丰富:高德 POI 结构化数据 + 全网旅行攻略 + 用户历史行程,都有现成的获取渠道。

唯一需要注意的是:**真正的瓶颈不是技术,而是「知识库数据从哪来、怎么整理」**。

---

## 二、RAG 在这个项目里能做什么(先定方向)

旅行助手加 RAG,通常对应 4 个场景,建议按优先级取舍:

| 场景 | 说明 | 价值 | 难度 | 当前状态 |
|---|---|---|---|---|
| ① 行程规划增强 | 生成计划前,先检索该城市的攻略/景点深度介绍/美食,作为「资料包」喂给规划专家,让行程更丰富、更本地化 | 高 | 低 | ✅ 已确认,先做 |
| ② 目的地问答机器人 | 独立入口,用户自由提问(如「上海有哪些小众博物馆?」) | 高 | 中 | ✅ 已确认,第二个做 |
| ③ 用户历史行程记忆 | 记住用户过去的偏好,做个性化推荐(需要后端持久化,当前 tripPlan 只存在前端 sessionStorage) | 中 | 中 | ✅ 已确认,最后做 |
| ④ 行程内知识点补充 | 结果页每个景点附一段「百科式」介绍 | 中 | 低 | ⏸ 暂不单列,由 ① 顺带覆盖 |

**执行顺序**:① → ② → ③。① 挂在「行程生成」主链路上,改动最小、见效最快;② 在 ① 的检索/向量库基础上加一组接口即可;③ 需要先补后端持久化,最后做。

---

## 三、整体架构

在现有 `LangGraph` 编排里,加一个 **「知识检索」节点**,与景点/天气/酒店三个专家并行,最后一起汇入规划专家:

```
                  ┌─ 景点搜索专家(高德 MCP)
                  ├─ 天气查询专家(高德 MCP)
用户请求 ── START ─┼─ 酒店推荐专家(高德 MCP) ──┐
                  └─ 知识检索节点(RAG)   ───────┼──> 行程规划专家 ──> 最终计划
                                                     (把攻略知识也拼进 prompt)
```

同时,独立问答功能走另一条轻链路:

```
用户提问 ──> /api/rag/ask ──> 查询向量化 ──> 向量库检索 Top-K ──> (可选重排) ──> 拼 prompt ──> LLM 生成答案
                                                                        └── 返回引用来源
```

后端新增的模块(与现有 `services/` 并列):

- `services/embedding_service.py` — 文本向量化(单例,类似 `llm_service.py`)
- `services/vector_store.py` — 向量库连接与 CRUD
- `services/rag_service.py` — 检索 + 拼接 + 生成的统一入口
- `scripts/ingest.py` — 离线数据摄取脚本(加载文档 → 分块 → 向量化 → 入库)
- `data/documents/` — 存放攻略/知识原始文档

---

## 四、关键技术选型(已按决策确定)

本项目 LLM 用 DeepSeek、Embedding 用千问 API、中文场景。选型原则:**不引入本地模型、轻量、中文优先**。

### 1. 嵌入模型(Embedding)——RAG 质量的核心

**✅ 已决策:千问 Embedding API(阿里云百炼 `text-embedding-v3`),OpenAI 兼容模式调用。**

关键配置:

- **模型名**:`text-embedding-v3`(中文效果好,支持 1024/768/512 维度,默认 1024;如需更省空间可显式指定 `dimensions`)
- **接入方式**(两种任选):
  - **OpenAI 兼容模式(推荐)**:`base_url = https://dashscope.aliyuncs.com/compatible-mode/v1`,`api_key = 百炼 DASHSCOPE_API_KEY`,用 LangChain 的 `OpenAIEmbeddings` 即可——和项目现有 `ChatOpenAI` 的接入方式完全一致,复用同一套代码习惯。
  - LangChain 社区封装 `DashScopeEmbeddings`(`langchain-community` 提供)。
- **前置条件**:在[阿里云百炼控制台](https://bailian.console.aliyun.com/)开通模型服务并获取 API Key,写入 `.env`(如 `DASHSCOPE_API_KEY=sk-xxx`)。

> 说明:嵌入模型和 LLM 是**两个独立的模型**。LLM 继续用 DeepSeek 没问题,embedding 单独走千问,两者互不影响。
>
> 参考文档:
> - [OpenAI 兼容模式调用 Embedding(阿里云百炼官方)](https://help.aliyun.com/zh/model-studio/embedding-interfaces-compatible-with-openai)
> - [LangChain 如何接入千问向量模型](https://www.53ai.com/news/langchain/2025083081430.html)

### 2. 向量数据库

| 方案 | 特点 | 适用 |
|---|---|---|
| **Chroma**(`langchain-chroma`) | 本地持久化、开箱即用、零运维 | ✅ 起步首选 |
| FAISS | 纯内存/本地文件,更快但功能少 | 数据量小、追求简单时 |
| Milvus / Qdrant | 生产级,支持海量数据、混合检索 | 数据上规模后再迁移 |

> 建议:第一阶段用 **Chroma**,它和 LangChain 集成最顺;上海+广州两个城市的攻略量级(预计几百~几千条)完全在 Chroma 的能力范围内,无需考虑迁移。

### 3. 分块策略(Chunking)

- 用 `RecursiveCharacterTextSplitter`,中文场景**分块大小建议 300~500 字,重叠 50~100 字**。
- 攻略类文本结构性强,建议按「标题/小节」做**结构化分块**(保留元数据:城市、类别、来源),检索时可按城市过滤,大幅提升准确率。

### 4. 检索与重排(可选优化)

- 第一阶段:纯向量相似度检索,取 Top-K(3~5 条)。
- 第二阶段(可选):加 **BM25 + 向量混合检索**(关键词匹配补足向量召回),再加 **bge-reranker** 重排。

---

## 五、与现有代码的具体集成点(改动清单)

### 后端

| 文件 | 改动 |
|---|---|
| `backend/app/config.py` | 新增 embedding 模型名、向量库路径/连接、Top-K、是否开启 RAG 等配置项 |
| `backend/requirements.txt` | 加 `langchain-chroma`、`chromadb`(向量库);embedding 走 OpenAI 兼容模式,复用现有 `langchain-openai` 即可,无需额外装 sentence-transformers |
| `backend/app/services/embedding_service.py` | 新增:嵌入模型单例 |
| `backend/app/services/vector_store.py` | 新增:向量库初始化、写入、检索 |
| `backend/app/services/rag_service.py` | 新增:检索 + 拼 prompt + 生成答案的统一方法 |
| `backend/app/agents/trip_planner_agent.py` | 在 `PlannerState` 加 `knowledge_info` 字段;加一个 `_knowledge_node`;在 `_build_planner_query` 里把检索到的攻略注入 prompt;`_build_graph` 里把它和另外三个专家并行接进去 |
| `backend/app/models/schemas.py` | 新增 `RagAskRequest` / `RagAskResponse`(含引用来源) |
| `backend/app/api/routes/rag.py` | 新增路由:`POST /api/rag/ask`(问答)、`POST /api/rag/ingest`(上传/摄取文档)、`GET /api/rag/documents`(列表) |
| `backend/app/api/main.py` | 注册 `rag.router` |
| `backend/scripts/ingest.py` | 新增:离线批量摄取脚本 |

### 前端

| 文件 | 改动 |
|---|---|
| `frontend/src/services/api.ts` | 新增 `askQuestion()` 等 API 函数 |
| `frontend/src/views/` 或 `components/` | 新增「旅行问答」组件(聊天框 + 来源引用展示);结果页景点卡片可选展示 RAG 补充介绍 |

---

## 六、知识库建设(工作量最大的一环)

技术之外,数据才是关键。**✅ 已决策:从公开攻略中选取,首批只做上海、广州两个城市。**

### 6.1 数据来源建议(按优先级)

| 来源 | 说明 | 优先度 |
|---|---|---|
| **高德 POI 结构化数据** | 已有 `amap_service.get_poi_detail`,把沪/广热门景点详情直接入库,成本最低、质量最稳 | 高(作为基底数据) |
| **公开攻略/百科** | 马蜂窝、穷游、携程攻略、百度百科/维基的景点与美食介绍(注意**版权合规**,学习项目可,商用需授权) | 高(作为核心知识) |
| **自建 FAQ/目的地手册** | 自己整理「上海/广州须知、交通、美食、注意事项」等小册子,质量可控、无版权问题 | 中 |
| **用户历史行程** | 先在后端加持久化(数据库/JSON 文件),再把历史 tripPlan 转成知识条目,支撑个性化(③ 阶段再做) | 低(后置) |

### 6.2 首批数据范围(上海 + 广州)

建议每城首批准备 **100~300 篇/条** 内容,覆盖以下类别(元数据 `category` 字段):

- **景点**:外滩、豫园、东方明珠、广州塔、白云山、沙面、陈家祠……
- **美食**:上海本帮菜、生煎、小笼包;广州早茶、烧腊、糖水……
- **交通**:机场/高铁到市区、地铁线路、轮渡……
- **行程路线**:经典 1 日 / 2 日 / 3 日游路线参考
- **注意事项**:天气、预约规则、热门景点避坑……

每一条文档都必须带元数据:**`city`(shanghai/guangzhou)+ `category` + `source`(来源)+ `title`**,检索时先按 `city` 过滤再向量匹配,准确率会明显更高。

### 6.3 版权合规提示

公开攻略来自社区/平台,注意:
- 个人学习、课程演示用途问题不大;
- 若要做成对外产品,建议改用**官方/自建内容**(如自己整理的旅行手册)或取得授权;
- 抓取时遵守 robots 协议、控制频率,不要暴力爬取。

---

## 七、分阶段实施路线(建议)

| 阶段 | 目标 | 内容 |
|---|---|---|
| **P0 准备** | 定方案、备数据 | ✅ 已完成:方向、embedding(千问)、向量库(Chroma)已定;接下来收集整理**上海、广州**首批 100~300 条攻略文档(带 city/category 元数据) |
| **P1 基础设施** | 跑通「存」和「查」 | 千问 embedding 接入(`embedding_service.py`)+ Chroma(`vector_store.py`)+ 摄取脚本(`scripts/ingest.py`);能把沪/广攻略向量化入库、能按城市检索出相关片段 |
| **P2 接入行程规划** | 主链路见效 | `trip_planner_agent` 加知识检索节点,检索到的沪/广攻略注入规划 prompt,对比验证行程是否更丰富 |
| **P3 独立问答** | 新增功能入口 | `/api/rag/ask` + 前端问答组件,带引用来源 |
| **P4 用户记忆(③)** | 个性化 | 后端加持久化,历史 tripPlan 入库,检索时叠加用户偏好 |
| **P5 优化** | 提质提效 | 混合检索、rerank、RAGAS 评测、缓存、增量更新、延迟与成本监控 |

---

## 八、风险与成本提示

1. **延迟增加**:每次行程规划多一次检索 + 多一段上下文。解决:检索结果精简、Top-K 控制在 3 左右、必要时缓存热点城市。
2. **Token/API 成本上升**:检索片段会占 prompt 空间(DeepSeek 按量计费),embedding 调用千问 API 也按量计费(单条成本极低,但批量摄取时注意总量)。需要控制注入长度、摄取代价。
3. **千问 embedding 效果验证**:分块不当会影响中文检索质量。建议 P1 阶段先用「上海博物馆」等典型问题实测检索命中率,再批量入库。
4. **数据版权**:抓取公开攻略用于商用有法律风险;学习项目问题不大,建议标注来源。
5. **冷启动**:初期知识库只有沪/广两城,其他城市检索不到内容,需要有「无结果降级」策略(检索不到就按原逻辑生成,不阻塞主流程)。

---

## 九、下一步行动(决策已定,等待开工)

1. **申请并配置**:阿里云百炼开通 `text-embedding-v3`,拿到 `DASHSCOPE_API_KEY` 写入 `backend/.env`。
2. **收集数据**:整理上海、广州各 100~300 条攻略文档(景点/美食/交通/路线/注意),统一标注 `city` / `category` / `source` / `title` 元数据。
3. **P1 开工**:搭 embedding + Chroma + 摄取脚本,跑通「存」和「查」。
4. **P2 开工**:把知识检索节点接进 `trip_planner_agent`,验证行程规划增强效果。

需要开始实施时,告诉我从哪一步入手即可。
