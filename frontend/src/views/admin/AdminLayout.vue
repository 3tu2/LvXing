<template>
  <a-layout class="admin-layout">
    <!-- 侧边栏 -->
    <a-layout-sider class="admin-sider" width="220">
      <div class="admin-logo">南昌旅行助手 · 后台</div>
      <a-menu mode="inline" v-model:selectedKeys="selected" class="admin-menu">
        <a-menu-item key="dashboard">
          <DashboardOutlined /> 仪表盘
        </a-menu-item>
        <a-menu-item key="users">
          <TeamOutlined /> 用户管理
        </a-menu-item>
        <a-menu-item key="kb">
          <DatabaseOutlined /> 知识库
        </a-menu-item>
      </a-menu>
      <div class="admin-back">
        <a-button type="text" block @click="handleLogout">
          <LogoutOutlined /> 退出登录
        </a-button>
      </div>
    </a-layout-sider>

    <!-- 内容区 -->
    <a-layout-content class="admin-content">
      <Dashboard v-if="selected[0] === 'dashboard'" />
      <Users v-else-if="selected[0] === 'users'" />
      <KBManage v-else />
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
// 后台管理布局:侧边菜单 + 内容区(tab 切换三个子模块)。
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { DashboardOutlined, TeamOutlined, DatabaseOutlined, LogoutOutlined } from '@ant-design/icons-vue'
import { clearAuth } from '@/services/auth'
import Dashboard from './Dashboard.vue'
import Users from './Users.vue'
import KBManage from './KBManage.vue'

const router = useRouter()
const selected = ref<string[]>(['dashboard'])

const handleLogout = () => {
  clearAuth()
  message.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.admin-layout {
  min-height: 100vh;
}
.admin-sider {
  background: #0f766e;
}
.admin-logo {
  color: #fff;
  font-weight: 700;
  padding: 20px 16px;
  font-size: 16px;
}
.admin-menu {
  background: transparent;
  color: #d1fae5;
}
.admin-menu :deep(.ant-menu-item) {
  color: #d1fae5;
}
.admin-menu :deep(.ant-menu-item-selected) {
  background: #0ea5a4;
  color: #fff;
}
.admin-back {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}
.admin-content {
  background: #f0fdfa;
  overflow: auto;
}
</style>
