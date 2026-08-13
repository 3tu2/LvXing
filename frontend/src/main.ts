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

// 创建路由:history 模式表示用干净的网址(不带 # 号)
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',          // 访问 http://localhost:5173/ 时
      name: 'Home',
      component: Home     // 显示首页
    },
    {
      path: '/result',    // 访问 http://localhost:5173/result 时
      name: 'Result',
      component: Result   // 显示结果页
    }
  ]
})

// 创建 Vue 应用实例,根组件是 App.vue
const app = createApp(App)

// 安装插件(把路由和组件库注册到应用里,之后就能用 <router-view>、<a-button> 等)
app.use(router)
app.use(Antd)

// 把应用挂载到 index.html 中 <div id="app"></div> 这个元素上
app.mount('#app')
