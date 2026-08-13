/**
 * 环境变量的类型声明文件。
 *
 * 在前端代码里,我们可以用 import.meta.env.XXX 读取 .env 文件里定义的变量
 * (注意:只有以 VITE_ 开头的变量才会暴露给前端使用,这是 Vite 的规定)。
 *
 * 但 TypeScript 默认不知道 import.meta.env 上有哪些字段,会报类型错误。
 * 这个文件就是"手写说明书",告诉 TS:import.meta.env 上到底有哪些变量、是什么类型,
 * 这样编辑器就能给出补全提示,也不会报错。
 */

/// <reference types="vite/client" />   // 引入 Vite 自带的类型定义

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string   // 后端接口地址(可选的,问号表示可能没有)
  readonly VITE_AMAP_WEB_JS_KEY: string // 高德地图 Web 端(JS API)的 Key(必填)
}

interface ImportMeta {
  readonly env: ImportMetaEnv   // 声明 import.meta.env 的结构
}
