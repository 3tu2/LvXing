# 南昌旅行助手 — 本地部署与端到端验证指南

> 本文档给出从零部署到逐功能验证的完整步骤,适合首次在本机跑通项目时对照执行。
> 配套 `README.md`(项目概览)与 `nanchang-requirements.md`(需求基线)。

## 〇、一键初始化(推荐)

项目提供了自动初始化脚本,可完成「建虚拟环境 → 装依赖 → 检查配置 → 摄取知识库 → 创建管理员」:

```bash
# Windows:双击,或在 backend 目录执行
scripts\setup.bat

# Linux / macOS / Git Bash
bash scripts/setup.sh
```

> 脚本会自动复制 `.env`(若不存在)并提示你填密钥;`DASHSCOPE_API_KEY` 未配置时会自动跳过知识库摄取。
> 想手动逐步执行,继续看下面的详细步骤。

---

## 一、环境准备

| 依赖 | 要求 |
|---|---|
| Python | 3.10+(推荐 3.12) |
| Node.js | 16+ |
| 高德 Key | Web 服务 API + Web 端 JS API 各一个 |
| LLM Key | DeepSeek 等 OpenAI 兼容接口 |
| 千问 Embedding Key | 阿里云百炼(仅 RAG 需要) |

---

## 二、后端部署

### 1. 安装依赖

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate              # Windows;Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置 .env

```bash
cp .env.example .env
```

编辑 `.env`,至少填:

```ini
LLM_MODEL_ID=deepseek-chat
LLM_API_KEY=你的LLM密钥
LLM_BASE_URL=https://api.deepseek.com

AMAP_API_KEY=你的高德密钥

DASHSCOPE_API_KEY=你的千问Embedding密钥
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

JWT_SECRET=一段随机长字符串
```

> 生成 JWT_SECRET:`python -c "import secrets; print(secrets.token_urlsafe(48))"`

### 3. 摄取南昌知识库(RAG 功能必需)

```bash
python scripts/kb_ingest.py                      # 清洗→切片→向量化→BM25 双索引
python scripts/kb_ingest.py --search "滕王阁"     # 验证混合检索
```

> 若第 2 步报 401:检查 `DASHSCOPE_API_KEY`;若 Key 是第三方中转的,把 `EMBEDDING_BASE_URL` 改为中转服务地址。

### 4. 创建管理员(后台管理用)

```bash
python scripts/create_admin.py --username admin --password 123456
```

### 5. 启动

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

验证:`http://localhost:8000/docs` 应能打开。

---

## 三、前端部署

```bash
cd frontend
npm install
# 复制 .env.example 为 .env,填入 VITE_API_BASE_URL、VITE_AMAP_WEB_JS_KEY
npm run dev
```

访问 `http://localhost:5173`。

---

## 四、端到端验证(curl)

### 1. 注册 / 登录

```bash
# 注册
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test01","password":"123456","nickname":"测试"}'

# 登录(记下返回的 token)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test01","password":"123456"}'
```

预期:两者都返回 `token` 与用户信息。

### 2. 行程规划(创建会话 → 生成)

```bash
# 创建规划会话(记下 session_id)
curl -X POST http://localhost:8000/api/plan/session \
  -H "Content-Type: application/json" \
  -d '{"state":{"departure_city":"北京","start_date":"2026-06-01","end_date":"2026-06-03","party_adults":2,"budget":3000,"transportation":"高铁","interests":["历史文化","美食"]}}'

# 生成行程(用上一步的 session_id)
curl -X POST "http://localhost:8000/api/plan/generate?session_id=<SESSION_ID>"
```

预期:`current_plan` 为南昌旅行计划,`conflicts` 可能含预算/营业时间提示。

### 3. 局部重规划

```bash
curl -X POST http://localhost:8000/api/plan/replan \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<SESSION_ID>","instruction":"第二天酒店换成经济型"}'
```

预期:返回调整后的计划,只改相关部分。

### 4. 知识检索

```bash
curl "http://localhost:8000/api/kb/search?q=滕王阁营业时间"
```

预期:`data` 返回带来源的营业时间条目。

### 5. 旅行对话助手(带 token 测个性化)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"message":"南昌有什么好吃的?","chat_history":[]}'
```

预期:`reply` 为回答,`sources` 含知识来源,`related_memories` 可空。

### 6. 历史行程(需登录 token)

```bash
curl http://localhost:8000/api/trips -H "Authorization: Bearer <TOKEN>"
```

预期:若第 2 步用登录用户生成过,这里能看到保存的行程。

### 7. 后台管理(需 admin token)

```bash
# 用 admin 登录拿 token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" -d '{"username":"admin","password":"123456"}'

curl http://localhost:8000/api/admin/stats -H "Authorization: Bearer <ADMIN_TOKEN>"
curl http://localhost:8000/api/admin/users -H "Authorization: Bearer <ADMIN_TOKEN>"
```

预期:`stats` 返回用户数/行程数/问答数/知识库切片数。

---

## 五、常见问题排查

| 现象 | 原因与处理 |
|---|---|
| `ModuleNotFoundError: langchain_chroma` | 未装依赖,回到二.1 `pip install -r requirements.txt` |
| 知识检索为空 | 未摄取知识库,回到二.3 `python scripts/kb_ingest.py` |
| 生成行程报 401/鉴权失败 | 检查 `.env` 的 `LLM_API_KEY`、`AMAP_API_KEY` |
| 问答无实时天气/POI | 高德 `AMAP_API_KEY` 未配或配额用尽 |
| 禁用用户仍能访问 | 确认其已重新登录(token 有效期内仍有效) |
| 后台提示无权限 | 当前账号非 admin,用二.4 脚本创建/升级 |

---

## 六、数据与重置

- **SQLite**:`backend/data/app.db`(用户/行程/规划会话)
- **记忆向量库**:`backend/data/chroma/`(按 user_id 隔离的对话记忆)
- **知识库**:`backend/data/kb/`(向量 + BM25 索引)

重置方式:删除 `backend/data/` 下对应文件后重启即可(数据会重建)。

---

*文档版本:与 M0~M7 全部交付代码同步。*
