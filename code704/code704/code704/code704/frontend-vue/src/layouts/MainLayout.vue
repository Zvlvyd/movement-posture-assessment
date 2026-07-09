<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, h, onErrorCaptured, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { coachApi, messageApi } from '../services/api'
import { NAlert } from 'naive-ui'
import {
  NLayout, NLayoutHeader, NLayoutSider, NLayoutContent, NLayoutFooter,
  NMenu, NButton, NDropdown, NAvatar, NSpace, NIcon
} from 'naive-ui'
import {
  HomeOutline, BodyOutline, AnalyticsOutline, PlayCircleOutline,
  ListOutline, BookOutline, CheckmarkCircleOutline, PersonOutline,
  PeopleOutline, SettingsOutline, LogOutOutline,
  ChevronBackOutline, MenuOutline, SchoolOutline, FitnessOutline,
  ChatbubblesOutline, ClipboardOutline
} from '@vicons/ionicons5'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const collapsed = ref(false)
const isMobile = ref(false)
const unreadMessages = ref(0)
const pendingApprovals = ref(0)
let badgeTimer: number | undefined

function badgeLabel(text: string, count: number) {
  return count > 0 ? () => h('span', { class: 'menu-label' }, [text, h('b', { class: 'menu-badge' }, String(count))]) : text
}

const menuItems = computed(() => {
  const role = authStore.user?.role || ''
  const allItems: any[] = [
    { key: '/home', label: '首页', icon: () => h(NIcon, null, { default: () => h(HomeOutline) }), roles: ['trainee', 'coach', 'admin'] },
    { key: '/assessment', label: '体态评估', icon: () => h(NIcon, null, { default: () => h(BodyOutline) }), roles: ['trainee', 'admin'] },
    { key: '/fms', label: 'FMS筛查', icon: () => h(NIcon, null, { default: () => h(AnalyticsOutline) }), roles: ['trainee'] },
    { key: '/prescription-training', label: 'AI训练计划', icon: () => h(NIcon, null, { default: () => h(ListOutline) }), roles: ['trainee'] },
    { key: '/training', label: '计划训练', icon: () => h(NIcon, null, { default: () => h(BookOutline) }), roles: ['trainee'] },
    { key: '/learning', label: '标准动作学习', icon: () => h(NIcon, null, { default: () => h(SchoolOutline) }), roles: ['trainee', 'coach', 'admin'] },
    { key: '/checkin', label: '每日打卡', icon: () => h(NIcon, null, { default: () => h(CheckmarkCircleOutline) }), roles: ['trainee'] },
    { key: '/my-classes', label: '我的班级', icon: () => h(NIcon, null, { default: () => h(PeopleOutline) }), roles: ['trainee'] },
    { key: '/messages', label: badgeLabel('消息', unreadMessages.value), icon: () => h(NIcon, null, { default: () => h(ChatbubblesOutline) }), roles: ['trainee', 'coach', 'admin'] },
    { key: '/profile', label: '个人中心', icon: () => h(NIcon, null, { default: () => h(PersonOutline) }), roles: ['trainee', 'coach', 'admin'] },
    { key: '/coach', label: '教练工作台', icon: () => h(NIcon, null, { default: () => h(PeopleOutline) }), roles: ['coach', 'admin'] },
    { key: '/coach/actions', label: '动作库管理', icon: () => h(NIcon, null, { default: () => h(FitnessOutline) }), roles: ['coach', 'admin'] },
    { key: '/coach/plan-review', label: badgeLabel('计划审批', pendingApprovals.value), icon: () => h(NIcon, null, { default: () => h(ClipboardOutline) }), roles: ['coach', 'admin'] },
    { key: '/admin', label: '系统管理', icon: () => h(NIcon, null, { default: () => h(SettingsOutline) }), roles: ['admin'] }
  ]
  return allItems.filter(item => item.roles.includes(role)).map(({ roles: _, ...item }) => item)
})

const activeKey = computed(() => {
  const path = String(route.path || '/')
  if (path.startsWith('/coach/actions')) return '/coach/actions'
  if (path.startsWith('/coach/plan-review')) return '/coach/plan-review'
  const segments = path.split('/').filter(Boolean)
  return '/' + (segments[0] || 'home')
})

const userDropdownOptions = computed(() => [
  { label: '个人中心', key: 'profile' },
  { label: '退出登录', key: 'logout' }
])

function handleMenuClick(key: string) {
  router.push(key)
  if (isMobile.value) collapsed.value = true
}

function handleUserSelect(key: string) {
  if (key === 'logout') {
    authStore.logout()
    router.push('/login')
  } else if (key === 'profile') {
    router.push('/profile')
  }
}

function toggleCollapse() {
  collapsed.value = !collapsed.value
}

function handleResize() {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) collapsed.value = true
}

async function fetchBadges() {
  try { unreadMessages.value = (await messageApi.unreadCount()).unread_count || 0 } catch { /* optional badge */ }
  if (authStore.user?.role === 'coach' || authStore.user?.role === 'admin') {
    try { const data = await coachApi.listChangeRequests('pending'); pendingApprovals.value = data.total ?? data.requests?.length ?? 0 } catch { /* optional badge */ }
  }
}

onMounted(() => {
  handleResize()
  window.addEventListener('resize', handleResize)
  fetchBadges()
  badgeTimer = window.setInterval(fetchBadges, 5000)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  window.clearInterval(badgeTimer)
})

const userName = computed(() => authStore.user?.username || '用户')

const renderError = ref<string | null>(null)
onErrorCaptured((err, _instance, info) => {
  console.error('[MainLayout] Caught error:', err, info)
  renderError.value = String(err)
  // 阻止异常继续向上传播；当前子页面卸载后，切换路由会由下方 watch 恢复。
  return false
})

watch(() => route.fullPath, () => {
  renderError.value = null
})
</script>

<template>
  <n-layout style="height: 100vh" has-sider>
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed="collapsed"
      :collapsed-width="64"
      :width="260"
      class="app-sider"
    >
      <div class="sider-trigger" :class="{ 'is-collapsed': collapsed }" @click="toggleCollapse">
        <n-icon size="16" :component="ChevronBackOutline" />
      </div>
      <div class="logo-area" :class="{ 'is-collapsed': collapsed }">
        <div class="logo-icon">
          <img src="/media/pictures/transport.jpg" alt="运动姿态评估与纠错系统" />
        </div>
        <span v-if="!collapsed" class="logo-text">
          <span class="logo-title">运动姿态</span>
          <span class="logo-subtitle">评估与纠错系统</span>
        </span>
      </div>

      <div class="menu-divider top-divider"></div>
      <n-menu
        :key="authStore.user?.role || 'guest'"
        :value="activeKey"
        :collapsed="collapsed"
        :collapsed-width="64"
        :options="menuItems"
        @update:value="handleMenuClick"
        class="app-menu"
      />
    </n-layout-sider>

    <n-layout>
      <n-layout-header bordered class="app-header">
        <div class="header-left">
          <n-button text @click="toggleCollapse" class="menu-btn">
            <n-icon :component="collapsed ? MenuOutline : ChevronBackOutline" size="20" />
          </n-button>
          <div class="page-title">{{ (route.meta.title as string) || '首页' }}</div>
        </div>

        <n-space class="header-right">
          <n-dropdown :options="userDropdownOptions" @select="handleUserSelect" trigger="click">
            <div class="user-info">
              <n-avatar round :size="32" :fallback-char="userName[0] || 'U'" color="#7c3aed" style="background: #7c3aed; color: #fff" />
              <span class="user-name" v-if="!isMobile">{{ userName }}</span>
            </div>
          </n-dropdown>
        </n-space>
      </n-layout-header>

      <n-layout-content class="app-content">
        <n-alert v-if="renderError" type="error" :title="'页面渲染错误'" style="margin-bottom: 12px;">
          {{ renderError }}
        </n-alert>
        <router-view v-slot="{ Component }">
          <component v-if="!renderError" :is="Component" :key="$route.fullPath" />
        </router-view>
      </n-layout-content>

      <n-layout-footer class="app-footer">
        运动体态评估与纠错系统 ©2026
      </n-layout-footer>
    </n-layout>
  </n-layout>
</template>

<style scoped>
/* ── Sider ─────────────────────────── */
.app-sider {
  z-index: 100;
}

:deep(.n-layout-sider) {
  background: #f8fafc !important;
  position: relative;
}

:deep(.n-layout-sider)::after {
  content: '';
  position: absolute;
  inset: 0;
  background: url('/ai2.png') center/cover no-repeat;
  opacity: 0.12;
  filter: saturate(0.62) brightness(1.12);
  pointer-events: none;
  z-index: 0;
}

:deep(.n-layout-sider > *) {
  position: relative;
  z-index: 1;
}

/* ── Sider trigger ─ triangular tab ── */
.sider-trigger {
  position: absolute;
  top: 50%;
  right: -18px;
  transform: translateY(-50%);
  width: 18px;
  height: 52px;
  background: #f8fafc;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-left: none;
  border-radius: 0 6px 6px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 2px 0 6px rgba(0, 0, 0, 0.06);
}

.sider-trigger:hover {
  width: 22px;
  right: -22px;
  box-shadow: 2px 0 10px rgba(91, 94, 230, 0.15);
}

.sider-trigger .n-icon {
  color: #5b5ee6;
  font-size: 14px;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* collapsed state */
.app-sider :deep(.n-layout-sider--collapsed) .sider-trigger,
:deep(.n-layout-sider--collapsed) ~ .sider-trigger,
.sider-trigger.is-collapsed {
  right: auto;
  left: -18px;
  border-radius: 6px 0 0 6px;
  border-left: 1px solid rgba(0, 0, 0, 0.06);
  border-right: none;
  box-shadow: -2px 0 6px rgba(0, 0, 0, 0.06);
}

.sider-trigger.is-collapsed:hover {
  left: -22px;
  box-shadow: -2px 0 10px rgba(91, 94, 230, 0.15);
}

.sider-trigger.is-collapsed .n-icon {
  transform: rotate(180deg);
}

/* ── Logo ──────────────────────────── */
.logo-area {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 22px;
  height: 92px;
  box-sizing: border-box;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.logo-icon {
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #fff;
  border: 1px solid rgba(91, 94, 230, 0.14);
  border-radius: 16px;
  flex-shrink: 0;
  box-shadow: 0 4px 10px rgba(91, 94, 230, 0.12);
}

.logo-icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  transform: none;
}

.logo-text {
  background: linear-gradient(135deg, #5b5ee6 0%, #4f4dd9 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  line-height: 1.15;
  white-space: nowrap;
}

.logo-title {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.logo-subtitle {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.15px;
  opacity: 0.88;
}

.logo-area.is-collapsed {
  height: 72px;
  padding: 12px 10px;
  justify-content: center;
}

.logo-area.is-collapsed .logo-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
}

/* ── Menu ──────────────────────────── */
.app-menu {
  padding: 16px 8px;
  border: none !important;
}

:deep(.menu-label) { display: flex; align-items: center; gap: 6px; }
:deep(.menu-badge) { min-width: 17px; height: 17px; padding: 0 5px; border-radius: 9px; background: #ef4444; color: white; font-size: 10px; line-height: 17px; text-align: center; }

/* Divider lines */
.menu-divider {
  height: 1px;
  margin: 0 16px;
  flex-shrink: 0;
}

.top-divider {
  background: linear-gradient(90deg, transparent 0%, #93a5cf 20%, #5b5ee6 50%, #93a5cf 80%, transparent 100%);
  opacity: 0.5;
}

.bottom-divider {
  background: linear-gradient(90deg, transparent 0%, #5b5ee6 20%, #93a5cf 50%, #5b5ee6 80%, transparent 100%);
  opacity: 0.4;
}

/* Menu item default */
:deep(.n-menu-item-content) {
  border-radius: 10px !important;
  margin: 3px 4px;
  padding: 12px 12px !important;
  min-height: 44px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* Hover */
:deep(.n-menu-item-content:hover) {
  background: rgba(139, 92, 246, 0.06) !important;
  transform: scale(1.03);
}

:deep(.n-menu-item-content:hover .n-icon) {
  color: #5b5ee6 !important;
}

:deep(.n-menu-item-content:hover .n-menu-item-content__text) {
  color: #5b5ee6 !important;
}

/* Selected — left bar + light purple bg */
:deep(.n-menu-item-content--selected) {
  background: rgba(139, 92, 246, 0.08) !important;
  border-radius: 10px !important;
  position: relative;
}

:deep(.n-menu-item-content--selected::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  background: linear-gradient(180deg, #5b5ee6 0%, #4f4dd9 100%);
  border-radius: 0 3px 3px 0;
}

:deep(.n-menu-item-content--selected .n-icon) {
  color: #5b5ee6 !important;
}

:deep(.n-menu-item-content--selected .n-menu-item-content__text) {
  color: #5b5ee6 !important;
  font-weight: 600 !important;
}

/* ── Item dividers ────────────────────── */
:deep(.n-menu-item-content) {
  position: relative;
}

:deep(.n-menu-item:not(:last-child) .n-menu-item-content)::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 16px;
  right: 16px;
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, #8b9cf6 30%, #6b7cf6 70%, transparent 100%);
  opacity: 0.45;
}

.app-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(248, 250, 252, 0.85) !important;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.menu-btn {
  margin-left: -8px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background-color 0.2s;
}

.user-info:hover {
  background: rgba(0, 0, 0, 0.04);
}

.user-name {
  font-size: 14px;
  font-weight: 500;
}

/* ── Content ───────────────────────── */
.app-content {
  padding: 24px;
  overflow-y: auto;
  background:
    radial-gradient(ellipse at 15% 10%, rgba(139, 92, 246, 0.03) 0%, transparent 55%),
    radial-gradient(ellipse at 85% 90%, rgba(102, 126, 234, 0.03) 0%, transparent 55%),
    #f8fafc;
  flex: 1;
}

/* ── Footer ────────────────────────── */
.app-footer {
  text-align: center;
  font-size: 13px;
  color: #64748b;
  padding: 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  background: #f8fafc;
}

/* ── Transitions ───────────────────── */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ── Mobile ────────────────────────── */
@media (max-width: 768px) {
  .app-content {
    padding: 16px;
  }

  .page-title {
    font-size: 16px;
  }
}
</style>
