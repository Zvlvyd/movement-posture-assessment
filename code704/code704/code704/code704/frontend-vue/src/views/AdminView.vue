<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { adminApi, authApi } from '../services/api'
import type { AdminUser, SystemLog } from '../types'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import {
  NCard, NButton, NTabs, NTabPane, NTag, NIcon,
  NList, NListItem, NSpace, NInput, NGrid, NGridItem,
  NDataTable, NEmpty, NModal, NForm, NFormItem, NSelect,
  NPopconfirm, NSpin, NStatistic, useMessage
} from 'naive-ui'
import {
  SettingsOutline, PeopleOutline, BarChartOutline,
  ShieldOutline, SearchOutline,
  AddOutline, CreateOutline, TrashOutline, DocumentTextOutline,
  DesktopOutline, TrendingUpOutline, PieChartOutline,
  PersonOutline, FitnessOutline, CheckmarkCircleOutline,
  FlashOutline, AlertCircleOutline
} from '@vicons/ionicons5'

use([CanvasRenderer, LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const activeTab = ref('users')
const message = useMessage()
const searchQuery = ref('')
const showUserModal = ref(false)
const loading = ref(true)
const saving = ref(false)

const users = ref<AdminUser[]>([])
const logs = ref<SystemLog[]>([])
const config = ref<any>(null)
const dashboard = ref<any>(null)
const storage = ref<any>(null)
const checkedUserIds = ref<number[]>([])
const configDraft = ref<Record<string, any>>({})
const configSaving = ref(false)
const editingConfigKey = ref<string | null>(null)
const editingConfigValue = ref('')

const userForm = ref({ username: '', password: '', role: 'trainee' })

const roleOptions = [
  { label: '管理员', value: 'admin' },
  { label: '教练', value: 'coach' },
  { label: '学员', value: 'trainee' }
]

const columns = [
  { type: 'selection' },
  { title: 'ID', key: 'id', width: 60 },
  { title: '用户名', key: 'username' },
  { title: '手机号', key: 'phone', render: (row: any) => row.phone || '-' },
  {
    title: '角色', key: 'role',
    render: (row: any) => {
      const map: Record<string, string> = { admin: '管理员', coach: '教练', trainee: '学员' }
      const typeMap: Record<string, any> = { admin: 'error', coach: 'warning', trainee: 'default' }
      return h(NTag, { type: typeMap[row.role] || 'default', size: 'small', round: true }, { default: () => map[row.role] || row.role })
    }
  },
  {
    title: '状态', key: 'is_active',
    render: (row: any) =>
      h(NTag, { type: row.is_active ? 'success' : 'default', size: 'small', round: true },
        { default: () => row.is_active ? '活跃' : '禁用' })
  },
  { title: '注册时间', key: 'created_at', render: (row: any) => row.created_at ? new Date(row.created_at).toLocaleDateString() : '-' },
  {
    title: '操作', key: 'actions', width: 240,
    render: (row: any) =>
      h(NSpace, null, {
        default: () => [
          h(NButton, { type: 'primary', size: 'small', onClick: () => openEditRole(row) }, {
            default: () => '改角色'
          }),
          h(NButton, { type: 'primary', size: 'small', onClick: () => toggleStatus(row) }, {
            default: () => row.is_active ? '禁用' : '启用'
          }),
          h(NButton, { type: row.is_deleted ? 'success' : 'error', size: 'small', onClick: () => row.is_deleted ? restoreUser(row) : deleteUser(row) }, {
            default: () => row.is_deleted ? '恢复' : '删除'
          })
        ]
      })
  }
] as any

// We need h for render functions
import { h } from 'vue'

function loadData() {
  loading.value = true
  Promise.all([
    adminApi.users().catch(() => []),
    adminApi.config().catch(() => null),
    adminApi.dashboard().catch(() => null),
    adminApi.storage().catch(() => null)
  ]).then(([u, c, d, st]) => {
    users.value = Array.isArray(u) ? u : (u?.items || u?.users || [])
    config.value = c
    configDraft.value = { ...(c || {}) }
    dashboard.value = d
    storage.value = st
  }).finally(() => { loading.value = false })
  setTimeout(() => { loading.value = false }, 8000)
}

function loadLogs() {
  adminApi.logs(50).then(l => { logs.value = Array.isArray(l) ? l : (l?.items || l?.logs || []) }).catch(() => {})
}

async function deleteUser(user: any) {
  if (!window.confirm(`确定删除用户“${user.username}”吗？`)) return
  try { await adminApi.deleteUser(user.id); message.success('用户已删除'); loadData() }
  catch (err: any) { message.error(err?.response?.data?.detail || '删除失败') }
}

async function restoreUser(user: any) {
  try { await adminApi.restoreUser(user.id); message.success('用户已恢复'); loadData() }
  catch (err: any) { message.error(err?.response?.data?.detail || '恢复失败') }
}

async function batchOperation(operation: string) {
  if (!checkedUserIds.value.length) return message.warning('请先选择用户')
  try {
    await adminApi.batchOperation({ user_ids: checkedUserIds.value, operation })
    checkedUserIds.value = []
    message.success('批量操作已完成')
    loadData()
  } catch (err: any) { message.error(err?.response?.data?.detail || '批量操作失败') }
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

// ── Dashboard chart options ──
const regTrendOption = computed(() => ({
  tooltip: { trigger: 'axis' as const },
  grid: { left: 40, right: 20, top: 20, bottom: 30 },
  xAxis: {
    type: 'category' as const,
    data: (dashboard.value?.registration_trend || []).map((d: any) => d.date?.slice(5)),
    axisLabel: { fontSize: 11, color: '#94a3b8' }
  },
  yAxis: {
    type: 'value' as const, minInterval: 1,
    axisLabel: { fontSize: 11, color: '#94a3b8' }
  },
  series: [{
    type: 'line', data: (dashboard.value?.registration_trend || []).map((d: any) => d.count),
    smooth: true, lineStyle: { color: '#7c3aed', width: 2 },
    areaStyle: { color: 'rgba(124,58,237,0.08)' },
    itemStyle: { color: '#7c3aed' }
  }]
}))

const roleDistOption = computed(() => {
  const dist = dashboard.value?.role_distribution || {}
  const data = [
    { name: '学员', value: dist.trainee || 0, itemStyle: { color: '#3b82f6' } },
    { name: '教练', value: dist.coach || 0, itemStyle: { color: '#f59e0b' } },
    { name: '管理员', value: dist.admin || 0, itemStyle: { color: '#ef4444' } },
  ]
  return {
    tooltip: { trigger: 'item' as const },
    legend: { bottom: 0, textStyle: { fontSize: 11, color: '#64748b' } },
    series: [{
      type: 'pie', radius: ['40%', '70%'], center: ['50%', '45%'],
      data, label: { fontSize: 11, color: '#64748b' },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.1)' } }
    }]
  }
})

async function exportUsers() {
  try { saveBlob(await adminApi.exportUsers(), `users-${new Date().toISOString().slice(0, 10)}.csv`) }
  catch { message.error('导出用户失败') }
}

async function exportLogs() {
  try { saveBlob(await adminApi.exportLogs(5000), `logs-${new Date().toISOString().slice(0, 10)}.csv`) }
  catch { message.error('导出日志失败') }
}

function startEditConfig(key: string) {
  editingConfigKey.value = key
  editingConfigValue.value = config.value?.[key]?.value || ''
}
function cancelEditConfig() {
  editingConfigKey.value = null
  editingConfigValue.value = ''
}
async function saveConfigItem(key: string) {
  configSaving.value = true
  try {
    await adminApi.updateConfig({ [key]: editingConfigValue.value })
    message.success(`配置 ${key} 已更新`)
    editingConfigKey.value = null
    loadData()
  } catch (err: any) { message.error(err?.response?.data?.detail || '保存失败') }
  finally { configSaving.value = false }
}

const configEntries = computed(() => {
  if (!config.value) return []
  return Object.entries(config.value).map(([key, info]: [string, any]) => ({
    key,
    value: info?.value ?? info ?? '',
    description: info?.description ?? '',
    updated_at: info?.updated_at ?? '',
  }))
})

const configColumns = computed(() => [
  { title: '配置项', key: 'key', width: 220, render: (row: any) => h('code', { style: { fontSize: '12px', background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' } }, row.key) },
  { title: '值', key: 'value',
    render: (row: any) => {
      if (editingConfigKey.value === row.key) {
        return h(NInput, { value: editingConfigValue.value, 'onUpdate:value': (v: string) => editingConfigValue.value = v, size: 'small', style: { width: '260px' }, onKeyup: (e: KeyboardEvent) => { if (e.key === 'Enter') saveConfigItem(row.key) } })
      }
      return row.value ? h('span', null, String(row.value)) : h('span', { style: { color: '#94a3b8' } }, '（空）')
    }
  },
  { title: '说明', key: 'description', ellipsis: { tooltip: true }, render: (row: any) => row.description || '-' },
  { title: '最后更新', key: 'updated_at', width: 150, render: (row: any) => row.updated_at?.slice(0, 16) || '-' },
  {
    title: '操作', key: 'actions', width: 100,
    render: (row: any) => {
      if (editingConfigKey.value === row.key) {
        return h(NSpace, { size: 'small' }, { default: () => [
          h(NButton, { size: 'tiny', type: 'primary', loading: configSaving.value, onClick: () => saveConfigItem(row.key) }, { default: () => '保存' }),
          h(NButton, { size: 'tiny', onClick: cancelEditConfig }, { default: () => '取消' })
        ]})
      }
      return h(NButton, { size: 'tiny', onClick: () => startEditConfig(row.key) }, { default: () => '编辑' })
    }
  }
])

function toggleStatus(user: AdminUser) {
  adminApi.toggleStatus(user.id, !user.is_active).then(() => {
    user.is_active = !user.is_active
  }).catch(() => {})
}

function openEditRole(user: AdminUser) {
  const roles = ['admin', 'coach', 'trainee']
  const currentIdx = roles.indexOf(user.role)
  const nextRole = roles[(currentIdx + 1) % roles.length]
  adminApi.changeRole(user.id, nextRole).then(() => {
    user.role = nextRole
  }).catch(() => {})
}

function addUser() {
  userForm.value = { username: '', password: '', role: 'trainee' }
  showUserModal.value = true
}

function saveUser() {
  if (!userForm.value.username || !userForm.value.password) return
  saving.value = true
  authApi.register(userForm.value)
    .then(() => {
      showUserModal.value = false
      loadData()
    })
    .catch(() => {})
    .finally(() => { saving.value = false })
}

function handleTabChange(tab: string) {
  if (tab === 'logs') loadLogs()
}

onMounted(() => { loadData() })
</script>

<script lang="ts">
export default { name: 'AdminView' }
</script>

<template>
  <div class="admin-page">
      <n-card :bordered="false" class="header-card" size="large">
        <div class="header-content">
          <div class="header-left">
            <div class="header-icon">
              <n-icon size="28" :component="SettingsOutline" />
            </div>
            <div>
              <h2 class="page-title">系统管理</h2>
              <p class="page-subtitle">系统用户和数据管理</p>
            </div>
          </div>
        </div>
      </n-card>

      <n-grid :cols="4" :x-gap="12" :y-gap="12" class="stats-grid">
        <n-grid-item>
          <n-card :bordered="false" class="stat-card" size="medium">
            <div class="stat-icon" style="background: #3b82f615; color: #3b82f6;">
              <n-icon size="22" :component="PeopleOutline" />
            </div>
            <div class="stat-value">{{ users.length }}</div>
            <div class="stat-label">用户总数</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card :bordered="false" class="stat-card" size="medium">
            <div class="stat-icon" style="background: #f59e0b15; color: #f59e0b;">
              <n-icon size="22" :component="ShieldOutline" />
            </div>
            <div class="stat-value">{{ users.filter(u => u.role === 'coach').length }}</div>
            <div class="stat-label">教练数量</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card :bordered="false" class="stat-card" size="medium">
            <div class="stat-icon" style="background: #10b98115; color: #10b981;">
              <n-icon size="22" :component="BarChartOutline" />
            </div>
            <div class="stat-value">{{ dashboard?.active_users ?? users.filter(u => u.is_active).length }}</div>
            <div class="stat-label">活跃用户</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card :bordered="false" class="stat-card" size="medium">
            <div class="stat-icon" style="background: #8b5cf615; color: #8b5cf6;">
              <n-icon size="22" :component="SettingsOutline" />
            </div>
            <div class="stat-value">{{ config?.db_type || '-' }}</div>
            <div class="stat-label">数据库类型</div>
          </n-card>
        </n-grid-item>
      </n-grid>

      <n-card :bordered="false" class="section-card" size="large">
        <n-tabs v-model:value="activeTab" type="line" @update:value="handleTabChange">
          <n-tab-pane name="dashboard" tab="系统仪表板">
            <!-- Top Stats -->
            <n-grid :cols="4" :x-gap="12" :y-gap="12" style="margin-bottom:16px">
              <n-grid-item><n-card :bordered="false" size="small" class="stat-card">
                <n-statistic label="总用户数" :value="dashboard?.total_users || 0"><template #prefix><n-icon :component="PeopleOutline" /></template></n-statistic>
              </n-card></n-grid-item>
              <n-grid-item><n-card :bordered="false" size="small" class="stat-card">
                <n-statistic label="活跃用户" :value="dashboard?.active_users || 0"><template #prefix><n-icon :component="PersonOutline" /></template></n-statistic>
              </n-card></n-grid-item>
              <n-grid-item><n-card :bordered="false" size="small" class="stat-card">
                <n-statistic label="教练数" :value="dashboard?.role_distribution?.coach || 0"><template #prefix><n-icon :component="ShieldOutline" /></template></n-statistic>
              </n-card></n-grid-item>
              <n-grid-item><n-card :bordered="false" size="small" class="stat-card">
                <n-statistic label="管理员数" :value="dashboard?.role_distribution?.admin || 0"><template #prefix><n-icon :component="SettingsOutline" /></template></n-statistic>
              </n-card></n-grid-item>
            </n-grid>

            <!-- System Activity -->
            <n-grid :cols="4" :x-gap="12" :y-gap="12" style="margin-bottom:16px">
              <n-grid-item><n-card :bordered="false" size="small" class="stat-card">
                <n-statistic label="FMS 筛查" :value="dashboard?.system_activity?.fms_screens || 0"><template #prefix><n-icon :component="FitnessOutline" /></template></n-statistic>
              </n-card></n-grid-item>
              <n-grid-item><n-card :bordered="false" size="small" class="stat-card">
                <n-statistic label="体态评估" :value="dashboard?.system_activity?.assessments || 0"><template #prefix><n-icon :component="DesktopOutline" /></template></n-statistic>
              </n-card></n-grid-item>
              <n-grid-item><n-card :bordered="false" size="small" class="stat-card">
                <n-statistic label="训练计划" :value="dashboard?.system_activity?.prescriptions || 0"><template #prefix><n-icon :component="FlashOutline" /></template></n-statistic>
              </n-card></n-grid-item>
              <n-grid-item><n-card :bordered="false" size="small" class="stat-card">
                <n-statistic label="打卡次数" :value="dashboard?.system_activity?.checkins || 0"><template #prefix><n-icon :component="CheckmarkCircleOutline" /></template></n-statistic>
              </n-card></n-grid-item>
            </n-grid>

            <!-- Charts Row -->
            <n-grid :cols="2" :x-gap="12" :y-gap="12" style="margin-bottom:16px" responsive="screen">
              <n-grid-item span="2 m:1">
                <n-card :bordered="false" size="small" title="注册趋势（近30天）" class="chart-card">
                  <v-chart v-if="(dashboard?.registration_trend || []).length" :option="regTrendOption" autoresize style="height:260px" />
                  <n-empty v-else description="暂无数据" size="small" />
                </n-card>
              </n-grid-item>
              <n-grid-item span="2 m:1">
                <n-card :bordered="false" size="small" title="角色分布" class="chart-card">
                  <v-chart :option="roleDistOption" autoresize style="height:260px" />
                </n-card>
              </n-grid-item>
            </n-grid>

            <!-- Bottom Stats -->
            <n-grid :cols="4" :x-gap="12" :y-gap="12">
              <n-grid-item><n-card :bordered="false" size="small" class="stat-card">
                <n-statistic label="错误率（近7天）" :value="dashboard?.error_rate || 0"><template #suffix>%</template></n-statistic>
              </n-card></n-grid-item>
              <n-grid-item><n-card :bordered="false" size="small" class="stat-card">
                <n-statistic label="DAU" :value="dashboard?.dau || 0" />
              </n-card></n-grid-item>
              <n-grid-item><n-card :bordered="false" size="small" class="stat-card">
                <n-statistic label="WAU" :value="dashboard?.wau || 0" />
              </n-card></n-grid-item>
              <n-grid-item><n-card :bordered="false" size="small" class="stat-card">
                <n-statistic label="MAU" :value="dashboard?.mau || 0" />
              </n-card></n-grid-item>
            </n-grid>
          </n-tab-pane>

          <n-tab-pane name="users" tab="用户管理">
            <div class="toolbar">
              <n-input v-model:value="searchQuery" placeholder="搜索用户" style="width: 240px;">
                <template #prefix>
                  <n-icon :component="SearchOutline" />
                </template>
              </n-input>
              <n-space>
                <n-button @click="batchOperation('enable')">批量启用</n-button>
                <n-button @click="batchOperation('disable')">批量禁用</n-button>
                <n-button @click="exportUsers">导出用户</n-button>
                <n-button type="primary" @click="addUser"><template #icon><n-icon :component="AddOutline" /></template>新增用户</n-button>
              </n-space>
            </div>

            <n-dataTable
              :columns="columns"
              :data="users.filter(u => !searchQuery || u.username.includes(searchQuery))"
              :bordered="false"
              class="data-table"
              :row-key="(row: any) => row.id"
              v-model:checked-row-keys="checkedUserIds"
            />
          </n-tab-pane>

          <n-tab-pane name="system" tab="系统设置">
            <n-empty v-if="!config || configEntries.length === 0" description="暂无配置信息" />
            <n-card v-else :bordered="false" size="small" title="系统配置">
              <template #header-extra><n-button size="small" @click="loadData">刷新</n-button></template>
              <n-data-table
                :columns="configColumns"
                :data="configEntries"
                :row-key="(row: any) => row.key"
                size="small"
                :pagination="configEntries.length > 15 ? { pageSize: 15 } : false"
              />
              <n-card v-if="storage" size="small" style="margin-top: 16px;">
                存储概况：{{ storage.total_size || storage.total || '-' }} <span v-if="storage.database_size"> · 数据库 {{ storage.database_size }}</span>
              </n-card>
            </n-card>
          </n-tab-pane>

          <n-tab-pane name="logs" tab="操作日志">
            <n-space justify="end" style="margin-bottom: 12px;"><n-button @click="exportLogs">导出日志</n-button></n-space>
            <n-empty v-if="logs.length === 0" description="暂无日志数据" />
            <n-list v-else>
              <n-list-item v-for="log in logs" :key="log.id">
                <div class="log-item">
                  <div class="log-left">
                    <n-icon size="18" :component="DocumentTextOutline" style="color: #94a3b8;" />
                    <div>
                      <div class="log-action">{{ log.action }}</div>
                      <div class="log-meta">
                        <span v-if="log.username">{{ log.username }}</span>
                        <span v-if="log.ip_address" class="divider">·</span>
                        <span v-if="log.ip_address">{{ log.ip_address }}</span>
                      </div>
                    </div>
                  </div>
                  <span class="log-time">{{ new Date(log.created_at).toLocaleString() }}</span>
                </div>
              </n-list-item>
            </n-list>
          </n-tab-pane>
        </n-tabs>
      </n-card>

    <n-modal v-model:show="showUserModal" preset="card" title="新增用户" style="width: 440px;">
      <n-form :model="userForm" label-placement="top">
        <n-form-item label="用户名">
          <n-input v-model:value="userForm.username" placeholder="请输入用户名" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="userForm.password" type="password" placeholder="请输入密码" show-password-on="click" />
        </n-form-item>
        <n-form-item label="角色">
          <n-select v-model:value="userForm.role" :options="roleOptions" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showUserModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="saveUser">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.admin-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.header-card {
  background: linear-gradient(135deg, #5E74F8, #7B6CFF, #9A68D8) !important;
  color: white;
  border-radius: 16px !important;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 4px 0;
  color: white;
}

.page-subtitle {
  font-size: 13px;
  margin: 0;
  color: rgba(255, 255, 255, 0.85);
}

.stats-grid {
  margin-top: 0 !important;
}

.stat-card {
  border-radius: 12px !important;
  text-align: center;
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

.section-card {
  border-radius: 12px !important;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.data-table {
  margin-top: 0;
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.config-label {
  font-weight: 500;
}

.log-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.log-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.log-action {
  font-size: 14px;
  font-weight: 500;
}

.log-meta {
  font-size: 12px;
  color: #64748b;
  display: flex;
  gap: 6px;
  align-items: center;
}

.log-time {
  font-size: 12px;
  color: #94a3b8;
  flex-shrink: 0;
}

.divider {
  color: #cbd5e1;
}

@media (max-width: 768px) {
  .stats-grid {
    gap: 8px !important;
  }

  .stat-value {
    font-size: 20px;
  }

  .toolbar {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
}
</style>
