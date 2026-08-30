<template>
  <div class="auth-container">
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
    </div>

    <div class="auth-card-wrap">
      <div class="brand">
        <GlobalOutlined class="brand-icon" />
        <h1 class="brand-title">南昌旅行助手</h1>
        <p class="brand-subtitle">登录后,你的行程与偏好将被记住</p>
      </div>

      <a-card :bordered="false" class="auth-card">
        <a-form :model="form" layout="vertical" @finish="handleLogin">
          <a-form-item name="username" :rules="[{ required: true, message: '请输入用户名' }]">
            <a-input v-model:value="form.username" size="large" placeholder="用户名" allow-clear>
              <template #prefix><UserOutlined /></template>
            </a-input>
          </a-form-item>

          <a-form-item name="password" :rules="[{ required: true, message: '请输入密码' }]">
            <a-input-password v-model:value="form.password" size="large" placeholder="密码" allow-clear>
              <template #prefix><LockOutlined /></template>
            </a-input-password>
          </a-form-item>

          <a-button type="primary" html-type="submit" size="large" block :loading="loading" class="submit-btn">
            登录
          </a-button>
        </a-form>

        <div class="auth-footer">
          还没有账号?<a class="link" @click="router.push('/register')">立即注册</a>
        </div>
      </a-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { GlobalOutlined, UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import { loginUser } from '@/services/api'
import { setAuth } from '@/services/auth'

const router = useRouter()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const handleLogin = async () => {
  loading.value = true
  try {
    const res = await loginUser({ username: form.username, password: form.password })
    if (res.success && res.token && res.user) {
      setAuth(res.token, res.user)
      message.success(`欢迎回来,${res.user.nickname}!`)
      // 管理员进后台,普通用户进首页
      router.push(res.user.role === 'admin' ? '/admin' : '/')
    } else {
      message.error(res.message || '登录失败')
    }
  } catch (e: any) {
    message.error(e.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e6fffa 0%, #f0fdfa 100%);
  position: relative;
  overflow: hidden;
  padding: 24px;
}
.bg-decoration { position: absolute; inset: 0; pointer-events: none; overflow: hidden; }
.circle { position: absolute; border-radius: 50%; background: rgba(14, 165, 164, 0.08); animation: float 20s infinite ease-in-out; }
.circle-1 { width: 300px; height: 300px; top: -100px; left: -100px; }
.circle-2 { width: 240px; height: 240px; bottom: -80px; right: -60px; animation-delay: 6s; }
@keyframes float { 0%,100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-30px) rotate(180deg); } }

.auth-card-wrap { position: relative; z-index: 1; width: 100%; max-width: 400px; }
.brand { text-align: center; margin-bottom: 24px; }
.brand-icon { font-size: 52px; color: #0ea5a4; }
.brand-title { font-size: 30px; font-weight: 800; color: #0f766e; margin: 12px 0 6px; }
.brand-subtitle { font-size: 14px; color: #64748b; margin: 0; }

.auth-card { border-radius: 20px; box-shadow: 0 20px 50px rgba(13, 148, 136, 0.18); }
.submit-btn { height: 48px; border-radius: 12px; font-size: 16px; font-weight: 600; background: linear-gradient(135deg, #0ea5a4 0%, #10b981 100%); border: none; }
.auth-footer { margin-top: 16px; text-align: center; color: #64748b; font-size: 14px; }
.link { color: #0ea5a4; cursor: pointer; font-weight: 600; }
</style>
