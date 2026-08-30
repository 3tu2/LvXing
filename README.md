
# 南昌旅行助手 🌆✈️

基于 **LangChain + LangGraph + 高德 MCP + RAG** 构建的南昌专属智能旅行规划助手,支持用户账号、对话式增量行程规划、南昌本地知识增强、个性化问答与后台管理。
## ✨ 运行界面
<img width="1790" height="892" alt="屏幕截图 2026-08-30 184803" src="https://github.com/user-attachments/assets/deaf2d69-f982-441a-b611-bf031eafd4ea" />
<img width="1406" height="648" alt="屏幕截图 2026-08-30 191707" src="https://github.com/user-attachments/assets/42180079-c06f-43c5-8286-fb4b2895c60f" />
<img width="1667" height="1178" alt="屏幕截图 2026-08-30 191640" src="https://github.com/user-attachments/assets/3c47ae08-bb20-4b4f-8f82-06d9541c297c" />
<img width="1796" height="1093" alt="屏幕截图 2026-08-30 191620" src="https://github.com/user-attachments/assets/a782d0e7-6d85-4ca6-89ca-ac556a5337d8" />
<img width="1796" height="1035" alt="屏幕截图 2026-08-30 185451" src="https://github.com/user-attachments/assets/2207369a-8ff4-4502-af44-8cc6fea5acb1" />
<img width="2116" height="1051" alt="屏幕截图 2026-08-30 192220" src="https://github.com/user-attachments/assets/81347188-fe6f-438c-bb68-f5d8a8d7d215" />
## ✨ 功能特性

### 用户与账号
- 🔐 **用户体系**:注册 / 登录(JWT 认证,PBKDF2 密码哈希),**所有功能需登录后使用**
- 🧠 **个性化记忆**:基于 ChromaDB 存储历史对话向量,按用户 ID 隔离,反馈分析 Agent 自动提取旅行偏好并注入后续对话

### 行程规划
- 🗺️ **南昌聚焦**:全站固定南昌,集成高德地图(景点搜索 / 路线 / 天气)
- 🤖 **多智能体生成**:LangGraph 编排景点 / 天气 / 酒店三个专家并行采集,规划专家汇总
- 🧩 **对话式增量规划**:规划状态(出发地 / 日期 / 同行人数 / 预算 / 交通 / 兴趣标签)+ 参数补全 + **局部重规划**(避免全景重新生成)+ 冲突检查
- 📚 **RAG 知识增强**:南昌攻略 / 景点 / 美食 / 拍照点 / 交通枢纽 / 营业时间,清洗切片向量化,**向量 + BM25 混合检索(RRF 融合)**、来源约束、规划后处理(周一闭馆检测等)
- 📱 **历史行程**:登录用户生成即自动保存,可回看 / 打开 / 删除

### 对话与后台
- 💬 **旅行对话助手**:多轮追问、南昌知识 + 高德实时信息(天气 / POI)+ 个性化记忆,附来源引用
- 🛠️ **后台管理**:管理员专属仪表盘(用户 / 行程 / 问答 / 知识库统计)、用户管理(启用 / 禁用)、知识库管理

## 🏗️ 技术栈

**后端**:Python + FastAPI + LangChain / LangGraph + 高德 MCP + 千问 Embedding + ChromaDB + rank-bm25 + SQLite + PyJWT

**前端**:Vue 3 + TypeScript + Vite + Ant Design Vue + 高德地图 JS API + Axios

## 📁 项目结构

```
├── backend/
│   ├── app/
│   │   ├── agents/              # trip_planner_agent(多智能体)、feedback_agent(偏好提取)
│   │   ├── api/                 # main.py、deps.py(认证依赖)、routes/(10 组路由)
│   │   │   └── routes/          # auth/trip/planning/kb/chat/memory/trips/poi/map/admin
│   │   ├── models/schemas.py    # 全部数据模型
│   │   ├── services/            # 服务层(规划/知识/检索/记忆/认证/行程/后处理等)
│   │   ├── config.py            # 配置管理
│   │   └── db.py                # SQLite(用户/行程/规划会话)
│   ├── scripts/                 # kb_ingest.py(知识摄取)、create_admin.py(管理员种子)
│   ├── data/                    # documents/nanchang/(知识)、app.db、chroma/、kb/
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── views/               # Home/Result/Login/Register/MyTrips/Chat/admin/
    │   ├── services/            # api.ts、auth.ts
    │   ├── types/               # index.ts
    │   ├── main.ts              # 路由 + 守卫
    │   └── App.vue
    └── package.json
```

## 🚀 快速开始

> 💡 **一键初始化(推荐)**:`backend/scripts/setup.bat`(Windows)或 `bash backend/scripts/setup.sh`(Linux/macOS),
> 自动完成建虚拟环境、装依赖、检查配置、摄取知识库、创建管理员。详见 `docs/deployment.md`。

### 前提条件

- Python 3.10+(推荐 3.12)
- Node.js 16+
- 高德地图 API Key(Web 服务 API + Web 端 JS API)
- LLM API Key(DeepSeek 等 OpenAI 兼容接口)
- 千问 Embedding API Key(阿里云百炼,用于 RAG)

### 1. 后端安装

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows;Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env             # 编辑 .env,填入你的密钥
```

关键变量:

| 变量 | 说明 |
|---|---|
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL_ID` | 大模型(DeepSeek 等) |
| `AMAP_API_KEY` | 高德 Web 服务 Key(必填) |
| `DASHSCOPE_API_KEY` | 千问 Embedding Key(RAG 用) |
| `JWT_SECRET` | JWT 签名密钥(随机长字符串) |

### 3. 摄取南昌知识库(RAG 必需)

```bash
python scripts/kb_ingest.py               # 清洗 → 切片 → 向量化 → 双索引
python scripts/kb_ingest.py --search "滕王阁"   # 验证混合检索
```

### 4. 启动后端

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 创建管理员(可选,用后台管理时)

```bash
python scripts/create_admin.py --username admin --password 123456
```

### 6. 前端安装与启动

```bash
cd frontend
npm install
# 配置 .env(VITE_API_BASE_URL、VITE_AMAP_WEB_JS_KEY)
npm run dev
```

访问 `http://localhost:5173`。

## 📝 使用指南

1. **生成行程**:首页填写出发地、日期、同行人数、预算、交通方式、兴趣标签 → 生成(南昌专属计划)
2. **调整行程**:结果页"调整行程"框输入一句话指令(如"第二天酒店换成经济型"),只改局部
3. **旅行助手**:顶栏"旅行助手",聊天提问景点 / 美食 / 天气 / 交通,支持多轮追问
4. **我的行程**:登录后生成自动保存,顶栏头像下拉"我的行程"回看
5. **后台管理**:管理员登录后,头像下拉"后台管理"(仪表盘 / 用户 / 知识库)

## 📄 API 文档

启动后访问 `http://localhost:8000/docs` 查看完整接口。

主要端点:

```text
认证     POST /api/auth/register | POST /api/auth/login | GET /api/auth/me
行程     POST /api/trip/plan | GET /api/trips | GET/DELETE /api/trips/{id}
规划引擎  POST /api/plan/session | /api/plan/fill | /api/plan/generate | /api/plan/replan | /api/plan/check
知识     GET /api/kb/search | GET /api/kb/stats
问答     POST /api/chat(多轮 + 实时工具 + 记忆)
后台     GET /api/admin/stats | GET /api/admin/users | GET /api/admin/kb
地图     /api/poi/* | /api/map/*
```

## ✅ 快速验证清单

| 步骤 | 验证点 |
|---|---|
| 注册登录 | `POST /api/auth/register` → `POST /api/auth/login` 返回 token |
| 生成行程 | 首页提交 → 结果页展示南昌计划 |
| 局部重规划 | 结果页"调整行程"输入指令 → 只改局部 |
| 知识问答 | `/api/chat` 问"滕王阁营业时间" → 含来源 |
| 历史行程 | 登录生成 → 顶栏"我的行程"可见 |
| 后台管理 | admin 登录 → "后台管理"查看仪表盘 |

## 📜 开源协议

CC BY-NC-SA 4.0

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) / [LangGraph](https://github.com/langchain-ai/langgraph)
- [高德地图开放平台](https://lbs.amap.com/) / [amap-mcp-server](https://github.com/sugarforever/amap-mcp-server)
- [阿里云百炼](https://bailian.console.aliyun.com/)(千问 Embedding)
- [ChromaDB](https://www.trychroma.com/) / [rank-bm25](https://github.com/dorianbrown/rank_bm25)

---

**智能旅行助手** - 让旅行计划变得简单而智能 🌈
