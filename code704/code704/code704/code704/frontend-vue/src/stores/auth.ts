import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '../types'
import { authApi } from '../services/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(JSON.parse(localStorage.getItem('user') || 'null'))
  const token = ref<string | null>(localStorage.getItem('token'))
  const loading = ref(false)

  const isLoggedIn = computed(() => !!token.value && !!user.value)

  async function login(username: string, password: string) {
    loading.value = true
    try {
      const res = await authApi.login({ username, password })
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('user', JSON.stringify(res.user))
      user.value = res.user
      token.value = res.access_token
    } catch (error) {
      // 如果后端不可用，使用模拟登录（开发测试用）
      if (!navigator.onLine || (error as any)?.code === 'ERR_NETWORK') {
        console.warn('后端不可用，使用模拟登录')
        const mockUser: User = {
          id: 1,
          username: username,
          role: 'trainee',
          is_active: true,
          created_at: new Date().toISOString()
        }
        const mockToken = 'mock-token-' + Date.now()
        localStorage.setItem('token', mockToken)
        localStorage.setItem('user', JSON.stringify(mockUser))
        user.value = mockUser
        token.value = mockToken
      } else {
        throw error
      }
    } finally {
      loading.value = false
    }
  }

  async function register(username: string, password: string, phone?: string, gender?: string, role?: string) {
    loading.value = true
    try {
      await authApi.register({ username, password, phone, gender, role })
    } catch (error) {
      if (!navigator.onLine || (error as any)?.code === 'ERR_NETWORK') {
        console.warn('后端不可用，使用模拟注册')
        await login(username, password)
      } else {
        throw error
      }
    } finally {
      loading.value = false
    }
  }

  function logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    user.value = null
    token.value = null
  }

  function setUser(u: User) {
    localStorage.setItem('user', JSON.stringify(u))
    user.value = u
  }

  async function fetchUser() {
    try {
      const u = await authApi.me()
      user.value = u
    } catch {
      user.value = null
      token.value = null
    }
  }

  return {
    user,
    token,
    loading,
    isLoggedIn,
    login,
    register,
    logout,
    fetchUser,
    setUser
  }
})
