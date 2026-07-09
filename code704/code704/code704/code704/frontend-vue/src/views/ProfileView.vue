<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { userApi, checkinApi, fmsApi, assessmentApi, prescriptionV2Api, recordsApi } from '../services/api'
import type { FMSRecord, AssessmentRecord, TrainingRecord, TrainingStats } from '../types'
import VChart from 'vue-echarts'
import 'echarts'
import {
  NCard, NButton, NSpace, NIcon, NAvatar, NTag, NGrid, NGridItem,
  NModal, NInput, NForm, NFormItem, NSelect, NSpin, NEmpty, NText,
  NDescriptions, NDescriptionsItem, NInputNumber, NDatePicker, NDataTable, useMessage
} from 'naive-ui'
import {
  PersonOutline, CallOutline, MaleFemaleOutline, CalendarOutline,
  CreateOutline, FlameOutline, TrophyOutline, FitnessOutline,
  AnalyticsOutline, BodyOutline, PlayCircleOutline,
  ChevronForwardOutline, LogOutOutline, ListOutline, LockClosedOutline,
  TimeOutline, CheckmarkCircleOutline, TrendingUpOutline
} from '@vicons/ionicons5'

const router = useRouter()
const authStore = useAuthStore()
const message = useMessage()

// ── Data state ──
const loading = ref(true)
const streakDays = ref(0)
const recentCards = ref<any[]>([])
const badges = ref<any[]>([])
const fmsRecords = ref<FMSRecord[]>([])
const assessmentRecords = ref<AssessmentRecord[]>([])
const prescriptions = ref<any[]>([])
const trainingStats = ref<TrainingStats | null>(null)
const trainingRecords = ref<TrainingRecord[]>([])
const cycleConfig = ref<any>(null)

// ── Password & cycle settings ──
const showPasswordModal = ref(false)
const passwordSaving = ref(false)
const passwordForm = ref({ old_password: '', new_password: '', confirm_password: '' })
const cycleSaving = ref(false)
const cycleForm = ref({ cycle_length: 28, period_length: 5, last_period_timestamp: null as number | null })

// ── Edit modal state ──
const showEditModal = ref(false)
const saving = ref(false)
const editForm = ref({
  username: authStore.user?.username || '',
  phone: authStore.user?.phone || '',
  gender: authStore.user?.gender || 'male'
})

const genderOptions = [
  { label: '男', value: 'male' },
  { label: '女', value: 'female' }
]

// ── Role label ──
const roleLabel = computed(() => {
  const role = authStore.user?.role
  if (role === 'admin') return { text: '管理员', type: 'error' as const }
  if (role === 'coach') return { text: '教练', type: 'warning' as const }
  return { text: '学员', type: 'info' as const }
})

const roleColor = computed(() => {
  const role = authStore.user?.role
  if (role === 'admin') return '#ef4444'
  if (role === 'coach') return '#f59e0b'
  return '#3b82f6'
})

// ── Derived stats ──
const totalCheckins = computed(() => recentCards.value.length)
const monthlyCheckins = computed(() => {
  const month = new Date().toISOString().slice(0, 7)
  return recentCards.value.filter(c => c.date?.startsWith(month)).length
})
const daysInMonth = computed(() => new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).getDate())
const latestFms = computed(() => fmsRecords.value[0] || null)
const latestAssessment = computed(() => assessmentRecords.value[0] || null)

// ── Report Shelf derived data ──
const fmsScore = computed(() => Math.round(latestFms.value?.overall_score || 0))
const postureScore = computed(() => Math.round(latestAssessment.value?.overall_score || 0))
const actionAccuracy = computed(() => {
  const avg = trainingStats.value?.average_score
  return avg != null ? Math.round(Number(avg)) : 0
})
const riskLevel = computed(() => latestFms.value?.risk_level || '')
const lastUpdateTime = computed(() => {
  const dates = [
    latestFms.value?.test_date,
    latestAssessment.value?.test_date,
    trainingRecords.value[0]?.start_time
  ].filter(Boolean)
  if (!dates.length) return ''
  const latest = dates.map(d => new Date(d as string)).sort((a, b) => b.getTime() - a.getTime())[0]
  return latest.toLocaleDateString('zh-CN')
})

function postureStatusLabel(score: number) {
  if (score >= 85) return '整体姿态优秀'
  if (score >= 70) return '姿态状态良好'
  if (score >= 60) return '轻度姿态问题'
  return '建议进一步评估'
}

function actionStatusLabel(acc: number) {
  if (acc >= 85) return '动作达标率高'
  if (acc >= 70) return '动作表现良好'
  if (acc >= 60) return '仍有提升空间'
  return '建议加强训练'
}

const reportBooks = computed(() => [
  {
    key: 'posture',
    title: 'Posture Report',
    subtitle: '体态报告书',
    score: postureScore.value,
    scoreLabel: '最新体态评分',
    status: postureScore.value ? postureStatusLabel(postureScore.value) : '暂无数据',
    risk: latestAssessment.value?.risk_level,
    path: '/report/posture',
    theme: 'green'
  },
  {
    key: 'fms',
    title: 'FMS Report',
    subtitle: '功能性动作筛查',
    score: fmsScore.value,
    scoreLabel: '最新 FMS 评分',
    status: fmsScore.value ? (riskLevel.value ? riskLabel(riskLevel.value) : '暂无风险评级') : '暂无数据',
    risk: riskLevel.value,
    path: '/report/fms',
    theme: 'purple',
    featured: true
  },
  {
    key: 'action',
    title: 'Action Report',
    subtitle: '标准动作学习报告',
    score: actionAccuracy.value,
    scoreLabel: '最新学习评分',
    status: actionAccuracy.value ? actionStatusLabel(actionAccuracy.value) : '暂无数据',
    path: '/report/action',
    theme: 'blue'
  }
])

// ── Badge icon mappings ──
const badgeIcons: Record<string, any> = {
  streak_7: FlameOutline,
  streak_30: TrophyOutline,
  sessions_100: FitnessOutline,
  score_90: TrophyOutline,
  fms_first: AnalyticsOutline,
}
const badgeColors: Record<string, string> = {
  streak_7: '#ef4444',
  streak_30: '#8b5cf6',
  sessions_100: '#3b82f6',
  score_90: '#10b981',
  fms_first: '#f59e0b',
}

// ── ECharts ring options ──
const ringColors = {
  purple: ['#8b5cf6', '#e5e7eb'],
  blue: ['#3b82f6', '#e5e7eb'],
  green: ['#10b981', '#e5e7eb'],
}

function makeRingOption(value: number, max: number, color: [string, string], suffix: string) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return {
    series: [{
      type: 'gauge',
      startAngle: 90,
      endAngle: -270,
      radius: '85%',
      pointer: { show: false },
      progress: {
        show: true,
        overlap: false,
        roundCap: true,
        clip: false,
        itemStyle: { color: color[0] }
      },
      axisLine: {
        lineStyle: {
          width: 10,
          color: [[pct / 100, color[0]], [1, color[1]]]
        }
      },
      splitLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
      detail: {
        fontSize: 16,
        fontWeight: 700,
        color: color[0],
        offsetCenter: [0, '60%'],
        formatter: () => `${value}${suffix}`
      },
      title: {
        offsetCenter: [0, '20%'],
        fontSize: 11,
        color: '#64748b',
      },
      data: [{ value: pct, name: '' }]
    }]
  }
}

const monthlyRingOption = computed(() => {
  const max = daysInMonth.value
  return makeRingOption(monthlyCheckins.value, max, ringColors.purple, '天')
})

const fmsRingOption = computed(() => {
  const score = Math.round(latestFms.value?.overall_score || 0)
  return makeRingOption(score, 100, ringColors.blue, '分')
})

const assessRingOption = computed(() => {
  const score = Math.round(latestAssessment.value?.overall_score || 0)
  return makeRingOption(score, 100, ringColors.green, '分')
})

// ── Risk tag helpers ──
function riskTagType(level: string) {
  if (level === 'low') return 'success' as const
  if (level === 'medium') return 'warning' as const
  return 'error' as const
}
function riskLabel(level: string) {
  if (level === 'low') return '低风险'
  if (level === 'medium') return '中风险'
  return '高风险'
}

// ── Status tag for plans ──
function planStatusTagType(status: string) {
  if (status === 'active') return 'success' as const
  if (status === 'completed') return 'info' as const
  return 'default' as const
}
function planStatusLabel(status: string) {
  if (status === 'active') return '进行中'
  if (status === 'completed') return '已完成'
  if (status === 'draft') return '草稿'
  return status
}

function planDifficultyLabel(d: number) {
  if (d === 1) return '入门'
  if (d === 2) return '初级'
  if (d === 3) return '中级'
  if (d === 4) return '进阶'
  if (d === 5) return '高级'
  return '初级'
}

// ── Quick actions ──
const quickActions = [
  { title: '体态评估', desc: 'AI智能体态分析', icon: BodyOutline, path: '/assessment', color: '#3b82f6' },
  { title: 'FMS筛查', desc: '功能性动作测试', icon: AnalyticsOutline, path: '/fms', color: '#8b5cf6' },
  { title: '标准学习', desc: '标准动作跟练', icon: PlayCircleOutline, path: '/training', color: '#10b981' },
  { title: '每日打卡', desc: '坚持训练记录', icon: FlameOutline, path: '/checkin', color: '#f59e0b' },
]

function goTo(path: string) {
  router.push(path)
}

// ── Edit profile ──
function openEdit() {
  editForm.value = {
    username: authStore.user?.username || '',
    phone: authStore.user?.phone || '',
    gender: authStore.user?.gender || 'male'
  }
  showEditModal.value = true
}

function saveProfile() {
  saving.value = true
  userApi.updateProfile({
    username: editForm.value.username,
    phone: editForm.value.phone,
    gender: editForm.value.gender
  }).then((updatedUser) => {
    showEditModal.value = false
    if (authStore.user) {
      authStore.user = { ...authStore.user, ...updatedUser }
    }
    message.success('资料已更新')
  }).catch((err: any) => {
    message.error(err?.response?.data?.detail || '更新失败，请重试')
  }).finally(() => {
    saving.value = false
  })
}

async function changePassword() {
  if (!passwordForm.value.old_password) return message.warning('请输入旧密码')
  if (passwordForm.value.new_password.length < 6) return message.warning('新密码至少 6 位')
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) return message.warning('两次输入的新密码不一致')
  passwordSaving.value = true
  try {
    await userApi.changePassword({
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password,
    })
    showPasswordModal.value = false
    passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
    message.success('密码已修改')
  } catch (err: any) {
    message.error(err?.response?.data?.detail || '修改失败，请检查旧密码')
  } finally {
    passwordSaving.value = false
  }
}

async function saveCycleConfig() {
  cycleSaving.value = true
  try {
    const payload: any = {
      cycle_length: cycleForm.value.cycle_length,
      period_length: cycleForm.value.period_length,
    }
    if (cycleForm.value.last_period_timestamp) {
      payload.last_period_date = new Date(cycleForm.value.last_period_timestamp).toISOString().slice(0, 10)
    }
    cycleConfig.value = await userApi.updateCycleConfig(payload)
    message.success('月经周期设置已保存')
  } catch (err: any) {
    message.error(err?.response?.data?.detail || '周期设置保存失败')
  } finally {
    cycleSaving.value = false
  }
}

// ── Logout ──
function handleLogout() {
  authStore.logout()
  router.push('/login')
}

// ── Fetch all data ──
onMounted(async () => {
  const results = await Promise.allSettled([
    checkinApi.status().then(s => {
      streakDays.value = s.streak_days || 0
      recentCards.value = s.recent_cards || []
    }),
    checkinApi.badges().then(b => { badges.value = b || [] }),
    fmsApi.getRecords().then(r => { fmsRecords.value = r || [] }),
    assessmentApi.getRecords().then(r => { assessmentRecords.value = r || [] }),
    prescriptionV2Api.list().then(p => { prescriptions.value = (p?.plans || []).slice(0, 2) }),
    recordsApi.stats().then(s => { trainingStats.value = s }),
    recordsApi.history(90).then(r => { trainingRecords.value = r || [] }),
    userApi.getCycleConfig().then(c => {
      cycleConfig.value = c
      cycleForm.value = {
        cycle_length: c?.cycle_length || 28,
        period_length: c?.period_length || 5,
        last_period_timestamp: c?.last_period_date ? new Date(c.last_period_date).getTime() : null,
      }
    }),
  ])
  loading.value = false
})
</script>

<script lang="ts">
export default { name: 'ProfileView' }
</script>

<template>
  <div class="profile-page">

    <!-- Background grid overlay -->
    <div class="bg-grid"></div>

    <!-- ═══ Loading ═══ -->
    <n-spin v-if="loading" size="large" class="loading-spin" />

    <template v-else>
      <!-- ═══ Hero Banner ═══ -->
      <div class="hero-banner">
        <div class="hero-decor hero-decor-1"></div>
        <div class="hero-decor hero-decor-2"></div>
        <div class="hero-decor hero-decor-3"></div>
        <div class="hero-decor hero-decor-4"></div>
        <div class="hero-inner">
          <div class="hero-left">
            <div class="hero-avatar-wrap">
              <n-avatar
                round
                :size="80"
                :fallback-char="authStore.user?.username?.[0] || 'U'"
                class="hero-avatar"
                color="#7c3aed"
                style="background: #7c3aed; color: #fff"
              />
            </div>
            <div class="hero-info">
              <div class="hero-name-row">
                <h1 class="hero-name">{{ authStore.user?.username }}</h1>
                <n-tag :type="roleLabel.type" round size="small" :bordered="false">{{ roleLabel.text }}</n-tag>
              </div>
              <div class="hero-meta">
                <n-icon size="14" :component="CalendarOutline" />
                <span>注册于 {{ authStore.user?.created_at ? new Date(authStore.user.created_at).toLocaleDateString() : '-' }}</span>
              </div>
            </div>
          </div>
          <div class="hero-stats">
            <div class="hero-stat-item">
              <span class="hero-stat-num">{{ streakDays }}</span>
              <span class="hero-stat-lbl">连续打卡</span>
            </div>
            <div class="hero-stat-divider"></div>
            <div class="hero-stat-item">
              <span class="hero-stat-num">{{ totalCheckins }}</span>
              <span class="hero-stat-lbl">累计打卡</span>
            </div>
            <div class="hero-stat-divider"></div>
            <div class="hero-stat-item">
              <span class="hero-stat-num">{{ badges.length }}</span>
              <span class="hero-stat-lbl">获得徽章</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ Ability Overview (Ring Cards) ═══ -->
      <div class="rings-row">
        <div class="ring-card">
          <div class="ring-chart-area">
            <v-chart :option="monthlyRingOption" style="width:110px;height:110px" />
          </div>
          <div class="ring-info">
            <span class="ring-info-title">本月打卡</span>
            <span class="ring-info-num">{{ monthlyCheckins }}<small>天</small></span>
            <span class="ring-info-desc">已坚持训练 {{ monthlyCheckins }} 天</span>
          </div>
        </div>
        <div class="ring-card">
          <div class="ring-chart-area">
            <v-chart :option="fmsRingOption" style="width:110px;height:110px" />
          </div>
          <div class="ring-info">
            <span class="ring-info-title">FMS 评分</span>
            <span class="ring-info-num" :style="{ color: latestFms ? '#3b82f6' : '#94a3b8' }">
              {{ latestFms ? Math.round(latestFms.overall_score) : '--' }}<small v-if="latestFms">分</small>
            </span>
            <span v-if="latestFms" class="ring-info-desc">存在部分动作风险</span>
            <span v-else class="ring-info-desc">暂无数据</span>
          </div>
        </div>
        <div class="ring-card">
          <div class="ring-chart-area">
            <v-chart :option="assessRingOption" style="width:110px;height:110px" />
          </div>
          <div class="ring-info">
            <span class="ring-info-title">体态评分</span>
            <span class="ring-info-num" :style="{ color: latestAssessment ? '#10b981' : '#94a3b8' }">
              {{ latestAssessment ? Math.round(latestAssessment.overall_score) : '--' }}<small v-if="latestAssessment">分</small>
            </span>
            <span v-if="latestAssessment" class="ring-info-desc">整体姿态优秀</span>
            <span v-else class="ring-info-desc">暂无数据</span>
          </div>
        </div>
      </div>

      <!-- ═══ Report Shelf ═══ -->
      <div class="report-shelf-section">
        <div class="shelf-header">
          <span class="panel-title">📚 报告书架</span>
          <span v-if="lastUpdateTime" class="shelf-update">最近更新：{{ lastUpdateTime }}</span>
        </div>
        <div class="books-row">
          <div
            v-for="book in reportBooks"
            :key="book.key"
            class="book-card"
            :class="[`book-${book.theme}`, { 'book-featured': book.featured }]"
            @click="goTo(book.path)"
          >
            <div class="book-spine"></div>
            <div class="book-cover">
              <div class="book-cover-shine"></div>
              <div class="book-badge">{{ book.subtitle }}</div>
              <h3 class="book-title">{{ book.title }}</h3>
              <div class="book-score-wrap">
                <span class="book-score">{{ book.score || '--' }}</span>
                <span class="book-score-unit">{{ book.score ? '分' : '' }}</span>
              </div>
              <span class="book-score-label">{{ book.scoreLabel }}</span>
              <div class="book-status-row">
                <n-tag v-if="book.risk" :type="riskTagType(book.risk)" round size="tiny" :bordered="false" class="book-risk-tag">
                  {{ riskLabel(book.risk) }}
                </n-tag>
                <span class="book-status">{{ book.status }}</span>
              </div>
            </div>
            <div class="book-bottom">
              <span class="book-cta">查看报告 <span class="book-arrow">→</span></span>
            </div>
          </div>
        </div>
        <div class="shelf-board"></div>
      </div>

      <!-- ═══ Info + Assessments Row ═══ -->
      <div class="two-col">
        <!-- Basic Info -->
        <div class="panel-card">
          <div class="panel-header">
            <span class="panel-title">基本信息</span>
            <n-space>
              <n-button text size="small" @click="showPasswordModal = true">
                <template #icon><n-icon size="14" :component="LockClosedOutline" /></template>
                修改密码
              </n-button>
              <n-button text type="primary" size="small" @click="openEdit">
                <template #icon><n-icon size="14" :component="CreateOutline" /></template>
                编辑
              </n-button>
            </n-space>
          </div>
          <div class="info-list">
            <div class="info-row">
              <div class="info-icon" style="background:rgba(59,130,246,0.1);color:#3b82f6">
                <n-icon size="18" :component="PersonOutline" />
              </div>
              <span class="info-label">用户名</span>
              <span class="info-value">{{ authStore.user?.username || '-' }}</span>
            </div>
            <div class="info-row">
              <div class="info-icon" style="background:rgba(16,185,129,0.1);color:#10b981">
                <n-icon size="18" :component="CallOutline" />
              </div>
              <span class="info-label">手机号</span>
              <span class="info-value">{{ authStore.user?.phone || '未设置' }}</span>
            </div>
            <div class="info-row">
              <div class="info-icon" style="background:rgba(139,92,246,0.1);color:#8b5cf6">
                <n-icon size="18" :component="MaleFemaleOutline" />
              </div>
              <span class="info-label">性别</span>
              <span class="info-value">{{ authStore.user?.gender === 'female' ? '女' : '男' }}</span>
            </div>
            <div class="info-row">
              <div class="info-icon" style="background:rgba(245,158,11,0.1);color:#f59e0b">
                <n-icon size="18" :component="CalendarOutline" />
              </div>
              <span class="info-label">注册时间</span>
              <span class="info-value">{{ authStore.user?.created_at ? new Date(authStore.user.created_at).toLocaleDateString() : '-' }}</span>
            </div>
          </div>
        </div>

        <!-- Recent Assessments (Timeline style) -->
        <div class="panel-card">
          <div class="panel-header">
            <span class="panel-title">最近评估</span>
          </div>
          <div v-if="latestFms || latestAssessment" class="timeline">
            <div v-if="latestFms" class="timeline-item" @click="goTo('/fms')">
              <div class="tl-dot fms"></div>
              <div class="tl-line"></div>
              <div class="tl-content">
                <div class="tl-head">
                  <span class="tl-date">{{ new Date(latestFms.test_date).toLocaleDateString() }}</span>
                  <n-tag :type="riskTagType(latestFms.risk_level)" round size="tiny" :bordered="false">{{ riskLabel(latestFms.risk_level) }}</n-tag>
                </div>
                <span class="tl-title">FMS 筛查</span>
                <span class="tl-score">{{ Math.round(latestFms.overall_score) }} 分</span>
              </div>
            </div>
            <div v-if="latestAssessment" class="timeline-item" @click="goTo('/assessment')">
              <div class="tl-dot assess"></div>
              <div class="tl-content">
                <div class="tl-head">
                  <span class="tl-date">{{ new Date(latestAssessment.test_date).toLocaleDateString() }}</span>
                  <n-tag :type="riskTagType(latestAssessment.risk_level)" round size="tiny" :bordered="false">{{ riskLabel(latestAssessment.risk_level) }}</n-tag>
                </div>
                <span class="tl-title">体态评估</span>
                <span class="tl-score">{{ Math.round(latestAssessment.overall_score) }} 分</span>
              </div>
            </div>
          </div>
          <div v-else class="empty-mini">
            <span>暂无评估记录</span>
            <n-button size="small" class="gradient-btn" @click="goTo('/fms')">去筛查</n-button>
          </div>
        </div>
      </div>

      <!-- ═══ Menstrual Cycle ═══ -->
      <div v-if="authStore.user?.gender === 'female'" class="panel-card">
        <div class="panel-header">
          <span class="panel-title">月经周期设置</span>
        </div>
        <p class="cycle-desc">用于 AI 训练自动调整训练计划</p>
        <div class="cycle-form">
          <div class="cycle-field">
            <label>周期天数</label>
            <n-input-number v-model:value="cycleForm.cycle_length" :min="21" :max="40" style="width:120px" />
          </div>
          <div class="cycle-field">
            <label>经期天数</label>
            <n-input-number v-model:value="cycleForm.period_length" :min="2" :max="10" style="width:120px" />
          </div>
          <div class="cycle-field">
            <label>末次月经</label>
            <n-date-picker v-model:value="cycleForm.last_period_timestamp" type="date" clearable style="width:180px" />
          </div>
          <n-button class="gradient-btn" :loading="cycleSaving" @click="saveCycleConfig">保存设置</n-button>
        </div>
        <n-text v-if="cycleConfig?.intensity_coefficient" depth="3" style="font-size:12px;margin-top:8px;display:block;">
          当前周期训练强度系数：{{ cycleConfig.intensity_coefficient }}
        </n-text>
      </div>

      <!-- ═══ AI Prescriptions ═══ -->
      <div class="panel-card">
        <div class="panel-header">
          <span class="panel-title">AI 训练方案</span>
          <n-button text type="primary" size="small" @click="goTo('/prescription-training')">
            全部 <template #icon><n-icon size="14" :component="ChevronForwardOutline" /></template>
          </n-button>
        </div>
        <div v-if="prescriptions.length > 0" class="rx-cards">
          <div v-for="plan in prescriptions" :key="plan.id" class="rx-card" @click="goTo('/prescription-training')">
            <div class="rx-card-top">
              <div class="rx-card-icon" :style="{ background: roleColor + '12', color: roleColor }">
                <n-icon size="22" :component="FitnessOutline" />
              </div>
              <div class="rx-card-tags">
                <n-tag type="info" size="tiny" round :bordered="false">{{ plan.generation_method === 'deepseek' ? 'AI 生成' : '系统模板' }}</n-tag>
                <n-tag :type="planStatusTagType(plan.status)" size="tiny" round :bordered="false">{{ planStatusLabel(plan.status) }}</n-tag>
              </div>
            </div>
            <h4 class="rx-card-name">{{ plan.plan_name || '训练方案' }}</h4>
            <div class="rx-card-meta">
              <span><n-icon size="14" :component="BodyOutline" /> {{ plan.items?.length || 0 }} 个动作</span>
              <span><n-icon size="14" :component="TimeOutline" /> {{ planDifficultyLabel(plan.difficulty) }}</span>
            </div>
            <n-button class="gradient-btn" size="small" style="margin-top:14px;width:100%">
              <template #icon><n-icon :component="PlayCircleOutline" /></template>
              继续训练
            </n-button>
          </div>
        </div>
        <div v-else class="empty-mini">
          <span>暂无训练方案</span>
          <n-button size="small" class="gradient-btn" @click="goTo('/assessment')">去评估获取方案</n-button>
        </div>
      </div>

      <!-- ═══ Badges ═══ -->
      <div v-if="badges.length > 0" class="panel-card">
        <div class="panel-header">
          <span class="panel-title">成就徽章</span>
        </div>
        <div class="badges-row">
          <div v-for="badge in badges" :key="badge.type" class="badge-item">
            <div class="badge-icon-box" :style="{ background: (badgeColors[badge.type] || '#f59e0b') + '15', color: badgeColors[badge.type] || '#f59e0b' }">
              <n-icon size="28" :component="badgeIcons[badge.type] || TrophyOutline" />
            </div>
            <div class="badge-info">
              <span class="badge-name">{{ badge.name }}</span>
              <span class="badge-desc">{{ badge.description }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ Logout ═══ -->
      <div class="logout-wrap">
        <n-button text type="error" size="large" @click="handleLogout" class="logout-btn">
          <template #icon><n-icon size="18" :component="LogOutOutline" /></template>
          退出登录
        </n-button>
      </div>
    </template>

    <!-- ═══ Edit Modal ═══ -->
    <n-modal v-model:show="showEditModal" preset="card" title="编辑资料" style="width: 440px;">
      <n-form :model="editForm" label-placement="top">
        <n-form-item label="用户名">
          <n-input v-model:value="editForm.username" />
        </n-form-item>
        <n-form-item label="手机号">
          <n-input v-model:value="editForm.phone" placeholder="请输入手机号" />
        </n-form-item>
        <n-form-item label="性别">
          <n-select v-model:value="editForm.gender" :options="genderOptions" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showEditModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="saveProfile">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showPasswordModal" preset="card" title="修改密码" style="width: 440px;">
      <n-form :model="passwordForm" label-placement="top">
        <n-form-item label="旧密码"><n-input v-model:value="passwordForm.old_password" type="password" show-password-on="click" /></n-form-item>
        <n-form-item label="新密码"><n-input v-model:value="passwordForm.new_password" type="password" show-password-on="click" placeholder="至少 6 位" /></n-form-item>
        <n-form-item label="确认新密码"><n-input v-model:value="passwordForm.confirm_password" type="password" show-password-on="click" /></n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showPasswordModal = false">取消</n-button>
          <n-button type="primary" :loading="passwordSaving" @click="changePassword">确认修改</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
/* ── Page shell ── */
.profile-page {
  position: relative;
  max-width: 960px;
  margin: -24px auto 0;
  padding: 24px 24px 40px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  background: linear-gradient(180deg, #faf9ff 0%, #f5f4ff 55%, #ffffff 100%);
  min-height: calc(100vh - 64px - 56px);
}

.bg-grid {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(rgba(108,99,255,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(108,99,255,0.04) 1px, transparent 1px);
  background-size: 30px 30px, 30px 30px;
  pointer-events: none;
  z-index: 0;
}

.loading-spin { display: flex; justify-content: center; padding: 80px 0; position: relative; z-index: 1; }

/* ── Hero Banner ── */
.hero-banner {
  position: relative;
  z-index: 1;
  min-height: 180px;
  background: linear-gradient(135deg, #5E74F8, #7B6CFF, #9A68D8);
  border-radius: 20px;
  padding: 32px 36px;
  display: flex;
  align-items: center;
  overflow: hidden;
}
.hero-decor {
  position: absolute;
  border-radius: 50%;
  background: rgba(255,255,255,0.05);
  pointer-events: none;
}
.hero-decor-1 { width: 300px; height: 300px; top: -80px; right: -60px; }
.hero-decor-2 { width: 180px; height: 180px; bottom: -40px; right: 18%; }
.hero-decor-3 { width: 100px; height: 100px; top: 30px; right: 38%; }
.hero-decor-4 { width: 60px; height: 60px; bottom: 20px; left: 40%; }
.hero-inner {
  position: relative;
  z-index: 1;
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}
.hero-left { display: flex; align-items: center; gap: 16px; flex-shrink: 0; }
.hero-avatar-wrap { flex-shrink: 0; }
.hero-avatar {
  border: 3px solid rgba(255,255,255,0.3) !important;
  font-size: 32px !important;
}
.hero-info { display: flex; flex-direction: column; gap: 6px; }
.hero-name-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.hero-name { font-size: 24px; font-weight: 600; margin: 0; color: #fff; line-height: 1.2; }
.hero-meta { display: flex; align-items: center; gap: 4px; font-size: 13px; color: rgba(255,255,255,0.75); }
.hero-stats { display: flex; align-items: center; gap: 20px; flex-shrink: 0; }
.hero-stat-item { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.hero-stat-num { font-size: 30px; font-weight: 800; line-height: 1; color: #fff; }
.hero-stat-lbl { font-size: 12px; color: rgba(255,255,255,0.8); }
.hero-stat-divider { width: 1px; height: 44px; background: rgba(255,255,255,0.18); }

/* ── Panel card (unified) ── */
.panel-card {
  position: relative;
  z-index: 1;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(18px);
  border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.8);
  box-shadow: 0 12px 40px rgba(108,99,255,0.08);
  padding: 24px 28px;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}
.panel-title { font-size: 17px; font-weight: 600; color: #1e293b; }

/* ── Rings Row ── */
.rings-row {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.ring-card {
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(18px);
  border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.8);
  box-shadow: 0 12px 40px rgba(108,99,255,0.08);
  padding: 22px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.ring-chart-area { flex-shrink: 0; }
.ring-info { display: flex; flex-direction: column; gap: 3px; }
.ring-info-title { font-size: 14px; font-weight: 600; color: #1e293b; }
.ring-info-num { font-size: 17px; font-weight: 700; color: #8b5cf6; }
.ring-info-num small { font-size: 12px; font-weight: 500; color: #64748b; margin-left: 2px; }
.ring-info-desc { font-size: 12px; color: #8B8B99; }

/* ── Report Shelf ── */
.report-shelf-section {
  position: relative;
  z-index: 1;
}
.shelf-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
  padding: 0 4px;
}
.shelf-update {
  font-size: 12px;
  color: #8B8B99;
}
.books-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  align-items: flex-end;
  padding: 10px 4px 20px;
}
.book-card {
  position: relative;
  min-height: 220px;
  border-radius: 16px 14px 14px 16px;
  padding: 22px 20px 18px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
  background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(255,255,255,0.85));
  border: 1px solid rgba(255,255,255,0.7);
  box-shadow:
    0 8px 24px rgba(108,99,255,0.10),
    inset 0 1px 0 rgba(255,255,255,0.6);
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
  transform-style: preserve-3d;
}
.book-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  opacity: 0.18;
  pointer-events: none;
  transition: opacity 0.35s ease;
}
.book-spine {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 14px;
  border-radius: 16px 0 0 16px;
  background: linear-gradient(180deg, rgba(255,255,255,0.35), rgba(255,255,255,0.05));
  box-shadow: inset -2px 0 4px rgba(0,0,0,0.04);
}
.book-cover {
  position: relative;
  z-index: 1;
  padding-left: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.book-cover-shine {
  position: absolute;
  top: -40px;
  right: -40px;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,255,255,0.35) 0%, transparent 70%);
  pointer-events: none;
}
.book-badge {
  display: inline-flex;
  align-self: flex-start;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  backdrop-filter: blur(6px);
  background: rgba(255,255,255,0.28);
  color: rgba(255,255,255,0.95);
  margin-bottom: 4px;
}
.book-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
  text-shadow: 0 2px 4px rgba(0,0,0,0.08);
}
.book-score-wrap {
  display: flex;
  align-items: baseline;
  gap: 2px;
  margin-top: 6px;
}
.book-score {
  font-size: 36px;
  font-weight: 800;
  color: #fff;
  line-height: 1;
  text-shadow: 0 2px 8px rgba(0,0,0,0.12);
}
.book-score-unit {
  font-size: 14px;
  font-weight: 500;
  color: rgba(255,255,255,0.85);
}
.book-score-label {
  font-size: 12px;
  color: rgba(255,255,255,0.75);
}
.book-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 4px;
}
.book-risk-tag {
  background: rgba(255,255,255,0.25) !important;
  color: #fff !important;
}
.book-status {
  font-size: 12px;
  color: rgba(255,255,255,0.85);
}
.book-bottom {
  position: relative;
  z-index: 1;
  padding-left: 10px;
  padding-top: 14px;
  border-top: 1px solid rgba(255,255,255,0.18);
  margin-top: 12px;
}
.book-cta {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255,255,255,0.95);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: gap 0.25s ease;
}
.book-arrow {
  transition: transform 0.25s ease;
}
.book-card:hover .book-arrow {
  transform: translateX(4px);
}

/* Theme: purple (FMS, featured) */
.book-purple {
  background: linear-gradient(145deg, #8b5cf6, #7c3aed);
  transform: rotate(-1deg) translateY(0);
}
.book-purple:hover {
  transform: rotate(0deg) translateY(-6px) scale(1.03);
  box-shadow:
    0 20px 40px rgba(139,92,246,0.30),
    inset 0 1px 0 rgba(255,255,255,0.3);
}

/* Theme: green (Posture) */
.book-green {
  background: linear-gradient(145deg, #10b981, #059669);
  transform: rotate(1.5deg) translateY(0);
}
.book-green:hover {
  transform: rotate(0deg) translateY(-6px) scale(1.03);
  box-shadow:
    0 20px 40px rgba(16,185,129,0.28),
    inset 0 1px 0 rgba(255,255,255,0.3);
}

/* Theme: blue (Action) */
.book-blue {
  background: linear-gradient(145deg, #3b82f6, #2563eb);
  transform: rotate(-1.5deg) translateY(0);
}
.book-blue:hover {
  transform: rotate(0deg) translateY(-6px) scale(1.03);
  box-shadow:
    0 20px 40px rgba(59,130,246,0.28),
    inset 0 1px 0 rgba(255,255,255,0.3);
}

/* Featured center book */
.book-featured {
  transform: scale(1.05) rotate(0deg) translateY(-4px);
  z-index: 2;
}
.book-featured:hover {
  transform: scale(1.08) translateY(-10px);
  box-shadow:
    0 24px 48px rgba(139,92,246,0.35),
    inset 0 1px 0 rgba(255,255,255,0.35);
}

.shelf-board {
  height: 12px;
  margin: -8px 8px 0;
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(123,108,255,0.18), rgba(123,108,255,0.06));
  box-shadow: 0 6px 18px rgba(108,99,255,0.12);
  position: relative;
}
.shelf-board::after {
  content: '';
  position: absolute;
  left: 20px;
  right: 20px;
  top: 0;
  height: 1px;
  background: rgba(255,255,255,0.5);
}

@media (max-width: 768px) {
  .books-row {
    grid-template-columns: 1fr;
    gap: 16px;
    padding-bottom: 10px;
  }
  .book-card,
  .book-featured {
    transform: none !important;
    min-height: auto;
  }
  .book-featured:hover,
  .book-card:hover {
    transform: translateY(-4px) scale(1.02) !important;
  }
  .shelf-board { display: none; }
}

/* ── Two-column layout ── */
.two-col {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.two-col .panel-card { height: 100%; }

/* ── Basic Info List ── */
.info-list { display: flex; flex-direction: column; gap: 2px; }
.info-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 6px;
  border-radius: 10px;
  transition: background 0.2s;
}
.info-row:hover { background: rgba(123,108,255,0.04); }
.info-icon {
  width: 38px; height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.info-label { font-size: 13px; color: #8B8B99; width: 60px; flex-shrink: 0; }
.info-value { font-size: 14px; font-weight: 500; color: #1e293b; }

/* ── Timeline ── */
.timeline { display: flex; flex-direction: column; padding-left: 8px; }
.timeline-item {
  display: flex;
  gap: 12px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}
.timeline-item:hover .tl-content {
  background: rgba(123,108,255,0.04);
}
.tl-dot {
  width: 12px; height: 12px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}
.tl-dot.fms { background: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.15); }
.tl-dot.assess { background: #10b981; box-shadow: 0 0 0 3px rgba(16,185,129,0.15); }
.tl-line {
  position: absolute;
  left: 5.5px;
  top: 18px;
  bottom: 0;
  width: 1px;
  background: #e5e7eb;
}
.timeline-item:last-child .tl-line { display: none; }
.tl-content {
  flex: 1;
  padding: 8px 12px;
  border-radius: 10px;
  transition: background 0.2s;
  margin-bottom: 4px;
}
.tl-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.tl-date { font-size: 12px; color: #94a3b8; }
.tl-title { font-size: 14px; font-weight: 600; color: #1e293b; }
.tl-score { font-size: 20px; font-weight: 700; color: #1e293b; margin-top: 2px; display: block; }

/* ── Empty mini ── */
.empty-mini {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px;
  color: #8B8B99;
  font-size: 14px;
}

/* ── Gradient button ── */
.gradient-btn {
  background: linear-gradient(135deg, #7B6CFF, #5C8CFF) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 12px !important;
  font-weight: 600 !important;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
  box-shadow: 0 4px 16px rgba(123,108,255,0.25);
}
.gradient-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(123,108,255,0.35);
}
.gradient-btn :deep(.n-button__border),
.gradient-btn :deep(.n-button__state-border) { border: none !important; }

/* ── Menstrual Cycle ── */
.cycle-desc { font-size: 13px; color: #8B8B99; margin: -8px 0 16px; }
.cycle-form { display: flex; align-items: flex-end; gap: 16px; flex-wrap: wrap; }
.cycle-field { display: flex; flex-direction: column; gap: 4px; }
.cycle-field label { font-size: 12px; color: #64748b; }

/* ── AI Prescriptions ── */
.rx-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.rx-card {
  background: #f8fafc;
  border-radius: 14px;
  padding: 18px 20px;
  cursor: pointer;
  transition: all 0.25s ease;
  border: 1px solid transparent;
}
.rx-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(108,99,255,0.10);
  border-color: rgba(123,108,255,0.15);
}
.rx-card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.rx-card-icon {
  width: 40px; height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.rx-card-tags { display: flex; gap: 6px; }
.rx-card-name { font-size: 15px; font-weight: 600; color: #1e293b; margin: 0 0 10px; }
.rx-card-meta { display: flex; gap: 16px; font-size: 13px; color: #64748b; }
.rx-card-meta span { display: inline-flex; align-items: center; gap: 4px; }

/* ── Badges ── */
.badges-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.badge-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 12px;
  background: rgba(123,108,255,0.03);
  transition: all 0.2s;
}
.badge-item:hover {
  background: rgba(123,108,255,0.06);
  transform: translateY(-2px);
}
.badge-icon-box {
  width: 48px; height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.badge-info { display: flex; flex-direction: column; gap: 2px; }
.badge-name { font-size: 14px; font-weight: 600; color: #1e293b; }
.badge-desc { font-size: 12px; color: #8B8B99; }

/* ── Quick Actions ── */
.actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.action-card {
  padding: 14px;
  border-radius: 12px;
  background: rgba(123,108,255,0.03);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 10px;
}
.action-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(108,99,255,0.10);
  background: rgba(123,108,255,0.06);
}
.action-icon {
  width: 42px; height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.action-info { flex: 1; min-width: 0; }
.action-title { font-size: 14px; font-weight: 600; display: block; color: #1e293b; }
.action-desc { font-size: 12px; color: #8B8B99; display: block; }
.action-arrow { color: #94a3b8; flex-shrink: 0; }

/* ── Logout ── */
.logout-wrap {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: center;
  padding: 4px 0 8px;
}
.logout-btn { opacity: 0.5; transition: opacity 0.2s; }
.logout-btn:hover { opacity: 1; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .profile-page { padding: 16px; margin: -16px auto 0; gap: 14px; }
  .hero-banner { padding: 24px 20px; }
  .hero-inner { flex-direction: column; text-align: center; }
  .hero-left { flex-direction: column; text-align: center; }
  .hero-name-row { justify-content: center; }
  .hero-stats { width: 100%; justify-content: center; padding-top: 8px; }
  .hero-stat-num { font-size: 24px; }
  .rings-row { grid-template-columns: 1fr; }
  .two-col { grid-template-columns: 1fr; }
  .rx-cards { grid-template-columns: 1fr; }
  .actions-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
