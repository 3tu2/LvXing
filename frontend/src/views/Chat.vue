<template>
  <div class="chat-container">
    <!-- 顶栏 -->
    <div class="chat-header">
      <a-button type="text" class="back-btn" @click="router.push('/')">
        <ArrowLeftOutlined />
      </a-button>
      <span class="chat-title">南昌旅行助手</span>
      <span class="chat-sub">智能问答 · 实时信息</span>
    </div>

    <!-- 消息区 -->
    <div class="chat-body" ref="bodyRef">
      <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role === 'user' ? 'msg-user' : 'msg-assistant']">
        <div class="bubble">{{ m.content }}</div>
        <div v-if="m.role === 'assistant' && m.sources && m.sources.length" class="msg-meta">
          来源:{{ m.sources.join('、') }}
        </div>
        <div v-if="m.role === 'assistant' && m.memories && m.memories.length" class="msg-meta memories">
          参考了 {{ m.memories.length }} 条历史记忆
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="chat-input">
      <a-input
        v-model:value="input"
        placeholder="问我南昌的景点、美食、天气、交通…"
        size="large"
        :disabled="sending"
        @pressEnter="send"
      />
      <a-button type="primary" size="large" :loading="sending" @click="send" class="send-btn">
        发送
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
// 旅行对话助手:聊天式界面,支持多轮追问、来源/记忆标注,移动优先。
import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeftOutlined } from '@ant-design/icons-vue'
import { streamChat } from '@/services/api'
import type { ChatMessage } from '@/types'

interface DisplayMessage extends ChatMessage {
  sources?: string[]
  memories?: string[]
}

const router = useRouter()
const input = ref('')
const sending = ref(false)
const messages = ref<DisplayMessage[]>([])
const bodyRef = ref<HTMLElement>()

const scrollToBottom = async () => {
  await nextTick()
  if (bodyRef.value) {
    bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  }
}

const send = async () => {
  const text = input.value.trim()
  if (!text || sending.value) return

  // 历史上下文:取推送前的最近 6 条
  const history: ChatMessage[] = messages.value
    .slice(-6)
    .map((m) => ({ role: m.role, content: m.content }))

  // 用户消息 + 空的助手占位(流式填充)
  messages.value.push({ role: 'user', content: text })
  messages.value.push({ role: 'assistant', content: '' })
  const idx = messages.value.length - 1
  input.value = ''
  sending.value = true
  await scrollToBottom()

  try {
    await streamChat(text, history, {
      onDelta: (d) => {
        messages.value[idx].content += d
        scrollToBottom()
      },
      onDone: (sources, related) => {
        messages.value[idx].sources = sources
        messages.value[idx].memories = related
      },
      onError: (err) => {
        if (!messages.value[idx].content) messages.value[idx].content = err
      },
    })
  } catch (e: any) {
    if (!messages.value[idx].content) {
      messages.value[idx].content = e.message || '发送失败,请稍后重试'
    }
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

onMounted(() => {
  messages.value.push({
    role: 'assistant',
    content: '你好!我是南昌旅行助手 🤖 可以问我南昌的景点、美食、天气、交通等问题,也可以让我帮你规划行程。',
  })
})
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(135deg, #e6fffa 0%, #f0fdfa 100%);
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e6f4f1;
  box-shadow: 0 2px 12px rgba(14, 165, 164, 0.08);
}
.back-btn {
  color: #0ea5a4;
}
.chat-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f766e;
}
.chat-sub {
  font-size: 12px;
  color: #94a3b8;
}

.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.msg {
  display: flex;
  flex-direction: column;
  max-width: 78%;
}
.msg-user {
  align-self: flex-end;
  align-items: flex-end;
}
.msg-assistant {
  align-self: flex-start;
  align-items: flex-start;
}

.bubble {
  padding: 12px 16px;
  border-radius: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 15px;
}
.msg-user .bubble {
  background: linear-gradient(135deg, #0ea5a4 0%, #10b981 100%);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg-assistant .bubble {
  background: #fff;
  color: #334155;
  border: 1px solid #e6f4f1;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  border-bottom-left-radius: 4px;
}

.msg-meta {
  margin-top: 6px;
  font-size: 12px;
  color: #94a3b8;
  padding: 2px 8px;
  background: rgba(14, 165, 164, 0.08);
  border-radius: 8px;
}
.msg-meta.memories {
  background: rgba(245, 158, 11, 0.1);
  color: #b45309;
}

.chat-input {
  display: flex;
  gap: 10px;
  padding: 14px 20px;
  background: #fff;
  border-top: 1px solid #e6f4f1;
}
.send-btn {
  flex-shrink: 0;
  background: linear-gradient(135deg, #0ea5a4 0%, #10b981 100%);
  border: none;
}

@media (max-width: 768px) {
  .chat-body { padding: 14px; }
  .msg { max-width: 88%; }
}
</style>
