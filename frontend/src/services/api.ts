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
import type { TripFormData, TripPlanResponse } from '@/types'  // 导入类型(用 @ 别名引用 src 目录)

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
    // 打印请求方法(GET/POST)和地址,方便调试
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
    return Promise.reject(error)
  }
)

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
