<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { learningApi, createLearningWS } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { LearnableAction, LearnableActionDetail, AngleDiff, LearningFeedback, LearningComplete } from '../types'
import {
  NCard, NButton, NSpace, NTag, NIcon, NProgress, NEmpty, NSpin,
  NGrid, NGridItem,
  NModal, NDivider, NInput, NSelect, useMessage
} from 'naive-ui'
import {
  SchoolOutline, PlayCircleOutline, CheckmarkCircleOutline,
  ArrowBackOutline, SearchOutline, EyeOutline,
  TrophyOutline, BulbOutline, WarningOutline, CloseCircleOutline,
  StopOutline, RefreshOutline, InformationCircleOutline,
  BarbellOutline, CameraOutline, DocumentTextOutline
} from '@vicons/ionicons5'

const router = useRouter()
const authStore = useAuthStore()
const message = useMessage()

// ── Mode state ──
type PageMode = 'list' | 'demo' | 'ready' | 'learning' | 'result'
const mode = ref<PageMode>('list')
const showStartPrompt = ref(false)

// ── Demo / preview state ──
const demoAction = ref<LearnableActionDetail | null>(null)
const demoLoading = ref(false)
const demoMediaFailed = ref(false)

// ── Action catalog ──
const learnableActions = ref<LearnableAction[]>([])
const loading = ref(true)
const searchQuery = ref('')
const filterCategory = ref('')
const filterFamily = ref('')

// Detail modal
const detailVisible = ref(false)
const detailAction = ref<LearnableActionDetail | null>(null)
const detailLoading = ref(false)

// ── Computed for filtering ──
const categories = computed(() => [...new Set(learnableActions.value.map(a => a.category).filter(Boolean))].sort())
const families = computed(() => [...new Set(learnableActions.value.map(a => a.family_name).filter(Boolean))].sort())

const filteredActions = computed(() => {
  let list = learnableActions.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(a =>
      a.name.toLowerCase().includes(q) || a.description.toLowerCase().includes(q) || a.action_id.toLowerCase().includes(q)
    )
  }
  if (filterCategory.value && filterCategory.value !== '') {
    list = list.filter(a => a.category === filterCategory.value)
  }
  if (filterFamily.value && filterFamily.value !== '') {
    list = list.filter(a => a.family_name === filterFamily.value)
  }
  return [...list].sort((a, b) => {
    if (a.has_standard_angles !== b.has_standard_angles) return a.has_standard_angles ? -1 : 1
    return a.difficulty - b.difficulty
  })
})

// ── Current session action ──
const currentAction = ref<LearnableAction | null>(null)

// ── Detail actions ──
async function openDetail(action: LearnableAction) {
  detailVisible.value = true
  detailLoading.value = true
  try {
    detailAction.value = await learningApi.getLearnableDetail(action.name)
  } catch {
    message.error('加载动作详情失败')
    detailAction.value = null
  } finally {
    detailLoading.value = false
  }
}

// ── Open demo / preview page ──
async function openDemo(action: LearnableAction) {
  currentAction.value = action
  demoLoading.value = true
  demoMediaFailed.value = false
  try {
    demoAction.value = await learningApi.getLearnableDetail(action.name)
    mode.value = 'demo'
  } catch {
    message.error('加载动作详情失败')
  } finally {
    demoLoading.value = false
  }
}

// ── Start learning from demo ──
async function startFromDemo() {
  if (!demoAction.value) return
  currentView.value = demoAction.value.views?.[0] || '正面'
  const ok = await startCamera()
  if (!ok) {
    message.error('无法打开摄像头')
    return
  }
  mode.value = 'ready'
  showStartPrompt.value = true
}

// ── Start learning (camera preview) ── (kept for detail modal shortcut)
async function startLearning(action: LearnableAction) {
  currentAction.value = action
  detailVisible.value = false
  currentView.value = action.views?.[0] || '正面'
  try {
    const detail = await learningApi.getLearnableDetail(action.name)
    currentView.value = detail?.views?.[0] || currentView.value
  } catch { /* use catalog view */ }
  const ok = await startCamera()
  if (!ok) {
    message.error('无法打开摄像头')
    return
  }
  mode.value = 'ready'
  showStartPrompt.value = true
}

// ── Training session ──
const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const skeletonCanvasRef = ref<HTMLCanvasElement | null>(null)
const userKeypoints = ref<number[][] | null>(null)
const userConfidences = ref<number[] | null>(null)
const frameWidth = ref(640)
const frameHeight = ref(480)
const isSessionActive = ref(false)
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
const exerciseType = ref('')
const repCount = ref(0)
const holdTime = ref(0)
const validKpCount = ref(0)

let ws: WebSocket | null = null
let stream: MediaStream | null = null
let captureTimer: number = 0
let pendingReport = false
let reportTimeout: number = 0
const reporting = ref(false)

const STATUS_COLORS: Record<string, string> = {
  good: '#52c41a', close: '#faad14', warning: '#fa8c16', bad: '#f5222d', unknown: '#d9d9d9'
}
const STATUS_LABELS: Record<string, string> = {
  good: '优秀', close: '接近', warning: '注意', bad: '偏差', unknown: '未知'
}
const JOINT_LABELS: Record<string, string> = {
  trunk_tilt: '躯干倾斜', neck_tilt: '颈部倾斜',
  left_hip: '左髋角', right_hip: '右髋角',
  left_knee: '左膝角', right_knee: '右膝角',
  left_shoulder: '左肩角', right_shoulder: '右肩角',
  left_elbow: '左肘角', right_elbow: '右肘角',
  left_ankle: '左踝角', right_ankle: '右踝角',
}

async function startCamera(): Promise<boolean> {
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

// ── Skeleton overlay drawing ──
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

  // Display size from video element
  const displayW = video.getBoundingClientRect().width
  const displayH = video.getBoundingClientRect().height
  if (displayW === 0 || displayH === 0) return

  canvas.width = displayW
  canvas.height = displayH
  ctx.clearRect(0, 0, displayW, displayH)

  // Scale from YOLO frame space → display space (matching React SkeletonOverlay)
  const scaleX = frameWidth.value > 0 ? displayW / frameWidth.value : 1
  const scaleY = frameHeight.value > 0 ? displayH / frameHeight.value : 1

  const isValid = (idx: number) =>
    idx < kps.length &&
    kps[idx][0] > 0 && kps[idx][1] > 0 &&
    (!confidences || confidences[idx] >= MIN_CONFIDENCE)

  // Draw skeleton lines
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

  // Draw joint dots
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

function startSession() {
  showStartPrompt.value = false
  const token = authStore.token || ''
  if (!token) {
    message.error('未登录，请先登录后再开始训练')
    mode.value = 'ready'
    return
  }
  const socket = createLearningWS(token)
  ws = socket

  socket.onopen = () => {
    socket.send(JSON.stringify({
      type: 'start',
      action: currentAction.value?.name || '',
      view: currentView.value,
    }))
    isSessionActive.value = true
    mode.value = 'learning'
    frameCount.value = 0
    diffs.value = []
    feedbacks.value = []
    overallScore.value = null
    sessionPhase.value = 'waiting_for_body'
    exerciseType.value = ''
    repCount.value = 0
    holdTime.value = 0
  }

  socket.onmessage = (event) => {
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
      case 'learning_complete':
        console.log('[Learning] learning_complete received, record_id:', (data as LearningComplete).record_id, 'pendingReport:', pendingReport)
        console.log('[Learning] best_frame_diffs:', (data as any).best_frame_diffs?.length, 'best_frame_angles:', Object.keys((data as any).best_frame_angles || {}).length, 'best_frame_feedbacks:', (data as any).best_frame_feedbacks?.length)
        reporting.value = false
        stopCamera()
        closeWS()
        isSessionActive.value = false
        result.value = data as LearningComplete
        clearTimeout(reportTimeout)
        // 将 learning_complete 数据 + 动作名存入 sessionStorage，供报告页直接使用
        sessionStorage.setItem('learningCompleteData', JSON.stringify({
          ...data,
          action_name: currentAction.value?.name || '',
        }))
        if (pendingReport) {
          pendingReport = false
          console.log('[Learning] Navigating to report (direct from session)')
          router.push('/training/report/direct')
        } else {
          console.log('[Learning] Showing result page')
          mode.value = 'result'
        }
        break
      case 'error':
        console.error('[Learning] WS error:', data.message)
        message.error(data.message || '训练出错')
        break
    }
  }

  socket.onerror = (e) => {
    console.error('[Learning] WebSocket error:', e)
    isSessionActive.value = false
    message.error('WebSocket 连接失败，请检查后端服务是否启动')
  }
  socket.onclose = (e) => {
    isSessionActive.value = false
    if (e.code !== 1000) {
      console.warn('[Learning] WebSocket closed abnormally:', e.code, e.reason)
      if (e.code === 4001) {
        message.error('认证失败，请重新登录')
      } else if (e.code === 4003) {
        message.error('用户不存在')
      } else if (e.code !== 1000 && e.code !== 1005 && e.code !== 1006) {
        message.error(`连接异常关闭 (${e.code})`)
      }
    }
  }
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

function exitReady() {
  stopCamera()
  showStartPrompt.value = false
  mode.value = 'list'
  demoAction.value = null
}

function exitLearning() {
  endSession()
  stopCamera()
  closeWS()
  isSessionActive.value = false
  mode.value = 'list'
}

function handleFinishAndReport() {
  console.log('[Learning] handleFinishAndReport - sending finish')
  reporting.value = true
  pendingReport = true
  endSession()
  // 兜底超时：3 秒后若仍未收到 learning_complete，用已有数据跳转
  reportTimeout = window.setTimeout(() => {
    if (!pendingReport) return
    console.warn('[Learning] Timeout - navigating without learning_complete')
    reporting.value = false
    pendingReport = false
    stopCamera()
    closeWS()
    isSessionActive.value = false
    // 用本地已有数据构建简易 learning_complete
    const fallbackData = {
      type: 'learning_complete' as const,
      record_id: null as number | null,
      total_score: bestScore.value,
      best_score: bestScore.value,
      duration: Math.floor(frameCount.value * 0.2),
      frame_count: frameCount.value,
      summary: [],
      feedback_counts: {} as Record<string, number>,
      angle_history: [] as any[],
      best_frame_angles: {} as Record<string, number>,
      best_frame_diffs: [] as any[],
      best_frame_feedbacks: [] as any[],
      best_frame_kp: null,
      best_frame_conf: null,
    }
    sessionStorage.setItem('learningCompleteData', JSON.stringify({
      ...fallbackData,
      action_name: currentAction.value?.name || '',
    }))
    router.push('/training/report/direct')
  }, 3000)
}

// ── Result ──
const result = ref<LearningComplete | null>(null)

// ── Catalog ──
async function loadCatalog() {
  console.log('[LearningView] loadCatalog start')
  loading.value = true
  try {
    const data = await learningApi.getLearnable()
    console.log('[LearningView] loadCatalog got', data.length, 'actions')
    learnableActions.value = (Array.isArray(data) ? data : [])
      .map((action: any) => ({
        ...action,
        name: String(action?.name || ''),
        action_id: String(action?.action_id || ''),
        family: String(action?.family || ''),
        family_name: String(action?.family_name || '未分类'),
        category: String(action?.category || '未分类'),
        subcategory: String(action?.subcategory || ''),
        description: String(action?.description || ''),
        intensity: String(action?.intensity || 'MEDIUM'),
        difficulty: Number(action?.difficulty) || 1,
        phases: Array.isArray(action?.phases) ? action.phases : [],
        target_body_parts: Array.isArray(action?.target_body_parts) ? action.target_body_parts : [],
        steps: Array.isArray(action?.steps) ? action.steps : [],
        cues: Array.isArray(action?.cues) ? action.cues : [],
        views: Array.isArray(action?.views) && action.views.length ? action.views : ['正面'],
        common_errors: Array.isArray(action?.common_errors) ? action.common_errors : [],
        has_standard_angles: Boolean(action?.has_standard_angles)
      }))
      .filter(action => action.name)
  } catch (e) {
    console.error('[LearningView] loadCatalog error:', e)
    learnableActions.value = []
  } finally {
    loading.value = false
    console.log('[LearningView] loadCatalog done, loading:', loading.value, 'actions:', learnableActions.value.length)
  }
}

// ── Camera re-attach after mode switch ──
watch(mode, async (newMode) => {
  if ((newMode === 'ready' || newMode === 'learning') && stream) {
    await nextTick()
    if (videoRef.value) {
      videoRef.value.srcObject = stream
      await videoRef.value.play().catch(() => {})
    }
  }
})

// ── Lifecycle ──
onMounted(() => { loadCatalog() })
onUnmounted(() => {
  stopCamera()
  closeWS()
})
</script>

<script lang="ts">
export default { name: 'LearningView' }
</script>

<template>
  <!-- ═══════════════════════════ ACTION CATALOG ═══════════════════════════ -->
  <template v-if="mode === 'list'">
    <div class="page" style="max-width: 1100px; margin: 0 auto;">
      <div class="page-header">
        <n-space align="center">
          <n-icon size="24" :component="SchoolOutline" color="#5b5ee6" />
          <h2 style="margin: 0; font-size: 22px; font-weight: 700;">标准动作学习</h2>
        </n-space>
        <p style="margin: 4px 0 0; font-size: 13px; color: #64748b;">
          共 {{ learnableActions.length }} 个标准动作，含实时对比功能的动作优先展示
        </p>
      </div>

      <!-- Filters -->
      <n-space align="center" style="margin-bottom: 20px;" :wrap="true">
        <n-input
          v-model:value="searchQuery"
          placeholder="搜索动作名称..."
          clearable
          style="width: 220px;"
        >
          <template #prefix>
            <n-icon :component="SearchOutline" />
          </template>
        </n-input>
        <n-select
          v-model:value="filterCategory"
          :options="categories.map(c => ({ label: c, value: c }))"
          placeholder="分类筛选"
          clearable
          style="width: 140px;"
        />
        <n-select
          v-model:value="filterFamily"
          :options="families.map(f => ({ label: f, value: f }))"
          placeholder="家族筛选"
          clearable
          style="width: 140px;"
        />
        <n-tag size="small" round>共 {{ filteredActions.length }} 个</n-tag>
      </n-space>

      <div v-if="loading" style="text-align: center; padding: 60px 0;">
        <n-spin :show="true" />
      </div>

      <n-empty v-else-if="filteredActions.length === 0" description="未找到匹配的动作" style="padding: 60px 0;">
        <template #extra>
          <n-button @click="loadCatalog">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            刷新
          </n-button>
        </template>
      </n-empty>

      <div v-else class="action-grid-html">
        <div
          v-for="action in filteredActions"
          :key="action.action_id"
          class="action-card-html"
        >
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <n-icon
                :component="action.has_standard_angles ? CameraOutline : BarbellOutline"
                :color="action.has_standard_angles ? '#52c41a' : '#94a3b8'"
                size="20"
              />
              <strong style="font-size: 16px;">{{ action.name }}</strong>
            </div>
            <n-tag v-if="action.has_standard_angles" type="success" size="tiny" round>实时对比</n-tag>
          </div>

          <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px;">
            <n-tag size="tiny" type="info">{{ action.family_name }}</n-tag>
            <n-tag size="tiny">{{ action.category }}</n-tag>
            <n-tag size="tiny" :type="action.difficulty <= 2 ? 'success' : action.difficulty <= 4 ? 'warning' : 'error'">
              {{ '⭐'.repeat(action.difficulty) }}
            </n-tag>
            <n-tag size="tiny" type="default">{{ action.intensity }}</n-tag>
          </div>

          <p class="action-desc-text">{{ action.description }}</p>

          <div v-if="action.target_body_parts?.length" style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px;">
            <n-tag
              v-for="part in action.target_body_parts.slice(0, 4)"
              :key="part"
              size="tiny"
              :bordered="false"
              style="background: #eef2ff; color: #6366f1;"
            >
              {{ part }}
            </n-tag>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px;">
            <n-button size="small" @click="openDetail(action)">
              <template #icon><n-icon :component="InformationCircleOutline" /></template>
              查看详情
            </n-button>
            <n-button
              :type="action.has_standard_angles ? 'primary' : 'default'"
              size="small"
              @click="openDemo(action)"
            >
              <template #icon><n-icon :component="PlayCircleOutline" /></template>
              开始标准学习
            </n-button>
          </div>
        </div>
      </div>
    </div>
  </template>

  <!-- ═══════════════════════════ DEMO (Action Preview) ═══════════════════════════ -->
  <template v-else-if="mode === 'demo' && demoAction">
    <div class="demo-page">
      <div class="demo-header">
        <n-space align="center">
          <n-icon size="24" :component="SchoolOutline" color="#5b5ee6" />
          <h2 style="margin: 0; font-size: 20px; font-weight: 700;">{{ demoAction.name }} — 标准动作示范</h2>
        </n-space>
        <n-button @click="mode = 'list'">
          <template #icon><n-icon :component="ArrowBackOutline" /></template>
          返回列表
        </n-button>
      </div>

      <n-spin :show="demoLoading">
        <n-card :bordered="false" style="border-radius: 12px;">

          <!-- 视频 / 图片 / 占位示范 -->
          <div class="demo-media-box">
            <template v-if="!demoMediaFailed && demoAction.video_url">
              <video
                :src="demoAction.video_url"
                controls autoplay loop muted playsinline
                :poster="demoAction.thumbnail_url || undefined"
                style="width: 100%; height: 100%; object-fit: contain;"
                @error="demoMediaFailed = true"
              />
            </template>
            <template v-else-if="!demoMediaFailed && demoAction.thumbnail_url">
              <img
                :src="demoAction.thumbnail_url"
                :alt="demoAction.name"
                style="width: 100%; height: 100%; object-fit: contain;"
                @error="demoMediaFailed = true"
              />
            </template>
            <template v-else>
              <div class="demo-fallback">
                <n-icon size="64" :component="BarbellOutline" color="#6366f1" />
                <p style="color: #94a3b8; font-size: 14px;">{{ demoAction.description || '请观察标准动作示范' }}</p>
              </div>
            </template>
            <n-tag type="info" round :bordered="false" class="demo-badge">标准示范</n-tag>
          </div>

          <!-- 动作步骤 + 动作要领 -->
          <n-grid :cols="2" :x-gap="12" style="margin-bottom: 12px;">
            <n-grid-item v-if="demoAction.steps?.length">
              <n-card title="动作步骤" size="small" :bordered="false" style="border-radius: 10px;">
                <div v-for="(step, i) in demoAction.steps" :key="i" style="display: flex; gap: 8px; margin-bottom: 4px; align-items: flex-start;">
                  <n-tag :bordered="false" type="info" size="tiny" style="flex-shrink: 0; margin-top: 2px;">{{ i + 1 }}</n-tag>
                  <span style="font-size: 13px; line-height: 1.5;">{{ step }}</span>
                </div>
              </n-card>
            </n-grid-item>
            <n-grid-item>
              <n-card v-if="demoAction.cues?.length" title="动作要领" size="small" :bordered="false" style="border-radius: 10px; margin-bottom: 8px;">
                <n-space wrap :size="4">
                  <n-tag v-for="(cue, i) in demoAction.cues" :key="i" type="info" size="small" round :bordered="false">
                    <template #icon><n-icon :component="EyeOutline" /></template>
                    {{ cue }}
                  </n-tag>
                </n-space>
              </n-card>
              <n-card v-if="demoAction.target_body_parts?.length" title="目标部位" size="small" :bordered="false" style="border-radius: 10px;">
                <n-space wrap :size="4">
                  <n-tag v-for="bp in demoAction.target_body_parts" :key="bp" size="small" :bordered="false" style="background: #eef2ff; color: #6366f1;">
                    {{ bp }}
                  </n-tag>
                </n-space>
              </n-card>
            </n-grid-item>
          </n-grid>

          <!-- 常见错误 -->
          <n-card v-if="demoAction.common_errors?.length" title="常见错误" size="small" :bordered="false" style="border-radius: 10px; margin-bottom: 12px;">
            <div v-for="(err, i) in demoAction.common_errors" :key="i" style="margin-bottom: 6px;">
              <span style="font-weight: 600; color: var(--n-error-color, #d03050); font-size: 13px;">{{ err.name }}</span>
              <span style="font-size: 12px; color: #64748b; margin-left: 8px;">{{ err.feedback }}</span>
            </div>
          </n-card>

          <!-- 标准角度信息 -->
          <n-card v-if="demoAction.standard_keypoints && Object.keys(demoAction.standard_keypoints).length" title="标准关节角度" size="small" :bordered="false" style="border-radius: 10px; margin-bottom: 12px;">
            <div v-for="(vdata, view) in demoAction.standard_keypoints" :key="view" style="margin-bottom: 8px;">
              <n-space align="center" style="margin-bottom: 4px;">
                <n-tag type="success" size="tiny" round :bordered="false">{{ view }}</n-tag>
                <span style="font-size: 12px; color: #94a3b8;">{{ vdata.description }}</span>
              </n-space>
              <n-space wrap :size="4" v-if="vdata.target_angles">
                <n-tag v-for="(range, joint) in vdata.target_angles" :key="joint" size="tiny" type="info">
                  {{ joint }}: {{ range.min }}°–{{ range.max }}° (最优 {{ range.optimal }}°)
                </n-tag>
              </n-space>
            </div>
          </n-card>

          <!-- 元信息 -->
          <n-space align="center" style="margin-bottom: 16px;">
            <span style="font-size: 13px; color: #64748b;">支持视角：</span>
            <n-tag v-for="v in demoAction.views" :key="v" size="small" round :bordered="false">{{ v }}</n-tag>
            <n-divider vertical />
            <span style="font-size: 13px; color: #64748b;">难度：</span>
            <n-tag size="small" :type="demoAction.difficulty <= 2 ? 'success' : demoAction.difficulty <= 4 ? 'warning' : 'error'" round :bordered="false">
              {{ '⭐'.repeat(demoAction.difficulty) }}
            </n-tag>
          </n-space>

          <!-- 进入训练按钮 -->
          <div style="text-align: center; padding-top: 8px;">
            <template v-if="demoAction.has_standard_angles">
              <n-button type="primary" size="large" @click="startFromDemo" style="height: 48px; padding: 0 32px; font-size: 16px; border-radius: 8px;">
                <template #icon><n-icon size="20" :component="PlayCircleOutline" /></template>
                学习完毕，亲自上阵
              </n-button>
              <p style="margin-top: 8px; font-size: 12px; color: #94a3b8;">
                点击后将打开摄像头，实时检测动作并给出反馈
              </p>
            </template>
            <template v-else>
              <n-card :bordered="false" style="background: #fef3c7; border-radius: 10px; text-align: center;">
                <n-space align="center" justify="center">
                  <n-icon size="20" :component="WarningOutline" color="#f59e0b" />
                  <span style="color: #92400e; font-size: 14px;">该动作暂未配置标准角度数据，无法进行实时对比学习</span>
                </n-space>
                <div style="margin-top: 8px;">
                  <n-button @click="mode = 'list'">返回列表</n-button>
                </div>
              </n-card>
            </template>
          </div>

        </n-card>
      </n-spin>
    </div>
  </template>

  <!-- ═══════════════════════════ READY (Camera Preview) ═══════════════════════════ -->
  <template v-else-if="mode === 'ready'">
    <div class="training-layout">
      <div class="training-topbar">
        <n-space align="center">
          <n-button size="small" @click="exitReady">
            <template #icon><n-icon :component="ArrowBackOutline" /></template>
            返回
          </n-button>
          <span style="font-size: 16px; font-weight: 600;">{{ currentAction?.name || '准备中' }}</span>
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
                  @click="startSession"
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
              <div class="info-row"><span class="info-label">动作</span><span>{{ currentAction?.name }}</span></div>
              <div class="info-row"><span class="info-label">家族</span><span>{{ currentAction?.family_name }}</span></div>
              <div class="info-row"><span class="info-label">难度</span>
                <n-tag size="tiny" :type="currentAction && currentAction.difficulty <= 2 ? 'success' : currentAction && currentAction.difficulty <= 4 ? 'warning' : 'error'">
                  {{ '⭐'.repeat(currentAction?.difficulty || 1) }}
                </n-tag>
              </div>
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

  <!-- ═══════════════════════════ TRAINING SESSION ═══════════════════════════ -->
  <template v-else-if="mode === 'learning'">
    <div class="training-layout">
      <div class="training-topbar">
        <n-space align="center">
          <span style="font-size: 16px; font-weight: 600;">{{ currentAction?.name || '训练中' }}</span>
          <n-tag v-if="bestScore > 0" type="warning" size="small" round>
            <template #icon><n-icon :component="TrophyOutline" /></template>
            最佳 {{ bestScore }} 分
          </n-tag>
          <n-tag :type="sessionPhase === 'learning' ? 'success' : 'warning'" size="small" round>
            {{ sessionPhase === 'waiting_for_body' ? `等待人体入镜（${validKpCount} 个关键点）` : sessionPhase === 'body_confirmed' ? '人体已确认' : '动作识别中' }}
          </n-tag>
          <n-tag v-if="exerciseType === 'rep'" type="info" size="small" round>{{ repCount }} 次</n-tag>
          <n-tag v-else-if="exerciseType === 'hold'" type="info" size="small" round>{{ holdTime.toFixed(1) }} 秒</n-tag>
        </n-space>
        <n-space align="center">
          <span style="font-size: 13px; color: #64748b;">视角:</span>
          <n-space :size="4">
            <n-button
              v-for="v in (currentAction?.views || ['正面'])"
              :key="v"
              :type="currentView === v ? 'primary' : 'default'"
              size="tiny"
              @click="switchView(v)"
            >{{ v }}</n-button>
          </n-space>
        </n-space>
      </div>

      <div class="training-main">
        <div class="training-video">
          <div class="video-container">
            <video ref="videoRef" autoplay playsinline muted
              style="width: 100%; height: 100%; object-fit: contain;" />
            <canvas ref="canvasRef" style="display: none;" />
            <canvas ref="skeletonCanvasRef"
              style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain; pointer-events: none;" />

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

        <div class="training-analysis">
          <n-card v-if="currentAction" size="small" :bordered="false" class="analysis-card" style="margin-bottom: 12px;">
            <div class="info-rows">
              <div class="info-row"><span class="info-label">动作</span><span>{{ currentAction.name }}</span></div>
              <div class="info-row"><span class="info-label">家族</span><span>{{ currentAction.family_name }}</span></div>
              <div class="info-row"><span class="info-label">分类</span><span>{{ currentAction.category }}</span></div>
              <div class="info-row"><span class="info-label">难度</span>
                <n-tag size="tiny" :type="currentAction.difficulty <= 2 ? 'success' : currentAction.difficulty <= 4 ? 'warning' : 'error'">
                  {{ '⭐'.repeat(currentAction.difficulty) }}
                </n-tag>
              </div>
              <div class="info-row"><span class="info-label">强度</span><span>{{ currentAction.intensity }}</span></div>
            </div>
          </n-card>

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
                <span style="font-size: 11px;" :style="{ color: STATUS_COLORS[d.status] }">
                  {{ STATUS_LABELS[d.status] }}
                </span>
              </div>
            </template>
            <n-empty v-else description="等待分析数据" />
          </n-card>

          <n-card size="small" :bordered="false" class="analysis-card">
            <template #header>
              <n-space align="center">
                <span>实时反馈</span>
                <n-tag v-if="feedbacks.length > 0" type="error" size="tiny" round>
                  {{ feedbacks.length }}
                </n-tag>
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

      <div class="training-bottom">
        <n-space size="medium" wrap>
          <n-button type="primary" size="large" @click="handleFinishAndReport" :loading="reporting">
            <template #icon><n-icon :component="DocumentTextOutline" /></template>
            结束并查看报告
          </n-button>
          <n-button type="error" size="large" ghost @click="exitLearning">
            <template #icon><n-icon :component="StopOutline" /></template>
            退出
          </n-button>
        </n-space>
      </div>
    </div>
  </template>

  <!-- ═══════════════════════════ RESULT ═══════════════════════════ -->
  <template v-else-if="mode === 'result' && result">
    <div class="page" style="max-width: 700px; margin: 0 auto;">
      <n-card :bordered="false" class="result-card">
        <div style="text-align: center; margin-bottom: 24px;">
          <n-icon size="48" :component="TrophyOutline" color="#06b6d4" />
          <h2 style="margin: 8px 0 0; font-weight: 700;">学习完成！</h2>
          <p style="color: #64748b; font-size: 13px;">{{ currentAction?.name || '' }}</p>
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
              <span class="result-stat-label">学习帧数</span>
            </div>
          </n-grid-item>
        </n-grid>

        <n-grid :cols="2" style="margin-bottom: 24px;">
          <n-grid-item>
            <div class="result-stat">
              <span class="result-stat-num">{{ (result.duration / 60).toFixed(1) }}</span>
              <span class="result-stat-label">学习时长(分钟)</span>
            </div>
          </n-grid-item>
          <n-grid-item>
            <div class="result-stat">
              <span class="result-stat-num">
                {{ Object.values(result.feedback_counts || {}).reduce((a: number, b: number) => a + b, 0) }}
              </span>
              <span class="result-stat-label">反馈次数</span>
            </div>
          </n-grid-item>
        </n-grid>

        <n-card v-if="result.summary?.length > 0" size="small" :bordered="false" title="总结建议" style="margin-bottom: 16px;">
          <div v-for="(s, i) in result.summary" :key="i" style="margin-bottom: 4px; font-size: 13px;">
            <n-icon :component="BulbOutline" color="#06b6d4" style="margin-right: 6px;" />
            {{ s }}
          </div>
        </n-card>

        <n-divider />

        <n-space justify="center" size="medium">
          <n-button size="large" @click="mode = 'list'">
            <template #icon><n-icon :component="ArrowBackOutline" /></template>
            返回动作库
          </n-button>
          <n-button type="primary" size="large" @click="currentAction ? startLearning(currentAction) : (mode = 'list')">
            <template #icon><n-icon :component="PlayCircleOutline" /></template>
            再练一次
          </n-button>
          <n-button size="large" type="info" ghost @click="router.push(`/training/report/${result?.record_id || 'direct'}`)">
            <template #icon><n-icon :component="DocumentTextOutline" /></template>
            查看完整报告
          </n-button>
        </n-space>
      </n-card>
    </div>
  </template>

  <!-- Fallback -->
  <div v-else class="page" style="max-width: 1100px; margin: 0 auto;">
    <n-spin :show="loading" />
  </div>

  <!-- ═══════════════════════════ DETAIL MODAL ═══════════════════════════ -->
  <n-modal
    v-model:show="detailVisible"
    preset="card"
    :title="detailAction?.name || '动作详情'"
    style="max-width: 720px;"
    :mask-closable="true"
  >
    <n-spin :show="detailLoading">
      <template v-if="detailAction">
        <div class="info-rows info-rows-bordered" style="margin-bottom: 16px;">
          <div class="info-row"><span class="info-label">家族</span><span>{{ detailAction.family_name }}</span></div>
          <div class="info-row"><span class="info-label">分类</span><span>{{ detailAction.category }}</span></div>
          <div class="info-row"><span class="info-label">子分类</span><span>{{ detailAction.subcategory || '-' }}</span></div>
          <div class="info-row"><span class="info-label">难度</span><span>{{ '⭐'.repeat(detailAction.difficulty) }}</span></div>
          <div class="info-row"><span class="info-label">强度</span><span>{{ detailAction.intensity }}</span></div>
          <div class="info-row"><span class="info-label">视角</span><span>{{ (detailAction.views || []).join('、') }}</span></div>
        </div>

        <p style="font-size: 14px; color: #334155; line-height: 1.7; white-space: pre-wrap;">
          {{ detailAction.description }}
        </p>

        <n-card v-if="detailAction.steps?.length" size="small" :bordered="false" title="动作步骤" style="margin-bottom: 12px;">
          <div v-for="(step, i) in detailAction.steps" :key="i" style="font-size: 13px; margin-bottom: 6px;">
            <n-tag size="tiny" type="info" round style="margin-right: 8px;">{{ i + 1 }}</n-tag>
            {{ step }}
          </div>
        </n-card>

        <n-card v-if="detailAction.cues?.length" size="small" :bordered="false" title="动作要点" style="margin-bottom: 12px;">
          <div v-for="(cue, i) in detailAction.cues" :key="i" style="font-size: 13px; margin-bottom: 4px;">
            <n-icon :component="BulbOutline" color="#06b6d4" style="margin-right: 6px;" />
            {{ cue }}
          </div>
        </n-card>

        <n-card v-if="detailAction.phases?.length" size="small" :bordered="false" title="动作阶段" style="margin-bottom: 12px;">
          <n-space :wrap="true">
            <n-tag v-for="phase in detailAction.phases" :key="phase" size="small" type="info" round>
              {{ phase }}
            </n-tag>
          </n-space>
        </n-card>

        <n-card v-if="detailAction.target_body_parts?.length" size="small" :bordered="false" title="目标部位" style="margin-bottom: 12px;">
          <n-space :wrap="true">
            <n-tag v-for="part in detailAction.target_body_parts" :key="part" size="small" type="success" round>
              {{ part }}
            </n-tag>
          </n-space>
        </n-card>

        <n-card v-if="detailAction.common_errors?.length" size="small" :bordered="false" title="常见错误" style="margin-bottom: 12px;">
          <div v-for="(err, i) in detailAction.common_errors" :key="i" style="font-size: 13px; margin-bottom: 6px;">
            <n-icon :component="WarningOutline" :color="err.threshold > 10 ? '#f5222d' : '#fa8c16'" style="margin-right: 6px;" />
            <strong>{{ err.name }}</strong> ({{ err.joint }}): {{ err.feedback }}
          </div>
        </n-card>

        <n-card v-if="detailAction.standard_keypoints" size="small" :bordered="false" title="标准角度数据">
          <div v-for="(kps, view) in detailAction.standard_keypoints" :key="view" style="margin-bottom: 16px;">
            <n-tag type="primary" size="small" round style="margin-bottom: 8px;">{{ view }}</n-tag>
            <p style="font-size: 13px; color: #64748b; margin-bottom: 8px;">{{ kps.description }}</p>
            <div v-for="(angle, joint) in kps.target_angles" :key="joint" style="font-size: 13px; margin-bottom: 4px; padding-left: 12px;">
              <n-space :size="4" align="center">
                <span style="font-weight: 500;">{{ joint }}:</span>
                <span style="color: #06b6d4;">{{ angle.optimal }}°</span>
                <span style="color: #94a3b8;">({{ angle.min }}° – {{ angle.max }}°)</span>
              </n-space>
            </div>
          </div>
        </n-card>
      </template>
    </n-spin>

    <template #footer>
      <n-space justify="end">
        <n-button @click="detailVisible = false">关闭</n-button>
        <n-button v-if="detailAction" type="primary" @click="startLearning(detailAction)">
          <template #icon><n-icon :component="PlayCircleOutline" /></template>
          开始学习
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<style scoped>
/* ── Common ── */
.page { padding: 8px 0; }
.page-header { margin-bottom: 20px; }
.action-desc-text {
  font-size: 13px;
  color: #64748b;
  margin: 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ── Plain HTML Card Grid ── */
.action-grid-html {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
@media (max-width: 900px) {
  .action-grid-html { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .action-grid-html { grid-template-columns: 1fr; }
}
.action-card-html {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  border: 2px solid #e8ecf0;
  transition: all 0.2s ease;
  cursor: default;
  position: relative;
}
.action-card-html::before {
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 3px;
  background: linear-gradient(180deg, #5b5ee6 0%, #4f4dd9 100%);
  border-radius: 0 3px 3px 0;
  opacity: 0.3;
  transition: opacity 0.2s;
}
.action-card-html:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(91, 94, 230, 0.18), 0 2px 6px rgba(0,0,0,0.06);
  border-color: rgba(91, 94, 230, 0.45);
}
.action-card-html:hover::before {
  opacity: 1;
  width: 4px;
  box-shadow: 0 0 12px rgba(91, 94, 230, 0.3);
}

/* ── Training ── */
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
.training-video { flex: 2; min-width: 0; }
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
.score-num { font-size: 28px; font-weight: 700; }
.score-label { font-size: 12px; color: #fff; }
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
.analysis-card { border-radius: 10px !important; }
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

/* ── Info Rows (replaces NDescriptions) ── */
.info-rows { display: flex; flex-direction: column; gap: 0; }
.info-rows-bordered { border: 1px solid #e8ecf0; border-radius: 8px; overflow: hidden; }
.info-rows-bordered .info-row { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }
.info-rows-bordered .info-row:last-child { border-bottom: none; }
.info-row { display: flex; align-items: center; font-size: 13px; }
.info-label { width: 60px; flex-shrink: 0; color: #94a3b8; }

/* ── Result ── */
.result-card { border-radius: 16px !important; }
.result-stat { text-align: center; display: flex; flex-direction: column; }
.result-stat-num { font-size: 26px; font-weight: 700; color: #334155; }
.result-stat-label { font-size: 12px; color: #94a3b8; }

/* ── Demo Page ── */
.demo-page { max-width: 960px; margin: 0 auto; padding: 16px 16px 32px; }
.demo-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.demo-media-box {
  position: relative; background: #000; border-radius: 12px;
  width: 100%; height: 420px; display: flex; align-items: center;
  justify-content: center; overflow: hidden; margin-bottom: 16px;
}
.demo-badge { position: absolute; top: 12px; left: 12px; }
.demo-fallback {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 12px; color: #94a3b8;
}

@media (max-width: 768px) {
  .training-main { flex-direction: column; }
  .training-video { flex: none; height: 50%; }
  .training-analysis { overflow-y: visible; min-width: auto; }
  .demo-media-box { height: 260px; }
}
</style>
