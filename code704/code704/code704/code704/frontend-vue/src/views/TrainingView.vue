<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { prescriptionV2Api, learningApi, createLearningWS } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { PlanV2, PlanItemV2, LearningComplete, AngleDiff, LearningFeedback } from '../types'
import {
  NCard, NButton, NSpace, NTag, NIcon, NProgress, NEmpty, NSpin,
  NGrid, NGridItem, NDescriptions, NDescriptionsItem,
  NDivider, useMessage
} from 'naive-ui'
import {
  ListOutline, PlayCircleOutline, CheckmarkCircleOutline,
  ArrowBackOutline, ArrowForwardOutline, TrophyOutline,
  BulbOutline, EyeOutline, WarningOutline, CloseCircleOutline,
  StopOutline, RefreshOutline, FitnessOutline,
  TimeOutline, StarOutline, CalendarOutline,
  BarbellOutline, FlameOutline, FlashOutline,
  DocumentTextOutline
} from '@vicons/ionicons5'
import TrainingHeroCard from '../components/training/TrainingHeroCard.vue'
import TrainingPhaseSection from '../components/training/TrainingPhaseSection.vue'

import { mockPlans, mockProgress } from '../mock/trainingMockData'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const message = useMessage()

type PageMode = 'plan_list' | 'plan_detail' | 'ready' | 'training' | 'result'
const showStartPrompt = ref(true)

const PHASE_LABELS: Record<string, string> = { warmup: '热身', main: '主训练', cooldown: '冷身' }
const PHASE_COLORS: Record<string, string> = { warmup: '#3B82F6', main: '#FF006E', cooldown: '#00F0FF' }
const PHASE_DESCRIPTIONS: Record<string, string> = { warmup: '激活身体', main: '重点提升', cooldown: '放松恢复' }
const PHASE_ICONS: Record<string, any> = { warmup: FlameOutline, main: FitnessOutline, cooldown: FlashOutline }
const STATUS_COLORS: Record<string, string> = { good: '#52c41a', close: '#faad14', warning: '#fa8c16', bad: '#f5222d', unknown: '#d9d9d9' }
const STATUS_LABELS: Record<string, string> = { good: '优秀', close: '接近', warning: '注意', bad: '偏差', unknown: '未知' }
const JOINT_LABELS: Record<string, string> = {
  trunk_tilt: '躯干倾斜', neck_tilt: '颈部倾斜',
  left_hip: '左髋角', right_hip: '右髋角',
  left_knee: '左膝角', right_knee: '右膝角',
  left_shoulder: '左肩角', right_shoulder: '右肩角',
  left_elbow: '左肘角', right_elbow: '右肘角',
  left_ankle: '左踝角', right_ankle: '右踝角',
}

const DIFFICULTY_LABELS: Record<number, string> = { 1: '入门', 2: '初级', 3: '中级', 4: '进阶', 5: '高级' }
const DIFFICULTY_COLORS: Record<number, string> = { 1: '#10b981', 2: '#10b981', 3: '#f59e0b', 4: '#f97316', 5: '#ef4444' }

// ── Mock mode ──
const useMock = ref(false)

// ── Page mode state ──
const mode = ref<PageMode>('plan_list')
const plans = ref<PlanV2[]>([])
const loading = ref(true)
const loadError = ref(false)
const selectedPlan = ref<PlanV2 | null>(null)
const currentItem = ref<PlanItemV2 | null>(null)
type ItemProgress = { sets_done: number; total_sets: number; latest_reps: number; latest_score: number }
const completedExercises = ref<Set<number>>(new Set())
const itemProgress = ref<Map<number, ItemProgress>>(new Map())
const result = ref<LearningComplete | null>(null)

// ── Training session state ──
const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const skeletonCanvasRef = ref<HTMLCanvasElement | null>(null)
const userKeypoints = ref<number[][] | null>(null)
const userConfidences = ref<number[] | null>(null)
const frameWidth = ref(640)
const frameHeight = ref(480)
const isSessionActive = ref(false)
const progressSaved = ref(false)
const pendingReport = ref(false)
let resolveReport: (() => void) | null = null
const currentView = ref('正面')
const standardAngles = ref<Record<string, { min: number; max: number; optimal: number }>>({})
const keyChecks = ref<any[]>([])
const instruction = ref('')
const diffs = ref<AngleDiff[]>([])
const feedbacks = ref<LearningFeedback[]>([])
const overallScore = ref<number | null>(null)
const bestScore = ref(0)
const frameCount = ref(0)
const sessionPhase = ref('waiting_for_body')
const repCount = ref(0)
const exerciseType = ref('')

// ── Per-set progress ──
const setProgress = computed(() => {
  if (!currentItem.value || exerciseType.value !== 'rep') return null
  const totalS = Number(currentItem.value.sets) || 3
  const repsPerS = Number(currentItem.value.reps) || 10
  const total = Number(repCount.value) || 0
  const doneS = Math.floor(total / repsPerS)
  const curR = total % repsPerS
  return { doneS, curR, totalS, repsPerS, total }
})
const fsmState = ref('')
const holdTime = ref(0)
const validKpCount = ref(0)

let ws: WebSocket | null = null
let stream: MediaStream | null = null
let captureTimer: number = 0

async function loadPlans() {
  loading.value = true
  loadError.value = false
  try {
    if (useMock.value) {
      plans.value = mockPlans.filter(p => p.status === 'active')
    } else {
      const r = await prescriptionV2Api.list()
      plans.value = (r.plans || []).filter(p => p.status === 'active')
    }
  } catch {
    if (import.meta.env.DEV) {
      console.warn('[TrainingView] API failed, falling back to mock data')
      plans.value = mockPlans.filter(p => p.status === 'active')
      useMock.value = true
    } else {
      plans.value = []
      loadError.value = true
    }
  } finally {
    loading.value = false
  }
}

function coverGradient(_plan: PlanV2): string {
  return 'linear-gradient(135deg, #e8e0ff 0%, #f0eaff 100%)'
}

async function refreshProgress(planId: number) {
  try {
    if (useMock.value) {
      const mp = mockProgress[planId]
      completedExercises.value = new Set(mp?.completed_item_ids || [])
      itemProgress.value = new Map((mp?.items || []).map((p: any) => [p.plan_item_id, p]))
    } else {
      const progress = await prescriptionV2Api.getProgress(planId)
      completedExercises.value = new Set(progress.completed_item_ids || [])
      itemProgress.value = new Map((progress.items || []).map((p: any) => [p.plan_item_id, p]))
    }
  } catch {
    completedExercises.value = new Set()
    itemProgress.value = new Map()
  }
}

async function selectPlan(plan: PlanV2) {
  selectedPlan.value = plan
  await refreshProgress(plan.id)
  mode.value = 'plan_detail'
}

// ── Phase grouping ──
function getPhaseExercises(plan: PlanV2): Record<string, PlanItemV2[]> {
  const groups: Record<string, PlanItemV2[]> = { warmup: [], main: [], cooldown: [] };
  (plan.items || []).forEach(item => {
    const phase = item.phase || 'main'
    if (!groups[phase]) groups[phase] = []
    groups[phase].push(item)
  })
  return groups
}

// ── New computed properties for hero / toolbar ──
const phaseGroups = computed(() => selectedPlan.value ? getPhaseExercises(selectedPlan.value) : {})
const phaseKeys = computed(() => Object.keys(phaseGroups.value).filter(p => phaseGroups.value[p].length > 0))
const orderedPhases = computed(() => {
  const order = ['warmup', 'main', 'cooldown']
  return order.filter(p => phaseKeys.value.includes(p))
})
const totalExercises = computed(() => (selectedPlan.value?.items || []).length)
const doneCount = computed(() => completedExercises.value.size)

const planProgressPercent = computed(() =>
  totalExercises.value > 0 ? Math.round((doneCount.value / totalExercises.value) * 100) : 0
)

const safeDur = (item: PlanItemV2) => (Number(item.sets) || 0) * (Number(item.duration_seconds) || 0)

const totalDurationSeconds = computed(() =>
  (selectedPlan.value?.items || []).reduce((total, item) => total + safeDur(item), 0)
)
const totalDurationMinutes = computed(() => Math.ceil(totalDurationSeconds.value / 60) || 0)

const remainingDurationSeconds = computed(() => {
  const incompleteItems = (selectedPlan.value?.items || []).filter(
    item => !completedExercises.value.has(item.id)
  )
  return incompleteItems.reduce((total, item) => total + safeDur(item), 0)
})
const remainingMinutes = computed(() => Math.ceil(remainingDurationSeconds.value / 60) || 0)

const phaseBreakdown = computed(() => {
  const groups = phaseGroups.value
  return orderedPhases.value.map(phase => ({
    phase,
    label: PHASE_LABELS[phase] || phase,
    color: PHASE_COLORS[phase] || '#64748b',
    total: groups[phase]?.length || 0,
    done: (groups[phase] || []).filter(item => completedExercises.value.has(item.id)).length,
  }))
})

const motivationalText = computed(() => {
  if (doneCount.value === 0) return '开始你的第一个动作，今天迈出第一步'
  if (planProgressPercent.value >= 100) return '训练全部完成！做得非常棒！'
  if (planProgressPercent.value >= 50) return '过半啦，继续坚持完成剩余动作'
  return '继续完成剩余动作，即将完成今日训练'
})

const recommendedItem = computed<PlanItemV2 | null>(() => {
  if (!selectedPlan.value?.items) return null
  for (const phase of orderedPhases.value) {
    const items = phaseGroups.value[phase] || []
    for (const item of items) {
      if (!completedExercises.value.has(item.id)) return item
    }
  }
  return null
})

const allCompleted = computed(() => doneCount.value >= totalExercises.value && totalExercises.value > 0)

// ── Camera ──
async function startCamera(): Promise<boolean> {
  if (stream) return true
  if (!navigator.mediaDevices?.getUserMedia) return false
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'user' }
    })
    return true
  } catch {
    return false
  }
}

function stopCamera() {
  clearInterval(captureTimer)
  stream?.getTracks().forEach(t => t.stop())
  stream = null
  if (videoRef.value) videoRef.value.srcObject = null
}

function closeWS() {
  clearInterval(captureTimer)
  const socket = ws
  if (socket) {
    socket.onmessage = null
    socket.onclose = null
    socket.onerror = null
    if (socket.readyState === WebSocket.OPEN) socket.close()
    ws = null
  }
}

// ── Skeleton overlay ──
const SKELETON_PAIRS: [number, number][] = [
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [0, 1], [0, 2], [1, 3], [2, 4],
]
const MIN_CONFIDENCE = 0.15

function drawSkeleton(kps: number[][], confidences?: number[]) {
  const canvas = skeletonCanvasRef.value
  const video = videoRef.value
  if (!canvas || !video) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const displayW = video.getBoundingClientRect().width
  const displayH = video.getBoundingClientRect().height
  if (displayW === 0 || displayH === 0) return

  canvas.width = displayW
  canvas.height = displayH
  ctx.clearRect(0, 0, displayW, displayH)

  const scaleX = frameWidth.value > 0 ? displayW / frameWidth.value : 1
  const scaleY = frameHeight.value > 0 ? displayH / frameHeight.value : 1

  const isValid = (idx: number) =>
    idx < kps.length &&
    kps[idx][0] > 0 && kps[idx][1] > 0 &&
    (!confidences || confidences[idx] >= MIN_CONFIDENCE)

  ctx.lineWidth = 3
  ctx.lineCap = 'round'
  for (const [i, j] of SKELETON_PAIRS) {
    if (isValid(i) && isValid(j)) {
      const [x1, y1] = kps[i]
      const [x2, y2] = kps[j]
      ctx.strokeStyle = '#00ff88'
      ctx.beginPath()
      ctx.moveTo(x1 * scaleX, y1 * scaleY)
      ctx.lineTo(x2 * scaleX, y2 * scaleY)
      ctx.stroke()
    }
  }

  for (let i = 0; i < kps.length; i++) {
    if (!isValid(i)) continue
    const [x, y] = kps[i]
    ctx.fillStyle = '#00ff88'
    ctx.beginPath()
    ctx.arc(x * scaleX, y * scaleY, 4, 0, Math.PI * 2)
    ctx.fill()
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 1.5
    ctx.stroke()
  }
}

function captureAndSend() {
  const video = videoRef.value
  const canvas = canvasRef.value
  const socket = ws
  if (!video || !canvas || !socket || socket.readyState !== WebSocket.OPEN) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return
  canvas.width = video.videoWidth || 640
  canvas.height = video.videoHeight || 480
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

  try {
    socket.send(JSON.stringify({ type: 'frame', data: canvas.toDataURL('image/jpeg', 0.7) }))
    frameCount.value++
  } catch { /* ignore */ }
}

// ── Training session ──
async function startSession(): Promise<boolean> {
  const ok = await startCamera()
  if (!ok) return false

  const token = authStore.token || ''
  const socket = createLearningWS(token)
  ws = socket

  return new Promise(resolve => {
    socket.onopen = () => {
      socket.send(JSON.stringify({
        type: 'start',
        action: currentItem.value?.action_name || '',
        view: currentView.value,
      }))
      isSessionActive.value = true
      frameCount.value = 0
      diffs.value = []
      feedbacks.value = []
      overallScore.value = null
      sessionPhase.value = 'waiting_for_body'
      repCount.value = 0
      holdTime.value = 0
      fsmState.value = ''
      validKpCount.value = 0
      resolve(true)
    }

    socket.onmessage = async (event) => {
      const data = JSON.parse(event.data)
      switch (data.type) {
        case 'session_ready':
          standardAngles.value = data.standard_angles || {}
          keyChecks.value = data.key_checks || []
          instruction.value = data.instruction || ''
          currentView.value = data.current_view || currentView.value
          sessionPhase.value = data.session_phase || 'waiting_for_body'
          exerciseType.value = data.exercise_type || ''
          bestScore.value = 0
          userKeypoints.value = null
          userConfidences.value = null
          clearInterval(captureTimer)
          captureTimer = window.setInterval(() => { captureAndSend() }, 200)
          break
        case 'comparison':
          diffs.value = data.diffs || []
          feedbacks.value = data.feedbacks || []
          overallScore.value = data.smoothed_score ?? data.overall_score
          bestScore.value = data.best_smoothed || data.best_score || 0
          sessionPhase.value = data.session_phase || sessionPhase.value
          exerciseType.value = data.exercise_type || exerciseType.value
          repCount.value = data.rep_count ?? repCount.value
          holdTime.value = data.hold_time ?? holdTime.value
          fsmState.value = data.fsm_state ?? fsmState.value
          validKpCount.value = data.valid_kp_count ?? validKpCount.value
          if (data.frame_width) frameWidth.value = data.frame_width
          if (data.frame_height) frameHeight.value = data.frame_height
          if (data.user_keypoints) {
            userKeypoints.value = data.user_keypoints
            userConfidences.value = data.user_confidences || null
            drawSkeleton(data.user_keypoints, data.user_confidences)
          }
          break
        case 'body_confirmed':
          sessionPhase.value = data.session_phase || 'body_confirmed'
          instruction.value = data.message || '已确认人体，请开始动作'
          break
        case 'view_switched':
          currentView.value = data.view
          standardAngles.value = data.standard_angles || {}
          keyChecks.value = data.key_checks || []
          userKeypoints.value = null
          userConfidences.value = null
          break
        case 'learning_complete': {
          stopCamera()
          closeWS()
          isSessionActive.value = false
          // 存入 sessionStorage 供报告页使用
          sessionStorage.setItem('learningCompleteData', JSON.stringify({
            ...data,
            action_name: currentItem.value?.action_name || '',
          }))
          const item = currentItem.value
          const plan = selectedPlan.value
          if (item && plan && !progressSaved.value) {
            try {
              progressSaved.value = true
              await prescriptionV2Api.saveProgress({
                plan_id: plan.id,
                plan_item_id: item.id,
                action_name: item.action_name,
                best_score: data.best_score || 0,
                rep_count: data.rep_count || 0,
                hold_time_seconds: data.hold_time || 0,
                duration_seconds: data.duration || 0,
              })
              await refreshProgress(plan.id)
            } catch {
              message.warning('训练已完成，但进度保存失败')
            }
          }
          result.value = data as LearningComplete
          // 仅当不是 handleFinishAndReport 触发的才跳内联结果
          if (!pendingReport.value) { mode.value = 'result' }
          // 如果是 handleFinishAndReport 触发的，通知它数据已就绪
          if (pendingReport.value && resolveReport) {
            resolveReport()
            resolveReport = null
          }
          break
        }
        case 'error':
          console.error('[Training] WS error:', data.message)
          break
      }
    }

    socket.onerror = () => {
      isSessionActive.value = false
      resolve(false)
    }

    socket.onclose = () => {
      isSessionActive.value = false
    }
  })
}

function endSession() {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'finish' }))
  }
}

function switchView(view: string) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'switch_view', view }))
  }
}

function exitTraining() {
  endSession()
  stopCamera()
  closeWS()
  isSessionActive.value = false
  mode.value = 'plan_detail'
}

// ── Start exercise ──
async function handleStartExercise(item: PlanItemV2) {
  currentItem.value = item
  currentView.value = '正面'
  try {
    const detail = await learningApi.getLearnableDetail(item.action_name)
    currentView.value = detail?.views?.[0] || '正面'
  } catch { /* use default */ }
  const ok = await startCamera()
  if (!ok) { message.error('无法打开摄像头'); return }
  showStartPrompt.value = true
  mode.value = 'ready'
}

// ── Start session from ready ──
async function startReadySession() {
  showStartPrompt.value = false
  progressSaved.value = false
  pendingReport.value = false
  result.value = null
  const ok = await startSession()
  if (ok) mode.value = 'training'
  else message.error('无法启动训练连接')
}

function exitReady() {
  stopCamera()
  showStartPrompt.value = false
  mode.value = 'plan_detail'
}

function handleContinueFromToolbar() {
  if (recommendedItem.value) {
    handleStartExercise(recommendedItem.value)
  }
}

function handleViewReport() {
  // 标准动作学习完成后，跳转到完整训练报告页
  const reportId = result.value?.record_id || 'mock'
  router.push({ path: `/training/report/${reportId}`, query: { planId: selectedPlan.value?.id } })
}

async function handleFinishAndReport() {
  // 中途结束训练并查看报告：通知后端结束、等待 learning_complete、跳转报告页
  pendingReport.value = true
  endSession()
  // 等待 WebSocket 返回 learning_complete（3 秒超时兜底）
  await Promise.race([
    new Promise<void>(resolve => { resolveReport = resolve }),
    new Promise<void>(resolve => setTimeout(resolve, 3000)),
  ])
  resolveReport = null

  stopCamera()
  closeWS()
  isSessionActive.value = false

  // 如果 WebSocket 已保存进度，跳过；否则兜底保存
  if (!progressSaved.value) {
    const item = currentItem.value
    const plan = selectedPlan.value
    if (item && plan) {
      try {
        progressSaved.value = true
        await prescriptionV2Api.saveProgress({
          plan_id: plan.id,
          plan_item_id: item.id,
          action_name: item.action_name,
          best_score: bestScore.value || 0,
          rep_count: repCount.value || 0,
          hold_time_seconds: holdTime.value || 0,
          duration_seconds: Math.floor(frameCount.value * 0.2) || 0,
        })
        await refreshProgress(plan.id)
      } catch { /* ignore */ }
    }
  }

  router.push({ path: '/training/report/direct', query: { planId: selectedPlan.value?.id } })
}

// ── Available views for training ──
const availableViews = ['正面', '侧面']

// ── Camera re-attach after mode switch ──
watch(mode, async (newMode) => {
  if ((newMode === 'ready' || newMode === 'training') && stream) {
    await nextTick()
    if (videoRef.value) {
      videoRef.value.srcObject = stream
      await videoRef.value.play().catch(() => {})
    }
  }
})

// ── Lifecycle ──
onMounted(async () => {
  await loadPlans()
  const planId = route.query.planId
  if (planId) {
    const plan = plans.value.find(p => p.id === Number(planId))
    if (plan) selectPlan(plan)
  }
})
onUnmounted(() => {
  stopCamera()
  closeWS()
})
</script>

<script lang="ts">
export default { name: 'TrainingView' }
</script>

<template>
  <!-- ═══════════════════════════════════════════════════════════ -->
  <!-- PLAN LIST                                                  -->
  <!-- ═══════════════════════════════════════════════════════════ -->
  <template v-if="mode === 'plan_list'">
    <div class="plan-list-page">

      <!-- ── Hero Banner ── -->
      <div class="hero-banner">
        <div class="hero-bg-decor hero-decor-1"></div>
        <div class="hero-bg-decor hero-decor-2"></div>
        <div class="hero-bg-decor hero-decor-3"></div>
        <div class="hero-content">
          <div class="hero-left">
            <div class="hero-greeting">
              <span class="hero-emoji">💪</span>
              <div>
                <h1 class="hero-title">今日训练</h1>
                <p class="hero-subtitle">AI 已根据你的评估为你推荐训练计划</p>
              </div>
            </div>
          </div>
          <div class="hero-right">
            <div class="hero-action-ring" @click="router.push('/prescription-training')">
              <div class="ring-pulse"></div>
              <img class="ring-illustration" src="/media/pictures/start.png" alt="" />
              <span class="ring-label">生成新训练方案</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Loading / Error / Empty states ── -->
      <n-card v-if="loadError && !loading && plans.length === 0" :bordered="false" class="section-card">
        <div style="text-align: center; padding: 40px;">
          <n-icon size="48" :component="WarningOutline" color="#faad14" />
          <p style="font-size: 15px; font-weight: 600;">无法加载训练计划</p>
          <p style="font-size: 13px; color: #64748b;">请检查网络连接后重试</p>
          <n-button type="primary" @click="loadPlans" style="margin-top: 12px;">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            重试
          </n-button>
        </div>
      </n-card>

      <n-card v-else-if="!loading && plans.length === 0" :bordered="false" class="section-card">
        <n-empty description="暂无活跃的训练计划" style="padding: 40px 0;">
          <template #extra>
            <n-button type="primary" @click="router.push('/prescription-training')">
              <template #icon><n-icon :component="FitnessOutline" /></template>
              去生成训练方案
            </n-button>
          </template>
        </n-empty>
      </n-card>

      <!-- ── Training Plans Section ── -->
      <div v-if="plans.length > 0" class="plans-section">
        <div class="section-heading">
          <n-icon size="20" :component="ListOutline" color="#5b5ee6" />
          <span>我的训练计划</span>
          <n-tag size="small" round :bordered="false" type="info">{{ plans.length }} 个计划</n-tag>
        </div>

        <n-spin :show="loading">
          <div class="plan-cards-grid">
            <div
              v-for="plan in plans"
              :key="plan.id"
              class="plan-card-new"
              @click="selectPlan(plan)"
            >
              <!-- Cover -->
              <div class="plan-cover" :style="{ background: coverGradient(plan) }">
                <div class="plan-cover-icon">
                  <n-icon size="28" :component="BarbellOutline" color="#7c6ff7" />
                </div>
                <div class="plan-cover-badge">
                  <n-tag
                    :type="plan.generation_method === 'deepseek' ? 'info' : 'warning'"
                    size="tiny" round :bordered="false"
                  >
                    {{ plan.generation_method === 'deepseek' ? 'AI 生成' : '标准模板' }}
                  </n-tag>
                </div>
              </div>

              <!-- Info -->
              <div class="plan-body">
                <h3 class="plan-name">{{ plan.plan_name }}</h3>
                <div class="plan-meta">
                  <span class="plan-meta-item">
                    <n-icon size="14" :component="StarOutline" :color="DIFFICULTY_COLORS[plan.difficulty] || '#f59e0b'" />
                    {{ DIFFICULTY_LABELS[plan.difficulty] || '初级' }}
                  </span>
                  <span class="plan-meta-item">
                    <n-icon size="14" :component="TimeOutline" color="#94a3b8" />
                    {{ ((plan.items || []).reduce((s, i) => s + (Number(i.sets)||0) * (Number(i.duration_seconds)||0), 0) / 60).toFixed(0) || 0 }} 分钟
                  </span>
                  <span class="plan-meta-item">
                    <n-icon size="14" :component="ListOutline" color="#94a3b8" />
                    {{ (plan.items || []).length }} 个动作
                  </span>
                </div>
                <div class="plan-footer">
                  <span class="plan-date">
                    <n-icon size="13" :component="CalendarOutline" color="#cbd5e1" />
                    {{ plan.created_at?.slice(0, 10) || '-' }}
                  </span>
                  <n-button
                    type="primary"
                    size="small"
                    round
                    :icon="PlayCircleOutline"
                    @click.stop="selectPlan(plan)"
                    class="plan-start-btn"
                  >
                    开始训练
                  </n-button>
                </div>
              </div>
            </div>
          </div>
        </n-spin>
      </div>
    </div>
  </template>

  <!-- ═══════════════════════════════════════════════════════════ -->
  <!-- PLAN DETAIL                                                -->
  <!-- ═══════════════════════════════════════════════════════════ -->
  <template v-else-if="mode === 'plan_detail' && selectedPlan">
    <div class="plan-detail-page">
      <!-- Back button -->
      <div class="back-row">
        <n-button text size="small" @click="mode = 'plan_list'">
          <template #icon><n-icon :component="ArrowBackOutline" /></template>
          返回计划列表
        </n-button>
      </div>

      <!-- Hero card -->
      <TrainingHeroCard
        :plan-name="selectedPlan.plan_name"
        :total-exercises="totalExercises"
        :done-count="doneCount"
        :progress-percent="planProgressPercent"
        :total-duration-minutes="totalDurationMinutes"
        :remaining-minutes="remainingMinutes"
        :motivational-text="motivationalText"
        :phase-breakdown="phaseBreakdown"
      />

      <!-- Phase sections -->
      <div class="phases-container">
        <TrainingPhaseSection
          v-for="phase in orderedPhases"
          :key="phase"
          :phase="phase"
          :phase-label="PHASE_LABELS[phase] || phase"
          :phase-description="PHASE_DESCRIPTIONS[phase] || ''"
          :phase-color="PHASE_COLORS[phase] || '#64748b'"
          :phase-icon="PHASE_ICONS[phase]"
          :items="phaseGroups[phase] || []"
          :completed-exercises="completedExercises"
          :item-progress="itemProgress"
          :recommended-item-id="recommendedItem?.id ?? null"
          @start-exercise="handleStartExercise"
        />
      </div>

    </div>
  </template>

  <!-- ═══════════════════════════════════════════════════════════ -->
  <!-- READY (Camera Preview)                                      -->
  <!-- ═══════════════════════════════════════════════════════════ -->
  <template v-else-if="mode === 'ready'">
    <div class="training-layout">
      <div class="training-topbar">
        <n-space align="center">
          <n-button size="small" @click="exitReady">
            <template #icon><n-icon :component="ArrowBackOutline" /></template>
            返回
          </n-button>
          <span style="font-size: 16px; font-weight: 600;">{{ currentItem?.action_name || '准备中' }}</span>
          <n-tag type="info" size="small" round>摄像头预览</n-tag>
        </n-space>
      </div>

      <div class="training-main">
        <div class="training-video">
          <div class="video-container">
            <video ref="videoRef" autoplay playsinline muted
              style="width: 100%; height: 100%; object-fit: contain;" />
            <div class="ready-overlay" :class="{ hidden: !showStartPrompt }">
              <div class="ready-content">
                <div class="ready-icon-wrap">
                  <n-icon size="48" :component="PlayCircleOutline" color="#fff" />
                </div>
                <h2 class="ready-title">准备开始</h2>
                <p class="ready-desc">请站在摄像头前，确保全身可见</p>
                <n-button
                  class="ready-start-btn"
                  size="large"
                  @click="startReadySession"
                >
                  <template #icon><n-icon size="20" :component="PlayCircleOutline" /></template>
                  开始训练
                </n-button>
              </div>
            </div>
          </div>
        </div>

        <div class="training-analysis">
          <n-card size="small" :bordered="false" class="analysis-card" style="margin-bottom: 12px;">
            <div class="info-rows">
              <div class="info-row"><span class="info-label">动作</span><span>{{ currentItem?.action_name }}</span></div>
              <div class="info-row"><span class="info-label">组数</span><span>{{ currentItem?.sets }} 组 x {{ currentItem?.reps }} 次</span></div>
              <div class="info-row"><span class="info-label">时长</span><span>{{ currentItem?.duration_seconds }}s</span></div>
            </div>
          </n-card>

          <n-card size="small" :bordered="false" title="准备提示" class="analysis-card">
            <ul style="font-size: 13px; color: #64748b; padding-left: 18px; line-height: 2;">
              <li>站在摄像头正前方 2-3 米处</li>
              <li>确保全身可见，光线充足</li>
              <li>穿着贴身衣物以便识别关节</li>
              <li>准备好后点击「开始训练」</li>
            </ul>
          </n-card>
        </div>
      </div>
    </div>
  </template>

  <!-- ═══════════════════════════════════════════════════════════ -->
  <!-- TRAINING SESSION                                           -->
  <!-- ═══════════════════════════════════════════════════════════ -->
  <template v-else-if="mode === 'training'">
    <div class="training-layout">
      <!-- Top bar -->
      <div class="training-topbar">
        <n-space align="center">
          <span style="font-size: 16px; font-weight: 600;">{{ currentItem?.action_name || '训练中' }}</span>
          <n-tag v-if="bestScore > 0" type="warning" size="small" round>
            <template #icon><n-icon :component="TrophyOutline" /></template>
            最佳 {{ bestScore }} 分
          </n-tag>
          <n-tag :type="sessionPhase === 'learning' ? 'success' : 'warning'" size="small" round>
            {{ sessionPhase === 'waiting_for_body' ? '等待人体入镜' : sessionPhase === 'body_confirmed' ? '人体已确认' : '动作识别中' }}
          </n-tag>
          <n-tag v-if="exerciseType === 'rep'" type="info" size="small" round>{{ repCount }} 次</n-tag>
          <n-tag v-else-if="exerciseType === 'hold'" type="info" size="small" round>{{ holdTime.toFixed(1) }} 秒</n-tag>
        </n-space>
        <n-space align="center">
          <span style="font-size: 13px; color: #64748b;">视角:</span>
          <n-space :size="4">
            <n-button
              v-for="v in availableViews"
              :key="v"
              :type="currentView === v ? 'primary' : 'default'"
              size="tiny"
              @click="switchView(v)"
            >{{ v }}</n-button>
          </n-space>
        </n-space>
      </div>

      <!-- Main area: Video + Analysis -->
      <div class="training-main">
        <!-- Video -->
        <div class="training-video">
          <div class="video-container">
            <video ref="videoRef" autoplay playsinline muted
              style="width: 100%; height: 100%; object-fit: contain;" />
            <canvas ref="canvasRef" style="display: none;" />
            <canvas ref="skeletonCanvasRef"
              style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;" />

            <div v-if="isSessionActive" class="video-badge-top">
              <span class="live-indicator">
                <span class="live-dot"></span>
                实时分析中
              </span>
              <n-tag size="tiny">{{ frameCount }} 帧</n-tag>
            </div>

            <div v-if="overallScore !== null" class="score-overlay">
              <div class="score-num" :style="{ color: overallScore >= 70 ? '#52c41a' : overallScore >= 40 ? '#faad14' : '#f5222d' }">
                {{ overallScore }}
              </div>
              <div class="score-label">当前得分</div>
            </div>

            <div v-if="isSessionActive && instruction" class="instruction-bar">
              <n-icon :component="BulbOutline" /> {{ instruction }}
            </div>
          </div>
        </div>

        <!-- Analysis Panel -->
        <div class="training-analysis">
          <!-- Exercise info -->
          <n-card v-if="currentItem" size="small" :bordered="false" class="analysis-card" style="margin-bottom: 12px;">
            <n-descriptions :column="1" size="small" label-placement="left">
              <n-descriptions-item label="动作">{{ currentItem.action_name }}</n-descriptions-item>
              <n-descriptions-item label="组数">{{ currentItem.sets }} 组 x {{ currentItem.reps }} 次</n-descriptions-item>
              <n-descriptions-item label="时长">{{ currentItem.duration_seconds }}s</n-descriptions-item>
            </n-descriptions>
            <p v-if="currentItem.notes" style="font-size: 12px; color: #94a3b8; margin: 4px 0 0;">
              备注: {{ currentItem.notes }}
            </p>
          </n-card>

          <!-- Key checks -->
          <n-card size="small" :bordered="false" title="动作要点" class="analysis-card" style="margin-bottom: 12px;">
            <div v-if="keyChecks.length > 0">
              <div v-for="(check, i) in keyChecks" :key="i" style="margin-bottom: 8px; font-size: 13px;">
                <n-icon :component="EyeOutline" color="#06b6d4" style="margin-right: 6px;" />
                {{ check.rule }}
                <n-tag size="tiny" style="margin-left: 8px;">{{ check.threshold }}{{ check.unit }}</n-tag>
              </div>
            </div>
            <span v-else style="font-size: 13px; color: #94a3b8;">等待数据...</span>
          </n-card>

          <!-- Angle diffs -->
          <n-card size="small" :bordered="false" title="关节角度差异" class="analysis-card" style="margin-bottom: 12px;">
            <template v-if="diffs.length > 0">
              <div v-for="d in diffs" :key="d.joint" style="margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; margin-bottom: 2px;">
                  <n-space :size="4" align="center">
                    <n-icon
                      :component="d.status === 'good' ? CheckmarkCircleOutline : d.status === 'bad' ? CloseCircleOutline : WarningOutline"
                      :color="STATUS_COLORS[d.status]"
                      size="14"
                    />
                    <span>{{ JOINT_LABELS[d.joint] || d.joint }}</span>
                  </n-space>
                  <span>
                    {{ d.user !== null ? `${d.user}°` : '-' }} /
                    <span style="color: #94a3b8;">标准 {{ d.standard_range }}°</span>
                  </span>
                </div>
                <n-progress
                  :percentage="d.percent ?? (d.user !== null ? Math.min(100, (d.user / d.standard_optimal) * 100) : 0)"
                  :color="STATUS_COLORS[d.status]"
                  :height="6"
                  :show-indicator="false"
                />
                <span style="font-size: 11px;" :style="{ color: STATUS_COLORS[d.status] }">{{ STATUS_LABELS[d.status] }}</span>
              </div>
            </template>
            <n-empty v-else description="等待分析数据" />
          </n-card>

          <!-- Feedback -->
          <n-card size="small" :bordered="false" class="analysis-card">
            <template #header>
              <n-space align="center">
                <span>实时反馈</span>
                <n-tag v-if="feedbacks.length > 0" type="error" size="tiny" round>{{ feedbacks.length }}</n-tag>
              </n-space>
            </template>
            <template v-if="feedbacks.length > 0">
              <div
                v-for="(fb, i) in feedbacks"
                :key="i"
                class="feedback-item"
                :class="'feedback-' + fb.severity"
              >
                <n-icon
                  :component="WarningOutline"
                  :color="fb.severity === 'bad' ? '#f5222d' : fb.severity === 'warning' ? '#fa8c16' : '#52c41a'"
                  size="14"
                  style="margin-right: 6px;"
                />
                {{ fb.message }}
              </div>
            </template>
            <div v-else style="text-align: center; padding: 12px; color: #52c41a;">
              <n-icon :component="CheckmarkCircleOutline" size="24" style="margin-bottom: 6px;" />
              <div style="font-size: 13px;">动作标准，继续保持！</div>
            </div>
          </n-card>
        </div>
      </div>

      <!-- Bottom controls -->
      <div class="training-bottom">
        <n-space size="medium" wrap>
          <n-button type="primary" size="large" @click="handleFinishAndReport" :loading="!isSessionActive">
            <template #icon><n-icon :component="DocumentTextOutline" /></template>
            结束并查看报告
          </n-button>
          <n-button type="error" size="large" ghost @click="exitTraining" :loading="!isSessionActive">
            <template #icon><n-icon :component="StopOutline" /></template>
            退出训练
          </n-button>
        </n-space>
      </div>
    </div>
  </template>

  <!-- ═══════════════════════════════════════════════════════════ -->
  <!-- RESULT                                                     -->
  <!-- ═══════════════════════════════════════════════════════════ -->
  <template v-else-if="mode === 'result' && result && selectedPlan">
    <div class="page" style="max-width: 700px; margin: 0 auto;">
      <n-card :bordered="false" class="result-card">
        <div style="text-align: center; margin-bottom: 24px;">
          <n-icon size="48" :component="TrophyOutline" color="#06b6d4" />
          <h2 style="margin: 8px 0 0; font-weight: 700;">训练完成！</h2>
        </div>

        <n-grid :cols="3" style="margin-bottom: 24px;">
          <n-grid-item>
            <div class="result-stat">
              <span class="result-stat-num" :style="{ color: result.total_score >= 70 ? '#52c41a' : '#faad14' }">
                {{ result.total_score }}
              </span>
              <span class="result-stat-label">总分</span>
            </div>
          </n-grid-item>
          <n-grid-item>
            <div class="result-stat">
              <span class="result-stat-num">{{ result.best_score }}</span>
              <span class="result-stat-label">最佳得分</span>
            </div>
          </n-grid-item>
          <n-grid-item>
            <div class="result-stat">
              <span class="result-stat-num">{{ result.frame_count }}</span>
              <span class="result-stat-label">训练帧数</span>
            </div>
          </n-grid-item>
        </n-grid>

        <n-grid :cols="2" style="margin-bottom: 24px;">
          <n-grid-item>
            <div class="result-stat">
              <span class="result-stat-num">{{ (result.duration / 60).toFixed(1) }}</span>
              <span class="result-stat-label">训练时长(分钟)</span>
            </div>
          </n-grid-item>
          <n-grid-item>
            <div class="result-stat">
              <span class="result-stat-num">{{ Object.values(result.feedback_counts || {}).reduce((a: number, b: number) => a + b, 0) }}</span>
              <span class="result-stat-label">反馈次数</span>
            </div>
          </n-grid-item>
        </n-grid>

        <n-card v-if="result.summary?.length > 0" size="small" :bordered="false" title="总结建议" style="margin-bottom: 16px;">
          <div v-for="(s, i) in result.summary" :key="i" style="margin-bottom: 4px; font-size: 13px;">
            {{ s }}
          </div>
        </n-card>

        <div style="text-align: center; font-size: 13px; color: #64748b; margin-bottom: 16px;">
          已完成 {{ doneCount }}/{{ totalExercises }} 个动作
        </div>

        <n-divider />

        <n-space justify="center" size="medium" wrap>
          <n-button size="large" @click="mode = 'plan_detail'">
            <template #icon><n-icon :component="ArrowBackOutline" /></template>
            返回计划
          </n-button>
          <n-button v-if="doneCount < totalExercises" type="primary" size="large" @click="mode = 'plan_detail'">
            <template #icon><n-icon :component="ArrowForwardOutline" /></template>
            下一个动作
          </n-button>
          <n-button size="large" type="info" ghost @click="handleViewReport">
            <template #icon><n-icon :component="DocumentTextOutline" /></template>
            查看完整报告
          </n-button>
          <n-button size="large" @click="mode = 'plan_list'; loadPlans();">
            <template #icon><n-icon :component="ListOutline" /></template>
            所有计划
          </n-button>
        </n-space>
      </n-card>
    </div>
  </template>

  <!-- Fallback -->
  <div v-else class="page" style="max-width: 900px; margin: 0 auto;">
    <n-spin :show="loading">
      <n-grid v-if="plans.length > 0" :cols="2" :x-gap="16" :y-gap="16" responsive="screen">
        <n-grid-item v-for="plan in plans" :key="plan.id">
          <n-card hoverable :bordered="false" class="plan-card" @click="selectPlan(plan)">
            <n-space align="center">
              <n-icon :component="ListOutline" color="#06b6d4" />
              <span style="font-weight: 600;">{{ plan.plan_name }}</span>
            </n-space>
          </n-card>
        </n-grid-item>
      </n-grid>
    </n-spin>
  </div>
</template>

<style scoped>
/* ── Common ── */
.page { padding: 8px 0; }
.page-header { margin-bottom: 20px; }
.section-card { border-radius: 12px !important; }

/* ── Plan List Page ── */
.plan-list-page {
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Hero Banner */
.hero-banner {
  position: relative;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20px;
  padding: 32px 36px;
  color: #fff;
  overflow: hidden;
}
.hero-bg-decor {
  position: absolute;
  border-radius: 50%;
  background: rgba(255,255,255,0.08);
  pointer-events: none;
}
.hero-decor-1 {
  width: 260px; height: 260px;
  top: -60px; right: -40px;
}
.hero-decor-2 {
  width: 140px; height: 140px;
  bottom: -30px; right: 25%;
  background: rgba(255,255,255,0.06);
}
.hero-decor-3 {
  width: 80px; height: 80px;
  top: 40px; right: 35%;
  background: rgba(255,255,255,0.1);
}
.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}
.hero-left { flex: 1; min-width: 0; }
.hero-greeting {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
}
.hero-emoji { font-size: 36px; line-height: 1; flex-shrink: 0; }
.hero-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 2px;
  color: #fff;
}
.hero-subtitle {
  font-size: 13px;
  margin: 0;
  color: rgba(255,255,255,0.8);
}
.hero-right { flex-shrink: 0; }
.hero-action-ring {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: rgba(255,255,255,0.15);
  backdrop-filter: blur(8px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid rgba(255,255,255,0.25);
  position: relative;
}
.hero-action-ring:hover {
  transform: scale(1.08);
  background: rgba(255,255,255,0.22);
  border-color: rgba(255,255,255,0.4);
}
.hero-action-ring:active {
  transform: scale(0.96);
}
.ring-pulse {
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  border: 2px dashed rgba(255,255,255,0.2);
  animation: ring-spin-plan 10s linear infinite;
  pointer-events: none;
}
@keyframes ring-spin-plan {
  to { transform: rotate(360deg); }
}
.ring-illustration {
  width: 100px;
  height: 100px;
  object-fit: contain;
  position: relative;
  z-index: 2;
}
.ring-label {
  position: absolute;
  bottom: 14px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 11px;
  font-weight: 600;
  color: rgba(255,255,255,0.95);
  z-index: 3;
  text-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

/* Section heading */
.section-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 16px;
}

/* Plan cards grid */
.plans-section { }
.plan-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

/* New plan card */
.plan-card-new {
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  border: 1px solid rgba(0,0,0,0.04);
}
.plan-card-new:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(102,126,234,0.14);
  border-color: rgba(102,126,234,0.15);
}
.plan-cover {
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.plan-cover-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(124,111,247,0.12);
  display: flex;
  align-items: center;
  justify-content: center;
}
.plan-cover-badge {
  position: absolute;
  top: 10px;
  right: 12px;
}
.plan-body {
  padding: 16px 18px 18px;
}
.plan-name {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.plan-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}
.plan-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #64748b;
}
.plan-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.plan-date {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #94a3b8;
}
.plan-start-btn {
  font-weight: 600;
}

/* ── Plan Detail Page ── */
.plan-detail-page {
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 40px;
}
.back-row {
  margin-bottom: 4px;
}
.phases-container {
  display: flex;
  flex-direction: column;
}

/* ── Plan List legacy (fallback) ── */
.plan-card {
  border-radius: 12px !important;
  cursor: pointer;
  transition: all 0.2s ease;
}
.plan-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

/* ── Training Session ── */
.training-layout {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
  gap: 0;
}
.training-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  flex-shrink: 0;
}
.training-main {
  display: flex;
  flex: 1;
  gap: 16px;
  overflow: hidden;
  min-height: 0;
}
.training-video {
  flex: 2;
  min-width: 0;
}
.video-container {
  position: relative;
  width: 100%;
  height: 100%;
  background: #000;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.video-badge-top {
  position: absolute;
  top: 12px;
  left: 12px;
  display: flex;
  gap: 8px;
  align-items: center;
}
.live-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #fff;
  background: rgba(0,0,0,0.5);
  padding: 4px 10px;
  border-radius: 20px;
}
.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #52c41a;
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.score-overlay {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(0,0,0,0.7);
  border-radius: 12px;
  padding: 8px 16px;
  text-align: center;
}
.score-num {
  font-size: 28px;
  font-weight: 700;
}
.score-label {
  font-size: 12px;
  color: #fff;
}
.instruction-bar {
  position: absolute;
  bottom: 12px;
  left: 12px;
  right: 12px;
  background: rgba(0,0,0,0.6);
  border-radius: 8px;
  padding: 8px 16px;
  color: #fff;
  font-size: 13px;
}
.training-analysis {
  flex: 1;
  overflow-y: auto;
  min-width: 280px;
}
.analysis-card {
  border-radius: 10px !important;
}
.feedback-item {
  padding: 8px 12px;
  margin-bottom: 6px;
  border-radius: 6px;
  font-size: 13px;
}
.feedback-bad {
  background: rgba(245,34,45,0.1);
  border: 1px solid rgba(245,34,45,0.2);
}
.feedback-warning {
  background: rgba(250,140,22,0.1);
  border: 1px solid rgba(250,140,22,0.2);
}
.feedback-good {
  background: rgba(82,196,26,0.1);
  border: 1px solid rgba(82,196,26,0.2);
}
.training-bottom {
  text-align: center;
  padding: 12px 0 4px;
  flex-shrink: 0;
}

/* ── Result ── */
.result-card {
  border-radius: 16px !important;
}
.result-stat {
  text-align: center;
  display: flex;
  flex-direction: column;
}
.result-stat-num {
  font-size: 26px;
  font-weight: 700;
  color: #334155;
}
.result-stat-label {
  font-size: 12px;
  color: #94a3b8;
}

/* ── Ready overlay ── */
.ready-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  transition: opacity 0.3s;
}
.ready-overlay.hidden {
  opacity: 0;
  pointer-events: none;
}
.ready-content {
  text-align: center;
  color: #fff;
}
.ready-icon-wrap {
  width: 80px; height: 80px;
  border-radius: 50%;
  background: rgba(255,255,255,0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  border: 2px solid rgba(255,255,255,0.25);
}
.ready-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 8px;
}
.ready-desc {
  font-size: 14px;
  opacity: 0.75;
  margin: 0 0 24px;
}
.ready-start-btn {
  background: linear-gradient(135deg, #7B6CFF, #5C8CFF) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 14px !important;
  padding: 14px 40px !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  height: auto !important;
  box-shadow: 0 4px 20px rgba(123,108,255,0.4) !important;
  transition: all 0.3s ease !important;
}
.ready-start-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(123,108,255,0.5) !important;
}

/* ── Info rows ── */
.info-rows { display: flex; flex-direction: column; gap: 0; }
.info-row { display: flex; align-items: center; font-size: 13px; gap: 8px; }
.info-label { width: 60px; flex-shrink: 0; color: #94a3b8; }

/* ── Mobile ── */
@media (max-width: 768px) {
  .hero-banner {
    padding: 24px 20px;
  }
  .hero-content {
    flex-direction: column;
    align-items: flex-start;
  }
  .plan-list-page .hero-right {
    align-self: center;
  }
  .hero-title {
    font-size: 20px;
  }
  .plan-cards-grid {
    grid-template-columns: 1fr;
  }
  .plan-detail-page {
    padding: 0 4px 40px;
  }
  .training-main {
    flex-direction: column;
  }
  .training-video {
    flex: none;
    height: 50%;
  }
  .training-analysis {
    overflow-y: visible;
    min-width: auto;
  }
}
</style>
