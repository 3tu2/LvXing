/**
 * 认证状态工具:负责 token 与用户信息的本地存储与全局响应式状态。
 *
 * 说明:项目未引入 Pinia,这里用 Vue 的 reactive 维护一份全局登录态,
 * 登录/登出后所有引用 authState 的组件(如 App.vue 顶栏)会自动更新。
 * token 与用户信息同时持久化到 localStorage,刷新页面后仍保持登录。
 */

import { reactive } from 'vue'
import type { User } from '@/types'

const TOKEN_KEY = 'nanchang_travel_token'
const USER_KEY = 'nanchang_travel_user'

// 从 localStorage 恢复(处理非法 JSON 的容错)
function readUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

/** 全局响应式登录态(组件可直接引用 authState.user / authState.token)。 */
export const authState = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',
  user: readUser(),
})

/** 登录/注册成功后调用:写入 token 与用户信息。 */
export function setAuth(token: string, user: User) {
  authState.token = token
  authState.user = user
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

/** 登出:清空 token 与用户信息。 */
export function clearAuth() {
  authState.token = ''
  authState.user = null
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

/** 是否已登录。 */
export function isLoggedIn(): boolean {
  return !!authState.token
}
