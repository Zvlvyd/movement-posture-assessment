<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useMessage } from 'naive-ui'
import {
  NCard, NForm, NFormItem, NInput, NButton, NSpace, NText, NIcon
} from 'naive-ui'
import { PersonOutline, LockClosedOutline } from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const message = useMessage()

const loading = ref(false)
const formRef = ref()
const formData = ref({
  username: '',
  password: ''
})

const rules: Record<string, any> = {
  username: {
    required: true,
    message: '请输入用户名',
    trigger: 'blur'
  },
  password: {
    required: true,
    message: '请输入密码',
    trigger: 'blur',
    min: 6,
    type: 'string'
  }
}

async function handleLogin() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  try {
    await authStore.login(formData.value.username, formData.value.password)
    message.success('登录成功')
    // 等待下一个 tick，确保状态更新完成
    await nextTick()
    const roleHome = authStore.user?.role === 'admin' ? '/admin' : authStore.user?.role === 'coach' ? '/coach' : '/home'
    const redirect = (route.query.redirect as string) || roleHome
    router.push(redirect)
  } catch (e: any) {
    message.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}

function goRegister() {
  router.push('/register')
}
</script>

<template>
  <div class="login-container">
    <div class="login-bg">
      <div class="bg-shape shape-1"></div>
      <div class="bg-shape shape-2"></div>
      <div class="bg-shape shape-3"></div>
    </div>

    <div class="login-card-wrapper">
      <n-card class="login-card" :bordered="false" :show-header="false">
        <div class="login-header">
          <div class="logo-circle">
            <img
              src="/media/pictures/transport.jpg"
              alt="运动体态评估与纠错系统"
              class="logo-image"
            >
          </div>
          <h1 class="system-title">运动体态评估与纠错系统</h1>
          <p class="system-subtitle">专业的运动姿态分析与训练平台</p>
        </div>

        <n-form
          ref="formRef"
          :model="formData"
          :rules="rules"
          label-placement="top"
          size="large"
          class="login-form"
        >
          <n-form-item label="用户名" path="username">
            <n-input
              v-model:value="formData.username"
              placeholder="请输入用户名"
              clearable
            >
              <template #prefix>
                <n-icon :component="PersonOutline" />
              </template>
            </n-input>
          </n-form-item>

          <n-form-item label="密码" path="password">
            <n-input
              v-model:value="formData.password"
              type="password"
              placeholder="请输入密码"
              show-password-on="click"
              @keyup.enter="handleLogin"
            >
              <template #prefix>
                <n-icon :component="LockClosedOutline" />
              </template>
            </n-input>
          </n-form-item>

          <n-button
            type="primary"
            block
            size="large"
            :loading="loading"
            @click="handleLogin"
            class="login-btn"
          >
            登录
          </n-button>
        </n-form>

        <div class="login-footer">
          <n-space justify="center">
            <n-text depth="3" class="register-text">
              还没有账号？
              <span class="register-link" @click="goRegister">立即注册</span>
            </n-text>
          </n-space>
        </div>
      </n-card>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
}

.bg-shape {
  position: absolute;
  border-radius: 50%;
  opacity: 0.1;
  background: white;
}

.shape-1 {
  width: 400px;
  height: 400px;
  top: -100px;
  right: -100px;
  animation: float 8s ease-in-out infinite;
}

.shape-2 {
  width: 300px;
  height: 300px;
  bottom: -50px;
  left: -50px;
  animation: float 10s ease-in-out infinite reverse;
}

.shape-3 {
  width: 200px;
  height: 200px;
  top: 50%;
  left: 30%;
  animation: float 6s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, -30px); }
}

.login-card-wrapper {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 500px;
  padding: 24px;
}

.login-card {
  border-radius: 20px !important;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25) !important;
  padding: 52px 44px 48px !important;
  backdrop-filter: blur(10px);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo-circle {
  width: 88px;
  height: 88px;
  margin: -44px auto 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20px;
  overflow: hidden;
  color: white;
  box-shadow:
    0 10px 24px rgba(102, 126, 234, 0.38),
    0 0 22px rgba(118, 75, 162, 0.3);
  animation: logo-float 4s ease-in-out infinite;
}

@keyframes logo-float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}

.logo-image {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.system-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 8px 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.system-subtitle {
  font-size: 14px;
  color: #64748b;
  margin: 0;
}

.login-form {
  margin-bottom: 24px;
}

.login-btn {
  margin-top: 8px;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  border: none !important;
  box-shadow: 0 4px 15px -3px rgba(102, 126, 234, 0.4);
}

.login-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px -3px rgba(102, 126, 234, 0.5);
}

.login-footer {
  text-align: center;
}

.register-text {
  font-size: 14px;
}

.register-link {
  color: #667eea;
  cursor: pointer;
  font-weight: 500;
  margin-left: 4px;
}

.register-link:hover {
  text-decoration: underline;
}

@media (max-width: 480px) {
  .login-card-wrapper {
    padding: 16px;
  }

  .login-card {
    padding: 32px 24px !important;
  }

  .logo-circle {
    width: 80px;
    height: 80px;
    margin: -22px auto 16px;
  }

  .system-title {
    font-size: 18px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .logo-circle {
    animation: none;
  }
}
</style>
