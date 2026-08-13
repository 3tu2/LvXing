/**
 * Vite 构建工具的配置文件。
 *
 * Vite 是前端的"打包 + 开发服务器"工具,这个文件用来配置它的一些行为:
 * 1. 使用 Vue 插件;
 * 2. 路径别名:@ 指向 src 目录(这样能写 import xx from '@/xxx',代替难写的相对路径);
 * 3. 开发服务器端口、以及"代理"(把 /api 开头的请求转发给后端)。
 */

import { defineConfig } from 'vite'     // defineConfig 能提供类型提示和校验
import vue from '@vitejs/plugin-vue'    // 让 Vite 能处理 .vue 文件
import { resolve } from 'path'          // Node 的路径工具,用来拼绝对路径

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],   // 启用 Vue 插件

  resolve: {
    alias: {
      // 路径别名:@ 代表 src 目录。
      // 例如 import xx from '@/services/api' 实际指向 src/services/api.ts
      // 注意:这里的配置要和 tsconfig.json 里的 "paths" 保持一致,两边都要配。
      '@': resolve(__dirname, 'src')
    }
  },

  server: {
    port: 5173,   // 开发服务器端口(前端访问地址:http://localhost:5173)
    proxy: {
      // 代理:当前端请求以 /api 开头时,Vite 会帮忙转发到后端
      '/api': {
        target: 'http://localhost:8000',  // 后端地址
        changeOrigin: true                 // 修改请求的 Origin,避免跨域问题
      }
    }
  }
})
