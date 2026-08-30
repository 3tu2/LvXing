/**
 * 前端入口文件。
 *
 * 这是整个前端应用的"启动点"。当浏览器加载 index.html 时,会通过
 * <script type="module" src="/src/main.ts"> 引入本文件,从这里开始执行。
 *
 * 它做了三件事:
 * 1. 创建"路由"(router):规定哪个网址显示哪个页面;
 * 2. 创建 Vue 应用,并安装路由、Ant Design Vue 组件库;
 * 3. 把应用"挂载"到页面上 id 为 app 的元素里。
 *
 * 小白可以这样理解:这就好比盖房子的"奠基 + 安装水电管线 + 挂牌"。
 */

import { createApp } from 'vue'                      // 创建 Vue 应用
import { createRouter, createWebHistory } from 'vue-router'  // 创建路由
import Antd from 'ant-design-vue'                    // Ant Design Vue 组件库(按钮、表单等)
import 'ant-design-vue/dist/reset.css'               // 组件库的基础样式
import App from './App.vue'                          // 根组件(整个页面的外壳)
import Home from './views/Home.vue'                  // 首页(填写旅行需求)
import Result from './views/Result.vue'              // 结果页(展示旅行计划)
import Login from './views/Login.vue'                // 登录页
import Register from './views/Register.vue'          // 注册页
import MyTrips from './views/MyTrips.vue'            // 我的行程页
import Chat from './views/Chat.vue'                  // 旅行对话助手
import AdminLayout from './views/admin/AdminLayout.vue'  // 后台管理
import { isLoggedIn, authState } from './services/auth'  // 登录态(路由守卫用)

// 创建路由:history 模式表示用干净的网址(不带 # 号)
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',          // 访问 http://localhost:5173/ 时
      name: 'Home',
      component: Home,     // 显示首页
      meta: { requiresAuth: true, userOnly: true }  // 需登录且仅普通用户
    },
    {
      path: '/result',    // 访问 http://localhost:5173/result 时
      name: 'Result',
      component: Result,   // 显示结果页
      meta: { requiresAuth: true, userOnly: true }  // 需登录且仅普通用户
    },
    {
      path: '/login',
      name: 'Login',
      component: Login,
      meta: { guestOnly: true }  // 已登录用户访问则跳回首页/后台
    },
    {
      path: '/register',
      name: 'Register',
      component: Register,
      meta: { guestOnly: true }
    },
    {
      path: '/trips',      // 我的行程(需登录,仅普通用户)
      name: 'MyTrips',
      component: MyTrips,
      meta: { requiresAuth: true, userOnly: true }
    },
    {
      path: '/chat',       // 旅行对话助手(需登录,仅普通用户)
      name: 'Chat',
      component: Chat,
      meta: { requiresAuth: true, userOnly: true }
    },
    {
      path: '/admin',      // 后台管理(需管理员)
      name: 'Admin',
      component: AdminLayout,
      meta: { requiresAuth: true, requiresAdmin: true }
    }
  ]
})

// 全局路由守卫:每次跳转前执行
// 1) 访问需要登录的页面(meta.requiresAuth)但未登录 → 跳登录页;
// 2) 访问需管理员页面(meta.requiresAdmin)但非管理员 → 跳首页;
// 3) 前台页面(meta.userOnly)仅普通用户可访问,管理员访问 → 跳后台;
// 4) 已登录用户访问登录/注册页(meta.guestOnly) → 按角色跳首页或后台。
router.beforeEach((to) => {
  const loggedIn = isLoggedIn()
  const role = authState.user?.role

  if (to.meta.requiresAuth && !loggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && role !== 'admin') {
    return { path: '/' }
  }
  if (to.meta.userOnly && role === 'admin') {
    return { path: '/admin' }
  }
  if (to.meta.guestOnly && loggedIn) {
    return { path: role === 'admin' ? '/admin' : '/' }
  }
  return true
})

// 创建 Vue 应用实例,根组件是 App.vue
const app = createApp(App)

// 安装插件(把路由和组件库注册到应用里,之后就能用 <router-view>、<a-button> 等)
app.use(router)
app.use(Antd)

// 把应用挂载到 index.html 中 <div id="app"></div> 这个元素上
app.mount('#app')
