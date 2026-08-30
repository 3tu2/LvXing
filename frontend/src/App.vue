<template>
  <!-- 根组件:整个应用的"外壳",负责搭出整体页面布局 -->
  <div id="app">
    <!-- a-config-provider 用于统一设置全局主题(把 Ant Design 默认的蓝色改成薄荷绿) -->
    <a-config-provider :theme="themeConfig">
      <!-- a-layout 是 Ant Design Vue 的布局组件,用来搭"上中下"结构 -->
      <a-layout style="min-height: 100vh; background: #f7fbfa">
        <!-- 顶部导航栏 -->
        <a-layout-header class="app-header">
          <div class="app-logo" @click="goHome"><GlobalOutlined class="app-logo-icon" />南昌旅行助手</div>

          <!-- 右侧:旅行助手入口 + 登录态 -->
          <div class="app-actions">
            <!-- 旅行助手入口:仅普通用户(管理员只进后台) -->
            <a-button
              v-if="authState.user?.role !== 'admin'"
              type="text"
              class="chat-entry"
              @click="router.push('/chat')"
            >
              <MessageOutlined /> 旅行助手
            </a-button>
            <template v-if="authState.user">
              <a-dropdown>
                <span class="user-trigger">
                  <a-avatar size="small" class="user-avatar">{{ initial }}</a-avatar>
                  <span class="user-name">{{ authState.user.nickname }}</span>
                  <DownOutlined class="user-caret" />
                </span>
                <template #overlay>
                  <a-menu>
                    <a-menu-item v-if="authState.user?.role !== 'admin'" key="trips" @click="router.push('/trips')">
                      <HistoryOutlined /> 我的行程
                    </a-menu-item>
                    <a-menu-item v-if="authState.user?.role === 'admin'" key="admin" @click="router.push('/admin')">
                      <SettingOutlined /> 后台管理
                    </a-menu-item>
                    <a-menu-item key="logout" @click="handleLogout">
                      <LogoutOutlined /> 退出登录
                    </a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
            </template>
            <template v-else>
              <a-space>
                <a-button type="text" @click="router.push('/login')">登录</a-button>
                <a-button type="primary" @click="router.push('/register')">注册</a-button>
              </a-space>
            </template>
          </div>
        </a-layout-header>

        <!-- 中间内容区:真正显示哪个页面,由路由决定 -->
        <a-layout-content style="padding: 0">
          <!-- router-view 是个"占位符",会根据当前网址自动换成对应的页面组件 -->
          <router-view />
        </a-layout-content>

        <!-- 底部页脚 -->
        <a-layout-footer class="app-footer">
          南昌旅行助手 ©2026
        </a-layout-footer>
      </a-layout>
    </a-config-provider>
  </div>
</template>

<script setup lang="ts">
// 根组件负责布局、全局主题与顶栏登录态。
// <script setup> 是 Vue3 的"组合式 API"写法。

import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { GlobalOutlined, LogoutOutlined, DownOutlined, HistoryOutlined, MessageOutlined, SettingOutlined } from '@ant-design/icons-vue'
import { authState, clearAuth } from './services/auth'

const router = useRouter()

// 头像显示的单个字符(取昵称/用户名的首字)
const initial = computed(() =>
  (authState.user?.nickname || authState.user?.username || '?').slice(0, 1)
)

// 回到各自首页:管理员进后台,普通用户进首页
const goHome = () => {
  router.push(authState.user?.role === 'admin' ? '/admin' : '/')
}

// 退出登录:清空本地登录态并回登录页
const handleLogout = () => {
  clearAuth()
  message.success('已退出登录')
  router.push('/login')
}

// 全局主题配置:把品牌主色统一定为薄荷绿,圆角更柔和。
const themeConfig = {
  token: {
    colorPrimary: '#0ea5a4',
    colorInfo: '#0ea5a4',
    borderRadius: 10,
  },
}
</script>

<style>
/* 全局样式:设置整个应用的基础字体与配色 */
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif;
  background: #f7fbfa;
}

/* 顶部导航栏:白底 + 薄荷绿标题,清爽轻盈 */
.app-header {
  background: #ffffff;
  padding: 0 50px;
  border-bottom: 1px solid #e6f4f1;
  box-shadow: 0 2px 12px rgba(14, 165, 164, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.app-logo {
  color: #0ea5a4;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: 1px;
  cursor: pointer;
}

.app-logo-icon {
  margin-right: 8px;
  font-size: 26px;
  vertical-align: -3px;
}

/* 右侧登录态区域 */
.app-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-entry {
  color: #0ea5a4;
  font-weight: 600;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  transition: background 0.2s;
}
.user-trigger:hover {
  background: #f0fdfa;
}
.user-avatar {
  background: #0ea5a4;
}
.user-name {
  font-size: 15px;
  font-weight: 600;
  color: #334155;
}
.user-caret {
  font-size: 12px;
  color: #94a3b8;
}

/* 底部页脚 */
.app-footer {
  text-align: center;
  color: #94a3b8;
  background: transparent;
}
</style>
