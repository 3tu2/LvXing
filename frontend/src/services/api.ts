/**
 * API 服务层:负责前端与后端之间的所有 HTTP 通信。
 *
 * 这里用 axios 封装了对后端的请求:
 * 1. 创建一个配置好的 axios 实例(统一设置后端地址、超时时间、请求头);
 * 2. 用"拦截器"统一打印日志、处理错误;
 * 3. 提供几个具体的函数(生成旅行计划、健康检查),供页面调用。
 *
 * 小白可以这样理解:页面组件(Home.vue 等)不需要自己拼网址、管请求细节,
 * 只要调用这里的函数即可,就像去餐厅点菜,不用关心后厨怎么做。
 */

import axios from 'axios'
import type {
  TripFormData, TripPlanResponse, RegisterPayload, LoginPayload, AuthResponse, User,
  PlannerState, PlanningSessionResponse, TripListResponse, TripDetailResponse,
  ChatMessage, ChatResponse, AdminStats, AdminUserItem, KBItem
} from '@/types'  // 导入类型
import { authState, clearAuth } from './auth'  // 登录态(用于自动附带 token)

// 后端地址:优先读环境变量 VITE_API_BASE_URL,没配就用本地默认地址
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// 创建 axios 实例,并做统一配置
const apiClient = axios.create({
  baseURL: API_BASE_URL,        // 所有请求都会自动拼上这个前缀
  timeout: 120000,              // 超时时间 120 秒(生成计划要等大模型,所以设长一点)
  headers: {
    'Content-Type': 'application/json'  // 请求体用 JSON 格式
  }
})

// 请求拦截器:每次"发送请求前"自动执行
apiClient.interceptors.request.use(
  (config) => {
    // 已登录则自动附带 JWT token,后端据此识别当前用户
    if (authState.token) {
      config.headers.Authorization = `Bearer ${authState.token}`
    }
    console.log('发送请求:', config.method?.toUpperCase(), config.url)
    return config  // 必须返回 config,请求才会继续
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)  // 把错误继续抛出去,让调用方处理
  }
)

// 响应拦截器:每次"收到响应后"自动执行
apiClient.interceptors.response.use(
  (response) => {
    console.log('收到响应:', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('响应错误:', error.response?.status, error.message)
    // 401 = token 失效/未登录,清除本地登录态
    if (error.response?.status === 401) {
      clearAuth()
    }
    return Promise.reject(error)
  }
)

/**
 * 注册新用户。
 */
export async function registerUser(payload: RegisterPayload): Promise<AuthResponse> {
  try {
    const response = await apiClient.post<AuthResponse>('/api/auth/register', payload)
    return response.data
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || error.message || '注册失败')
  }
}

/**
 * 登录。
 */
export async function loginUser(payload: LoginPayload): Promise<AuthResponse> {
  try {
    const response = await apiClient.post<AuthResponse>('/api/auth/login', payload)
    return response.data
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || error.message || '登录失败')
  }
}

/**
 * 获取当前登录用户信息(需 token)。
 */
export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>('/api/auth/me')
  return response.data
}

/**
 * 生成旅行计划。
 *
 * @param formData 用户在首页填写的表单数据
 * @returns 后端返回的完整响应(含 success / message / data)
 */
export async function generateTripPlan(formData: TripFormData): Promise<TripPlanResponse> {
  try {
    // POST 到 /api/trip/plan,请求体就是表单数据
    const response = await apiClient.post<TripPlanResponse>('/api/trip/plan', formData)
    return response.data
  } catch (error: any) {
    console.error('生成旅行计划失败:', error)
    // 尽量把后端返回的详细错误信息抛出去
    throw new Error(error.response?.data?.detail || error.message || '生成旅行计划失败')
  }
}

/**
 * 创建规划会话(提交规划状态,返回 session_id 与缺失字段)。
 * userId 为登录用户时传入,用于生成后自动保存为历史行程。
 */
export async function createPlanSession(state: PlannerState, userId?: number): Promise<PlanningSessionResponse> {
  try {
    const response = await apiClient.post<PlanningSessionResponse>('/api/plan/session', {
      state,
      user_id: userId ?? null,
    })
    return response.data
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || error.message || '创建规划会话失败')
  }
}

/**
 * 生成行程计划(参数齐全后调用多智能体)。
 */
export async function generatePlan(sessionId: string): Promise<PlanningSessionResponse> {
  try {
    const response = await apiClient.post<PlanningSessionResponse>(
      '/api/plan/generate', null, { params: { session_id: sessionId } }
    )
    return response.data
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || error.message || '生成行程失败')
  }
}

/**
 * 局部重规划(按修改指令调整现有计划)。
 */
export async function replanPlan(sessionId: string, instruction: string): Promise<PlanningSessionResponse> {
  try {
    const response = await apiClient.post<PlanningSessionResponse>('/api/plan/replan', {
      session_id: sessionId,
      instruction,
    })
    return response.data
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || error.message || '调整行程失败')
  }
}

/**
 * 历史行程列表(需登录)。
 */
export async function listTrips(): Promise<TripListResponse> {
  try {
    const response = await apiClient.get<TripListResponse>('/api/trips')
    return response.data
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || error.message || '获取历史行程失败')
  }
}

/**
 * 行程详情(需登录)。
 */
export async function getTrip(tripId: number): Promise<TripDetailResponse> {
  try {
    const response = await apiClient.get<TripDetailResponse>(`/api/trips/${tripId}`)
    return response.data
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || error.message || '获取行程详情失败')
  }
}

/**
 * 删除历史行程(需登录)。
 */
export async function deleteTrip(tripId: number): Promise<void> {
  try {
    await apiClient.delete(`/api/trips/${tripId}`)
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || error.message || '删除行程失败')
  }
}

/**
 * 旅行对话助手(多轮问答)。
 * 登录用户后端自动用数据库 ID;游客传 userId(前端 UUID)。
 */
export async function sendChat(
  message: string,
  history: ChatMessage[],
  userId?: string
): Promise<ChatResponse> {
  try {
    const response = await apiClient.post<ChatResponse>('/api/chat', {
      message,
      chat_history: history,
      user_id: userId ?? null,
    })
    return response.data
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || error.message || '发送消息失败')
  }
}

/** SSE 流式问答回调。 */
export interface StreamCallbacks {
  onDelta: (delta: string) => void
  onDone: (sources: string[], related: string[]) => void
  onError: (message: string) => void
}

/**
 * 旅行对话助手(SSE 流式)。
 * 用 fetch 读取 Server-Sent Events,答案逐字返回。
 */
export async function streamChat(
  message: string,
  history: ChatMessage[],
  callbacks: StreamCallbacks
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(authState.token ? { Authorization: `Bearer ${authState.token}` } : {}),
    },
    body: JSON.stringify({ message, chat_history: history }),
  })

  if (!res.ok || !res.body) {
    throw new Error(`流式请求失败(${res.status})`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const payload = JSON.parse(line.slice(6))
        if (payload.delta) callbacks.onDelta(payload.delta)
        if (payload.done) callbacks.onDone(payload.sources || [], payload.related || [])
        if (payload.error) callbacks.onError(payload.error)
      } catch {
        // 忽略无法解析的行
      }
    }
  }
}

// ============================================================
// 后台管理接口(需管理员)
// ============================================================

/** 仪表盘统计。 */
export async function getAdminStats(): Promise<AdminStats> {
  const response = await apiClient.get<AdminStats>('/api/admin/stats')
  return response.data
}

/** 用户列表。 */
export async function listAdminUsers(): Promise<AdminUserItem[]> {
  const response = await apiClient.get<{ data: AdminUserItem[] }>('/api/admin/users')
  return response.data.data
}

/** 启用/禁用用户。 */
export async function updateUserStatus(userId: number, status: 'active' | 'disabled'): Promise<void> {
  await apiClient.patch(`/api/admin/users/${userId}/status`, null, { params: { status } })
}

/** 知识库条目列表。 */
export async function listKb(limit = 100): Promise<KBItem[]> {
  const response = await apiClient.get<{ data: KBItem[] }>('/api/admin/kb', { params: { limit } })
  return response.data.data
}

/** 删除知识条目。 */
export async function deleteKb(kbId: string): Promise<void> {
  await apiClient.delete(`/api/admin/kb/${kbId}`)
}

/** 知识条目提交体(新增/修改)。 */
export interface KBPayload {
  text: string
  category: string
  title: string
  source: string
  poi_name: string
}

/** 新增知识条目。 */
export async function addKb(payload: KBPayload): Promise<void> {
  await apiClient.post('/api/admin/kb', payload)
}

/** 修改知识条目。 */
export async function updateKb(kbId: string, payload: KBPayload): Promise<void> {
  await apiClient.put(`/api/admin/kb/${kbId}`, payload)
}

/** 批量导入知识文件(.md/.json/.txt)。 */
export async function importKbFiles(files: File[]): Promise<{ success: boolean; message: string; imported: number; skipped: number }> {
  const formData = new FormData()
  files.forEach((f) => formData.append('files', f))
  const response = await apiClient.post('/api/admin/kb/import', formData)
  return response.data
}

/**
 * 获取景点图片 URL(需登录)。
 */
export async function getAttractionPhoto(name: string, city: string): Promise<string | null> {
  try {
    const response = await apiClient.get<{ success: boolean; data: { photo_url: string | null } }>(
      '/api/poi/photo',
      { params: { name, city } }
    )
    return response.data.data?.photo_url || null
  } catch (error) {
    console.error(`获取${name}图片失败:`, error)
    return null
  }
}

/**
 * 健康检查:确认后端是否在线。
 */
export async function healthCheck(): Promise<any> {
  try {
    const response = await apiClient.get('/health')
    return response.data
  } catch (error: any) {
    console.error('健康检查失败:', error)
    throw new Error(error.message || '健康检查失败')
  }
}

export default apiClient
