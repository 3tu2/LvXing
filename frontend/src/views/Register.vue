<template>
  <div class="auth-container">
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
    </div>

    <div class="auth-card-wrap">
      <div class="brand">
        <GlobalOutlined class="brand-icon" />
        <h1 class="brand-title">创建账号</h1>
        <p class="brand-subtitle">加入南昌旅行助手,开启个性化旅程</p>
      </div>

      <a-card :bordered="false" class="auth-card">
        <a-form :model="form" layout="vertical" @finish="handleRegister">
          <a-form-item
            name="username"
            :rules="[
              { required: true, message: '请输入用户名' },
              { min: 3, max: 30, message: '用户名需 3~30 个字符' }
            ]"
          >
            <a-input v-model:value="form.username" size="large" placeholder="用户名(3~30 个字符)" allow-clear>
              <template #prefix><UserOutlined /></template>
            </a-input>
          </a-form-item>

          <a-form-item
            name="nickname"
            :rules="[{ max: 30, message: '昵称最多 30 个字符' }]"
          >
            <a-input v-model:value="form.nickname" size="large" placeholder="昵称(可选,默认同用户名)" allow-clear>
              <template #prefix><SmileOutlined /></template>
            </a-input>
          </a-form-item>

          <a-form-item
            name="password"
            :rules="[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少 6 位' }
            ]"
          >
            <a-input-password v-model:value="form.password" size="large" placeholder="密码(至少 6 位)" allow-clear>
              <template #prefix><LockOutlined /></template>
            </a-input-password>
          </a-form-item>

          <a-form-item
            name="confirm"
            :rules="[
              { required: true, message: '请再次输入密码' },
              { validator: validateConfirm }
            ]"
          >
            <a-input-password v-model:value="form.confirm" size="large" placeholder="确认密码" allow-clear>
              <template #prefix><LockOutlined /></template>
            </a-input-password>
          </a-form-item>

          <a-button type="primary" html-type="submit" size="large" block :loading="loading" class="submit-btn">
            注册
          </a-button>
        </a-form>

        <div class="auth-footer">
          已有账号?<a class="link" @click="router.push('/login')">去登录</a>
        </div>
      </a-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { GlobalOutlined, UserOutlined, LockOutlined, SmileOutlined } from '@ant-design/icons-vue'
import { registerUser } from '@/services/api'
import { setAuth } from '@/services/auth'

const router = useRouter()
const loading = ref(false)
const form = reactive({ username: '', nickname: '', password: '', confirm: '' })

// 自定义校验:两次密码一致
const validateConfirm = async (_rule: any, value: string) => {
  if (value && value !== form.password) {
    return Promise.reject('两次输入的密码不一致')
  }
  return Promise.resolve()
}

const handleRegister = async () => {
  loading.value = true
  try {
    const res = await registerUser({
      username: form.username,
      password: form.password,
      nickname: form.nickname || undefined,
    })
    if (res.success && res.token && res.user) {
      setAuth(res.token, res.user)
      message.success('注册成功!')
      router.push(res.user.role === 'admin' ? '/admin' : '/')
    } else {
      message.error(res.message || '注册失败')
    }
  } catch (e: any) {
    message.error(e.message || '注册失败')
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
.circle-1 { width: 300px; height: 300px; top: -100px; right: -100px; }
.circle-2 { width: 240px; height: 240px; bottom: -80px; left: -60px; animation-delay: 6s; }
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
