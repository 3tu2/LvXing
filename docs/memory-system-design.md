# 对话记忆与个性化问答系统设计

> 本方案取代之前的"攻略知识库 RAG"方案(见 `rag-feasibility.md` 顶部变更说明)。
> 核心思路:不再检索外部攻略,而是把**用户自己的历史对话和偏好**变成可检索的记忆,
> 让助手越用越懂用户,实现个性化推荐。

---

## 一、需求与目标

| 需求 | 实现方式 |
|---|---|
| 基于 ChromaDB 存储历史对话向量 | 每轮问答(用户问题 + AI 回答)各存一条向量记忆 |
| 按用户 ID 隔离记忆 | 所有记忆带 `user_id` 元数据,检索强制 `filter={"user_id": ...}`,互不可见 |
| 语义相似度检索 | 新问题向量化后,在该用户自己的记忆里找最相似的 Top-K 条 |
| 反馈分析 Agent 提取旅行偏好 | LLM 从对话中提取结构化偏好(目的地/美食/预算/节奏等),写入记忆 |
| 后续对话注入偏好上下文 | 问答前把偏好画像 + 相关历史记忆拼进 system prompt |
| 问答服务 | `POST /api/chat` 完成"记忆检索 → 偏好注入 → 生成 → 记忆回写"闭环 |

---

## 二、整体架构

```
用户(ID 隔离)
   │  消息
   ▼
POST /api/chat
   │
   ├─ 1. 语义检索该用户历史记忆(memory_service)
   ├─ 2. 读取偏好画像(profile 快照)
   ├─ 3. 组装个性化上下文 → 注入 system prompt
   ├─ 4. LLM(DeepSeek)生成回答
   ├─ 5. 本轮对话写入向量库(dialogue 记忆)
   └─ 6. 后台任务:反馈分析 Agent 提取偏好
          └─ 更新 preference 记忆 + profile 画像快照

存储:ChromaDB(本地持久化 backend/data/chroma/)
  ├─ type=dialogue    历史对话(role: user/assistant)
  ├─ type=preference  单条偏好("用户旅行偏好 - 预算水平: 舒适")
  └─ type=profile     偏好画像快照(JSON 字符串,最新一条生效)
```

---

## 三、数据模型

### 记忆条目(向量库 Document)

| 字段 | 说明 |
|---|---|
| `page_content` | 记忆文本(对话内容 / 偏好描述 / 画像 JSON) |
| `metadata.user_id` | 用户 ID(**隔离键,所有检索必带**) |
| `metadata.type` | dialogue / preference / profile |
| `metadata.role` | 仅对话类:user / assistant |
| `metadata.preference_key` | 仅偏好类:偏好字段名 |
| `metadata.id` | Chroma 内部 ID(用于删除旧画像) |

### 偏好画像(profile 快照 JSON)

```json
{
  "destinations": ["上海", "日本"],
  "food_preferences": ["本帮菜", "不吃辣"],
  "travel_style": ["历史文化", "休闲度假"],
  "budget_level": "舒适",
  "transportation": "高铁",
  "accommodation": "民宿",
  "pace": "轻松",
  "notes": "带老人同行,对海鲜过敏"
}
```

---

## 四、模块清单(后端)

| 文件 | 职责 |
|---|---|
| `app/services/embedding_service.py` | 千问 Embedding 单例(text-embedding-v3,OpenAI 兼容模式) |
| `app/services/vector_store.py` | ChromaDB 封装:add_memory / search_memory / get_all_memories / count / clear;**强制 user_id 隔离** |
| `app/services/memory_service.py` | 记忆业务:record_dialogue / save_preferences / get_user_profile / build_user_context |
| `app/agents/feedback_agent.py` | 反馈分析 Agent:对话文本 → 结构化偏好 JSON |
| `app/api/routes/chat.py` | `POST /api/chat` 个性化问答 |
| `app/api/routes/memory.py` | 记忆管理/调试接口 |
| `app/models/schemas.py` | ChatRequest / ChatResponse / Memory* / Preference* 模型 |
| `app/config.py` | memory_top_k / enable_preference_extraction 等配置 |

---

## 五、API 接口

### 核心:POST /api/chat

```json
请求: { "user_id": "uuid-abc-123", "message": "我下周想去上海,预算有限" }
响应: {
  "success": true,
  "reply": "根据您喜欢轻松行程和有限的预算,建议...",
  "user_id": "uuid-abc-123",
  "related_memories": ["用户提问: ...", "用户旅行偏好 - 预算水平: 经济"],
  "preference_updated": false
}
```

### 管理/调试

| 接口 | 说明 |
|---|---|
| `POST /api/memory` | 手动写一条记忆(测试) |
| `GET /api/memory?user_id=&type=` | 查看某用户记忆列表 |
| `GET /api/memory/preferences?user_id=` | 查看偏好画像 |
| `POST /api/memory/extract` | 手动触发偏好提取 |
| `DELETE /api/memory?confirm=yes` | 清空向量库(危险) |

---

## 六、前端接入说明

1. **用户 ID 生成**:前端首次进入时 `localStorage` 里没有 userId 就生成一个
   (`crypto.randomUUID()`),之后所有 `/api/chat` 请求带上,实现"换台电脑也认得你"还需后端注册,当前按浏览器维度记忆;
2. **问答入口**:可加一个"AI 助手"抽屉/页面,聊天流展示 `reply` 与 `related_memories`(如"根据您上次提到的…");
3. **偏好展示**:结果页可展示用户画像,让用户直观看到助手记住了什么。

---

## 七、本地验证步骤(沙箱无外网,需本地执行)

```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt                     # 装 langchain-chroma / chromadb / text-splitters

# 验证千问 Key(需网络)
python -c "from langchain_openai import OpenAIEmbeddings; e=OpenAIEmbeddings(model='text-embedding-v3', api_key='<KEY>', base_url='https://dashscope.aliyuncs.com/compatible-mode/v1'); print('OK', len(e.embed_query('上海外滩')))"

uvicorn app.api.main:app --reload --port 8000       # 启动后端

# 验证闭环(三条命令,同一 user_id)
# 1) 第一次对话:告诉助手你的偏好
curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"user_id":"test-user-1","message":"我喜欢轻松的行程,预算3000以内,爱吃粤菜"}'
# 2) 第二次对话:看助手是否记得(回答应体现预算/风格/美食偏好)
curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"user_id":"test-user-1","message":"帮我规划去广州玩三天"}'
# 3) 查看提取出的偏好画像(应看到 budget_level=经济/舒适、food_preferences 含粤菜)
curl "http://localhost:8000/api/memory/preferences?user_id=test-user-1"
```

预期:第 2 次回答明显比第 1 次更贴合个人偏好,第 3 步能看到结构化画像。
再换一个 `user_id` 重复第 1 步,可验证**用户隔离**生效。

---

## 八、注意事项与后续优化

1. **Key 有效性与 base_url**:若 `sk-ws-` 前缀的 Key 是第三方中转的,需改
   `.env` 的 `EMBEDDING_BASE_URL` 为服务商地址;
2. **偏好提取是后台异步任务**,不阻塞回答返回;若想立即看到画像,可调
   `POST /api/memory/extract`;
3. **画像快照只保留最新一条**(每次更新先删旧的),避免无限累积;
4. 后续可做:用户画像随对话增量更新而非整包替换、多轮记忆摘要压缩、
   行程规划(plan_trip)也注入偏好上下文、前端聊天 UI。
