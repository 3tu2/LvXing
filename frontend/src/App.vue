<template>
  <!-- 根组件:整个应用的"外壳",负责搭出整体页面布局 -->
  <div id="app">
    <!-- a-config-provider 用于统一设置全局主题(把 Ant Design 默认的蓝色改成薄荷绿) -->
    <a-config-provider :theme="themeConfig">
      <!-- a-layout 是 Ant Design Vue 的布局组件,用来搭"上中下"结构 -->
      <a-layout style="min-height: 100vh; background: #f7fbfa">
        <!-- 顶部导航栏 -->
        <a-layout-header class="app-header">
          <div class="app-logo"><GlobalOutlined class="app-logo-icon" />智能旅行助手</div>
        </a-layout-header>

        <!-- 中间内容区:真正显示哪个页面,由路由决定 -->
        <a-layout-content style="padding: 0">
          <!-- router-view 是个"占位符",会根据当前网址自动换成对应的页面组件 -->
          <router-view />
        </a-layout-content>

        <!-- 底部页脚 -->
        <a-layout-footer class="app-footer">
          智能旅行助手 ©2026
        </a-layout-footer>
      </a-layout>
    </a-config-provider>
  </div>
</template>

<script setup lang="ts">
// 根组件本身没有额外逻辑,只负责布局和全局主题。
// <script setup> 是 Vue3 的"组合式 API"写法,里面写的代码会在组件加载时执行。

import { GlobalOutlined } from '@ant-design/icons-vue'  // 地球图标(品牌 logo)

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
}

.app-logo {
  color: #0ea5a4;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: 1px;
}

.app-logo-icon {
  margin-right: 8px;
  font-size: 26px;
  vertical-align: -3px;
}

/* 底部页脚 */
.app-footer {
  text-align: center;
  color: #94a3b8;
  background: transparent;
}
</style>
