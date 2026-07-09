<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useMessage } from 'naive-ui'
import {
  NCard, NForm, NFormItem, NInput, NButton, NSpace, NText, NSelect, NIcon
} from 'naive-ui'
import { BodyOutline, PersonOutline, LockClosedOutline, CallOutline, MaleFemaleOutline } from '@vicons/ionicons5'

const router = useRouter()
const authStore = useAuthStore()
const message = useMessage()

const loading = ref(false)
const formRef = ref()
const formData = ref({
  username: '',
  password: '',
  confirmPassword: '',
  phone: '',
  gender: 'male',
  role: 'trainee'
})

const genderOptions = [
  { label: '男', value: 'male' },
  { label: '女', value: 'female' }
]

const roleOptions = [
  { label: '训练者', value: 'trainee' },
  { label: '教练', value: 'coach' }
]

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
  },
  confirmPassword: {
    required: true,
    message: '请再次输入密码',
    trigger: 'blur',
    validator: (_rule: any, value: string) => {
      if (value !== formData.value.password) {
        return new Error('两次密码输入不一致')
      }
      return true
    }
  }
}

async function handleRegister() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  try {
    await authStore.register(
      formData.value.username,
      formData.value.password,
      formData.value.phone || undefined,
      formData.value.gender,
      formData.value.role
    )
    message.success('注册成功，请登录')
    router.push('/login')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}

function goLogin() {
  router.push('/login')
}
</script>

<template>
  <div class="register-container">
    <div class="register-bg">
      <div class="bg-shape shape-1"></div>
      <div class="bg-shape shape-2"></div>
      <div class="bg-shape shape-3"></div>
    </div>

    <div class="register-card-wrapper">
      <n-card class="register-card" :bordered="false" :show-header="false">
        <div class="register-header">
          <div class="logo-circle">
            <n-icon size="32" :component="BodyOutline" />
          </div>
          <h1 class="system-title">创建账号</h1>
          <p class="system-subtitle">加入运动体态评估与纠错系统</p>
        </div>

        <n-form
          ref="formRef"
          :model="formData"
          :rules="rules"
          label-placement="top"
          size="medium"
          class="register-form"
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
              placeholder="至少6位字符"
              show-password-on="click"
            >
              <template #prefix>
                <n-icon :component="LockClosedOutline" />
              </template>
            </n-input>
          </n-form-item>

          <n-form-item label="确认密码" path="confirmPassword">
            <n-input
              v-model:value="formData.confirmPassword"
              type="password"
              placeholder="再次输入密码"
              show-password-on="click"
              @keyup.enter="handleRegister"
            >
              <template #prefix>
                <n-icon :component="LockClosedOutline" />
              </template>
            </n-input>
          </n-form-item>

          <n-form-item label="手机号" path="phone">
            <n-input
              v-model:value="formData.phone"
              placeholder="选填"
              clearable
            >
              <template #prefix>
                <n-icon :component="CallOutline" />
              </template>
            </n-input>
          </n-form-item>

          <n-form-item label="性别" path="gender">
            <n-select
              v-model:value="formData.gender"
              :options="genderOptions"
            />
          </n-form-item>

          <n-form-item label="注册角色" path="role">
            <n-select
              v-model:value="formData.role"
              :options="roleOptions"
            />
          </n-form-item>

          <n-button
            type="primary"
            block
            size="large"
            :loading="loading"
            @click="handleRegister"
            class="register-btn"
          >
            注册
          </n-button>
        </n-form>

        <div class="register-footer">
          <n-space justify="center">
            <n-text depth="3" class="login-text">
              已有账号？
              <span class="login-link" @click="goLogin">立即登录</span>
            </n-text>
          </n-space>
        </div>
      </n-card>
    </div>
  </div>
</template>

<style scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-bg {
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

.register-card-wrapper {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 440px;
  padding: 20px;
}

.register-card {
  border-radius: 20px !important;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25) !important;
  padding: 36px 32px !important;
  backdrop-filter: blur(10px);
}

.register-header {
  text-align: center;
  margin-bottom: 28px;
}

.logo-circle {
  width: 64px;
  height: 64px;
  margin: 0 auto 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 18px;
  color: white;
  box-shadow: 0 10px 30px -5px rgba(102, 126, 234, 0.5);
}

.system-title {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 6px 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.system-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.register-form {
  margin-bottom: 20px;
}

.register-btn {
  margin-top: 8px;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  border: none !important;
  box-shadow: 0 4px 15px -3px rgba(102, 126, 234, 0.4);
}

.register-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px -3px rgba(102, 126, 234, 0.5);
}

.register-footer {
  text-align: center;
}

.login-text {
  font-size: 14px;
}

.login-link {
  color: #667eea;
  cursor: pointer;
  font-weight: 500;
  margin-left: 4px;
}

.login-link:hover {
  text-decoration: underline;
}

@media (max-width: 480px) {
  .register-card {
    padding: 28px 20px !important;
  }

  .system-title {
    font-size: 18px;
  }
}
</style>
