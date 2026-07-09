<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { assessmentApi } from '../services/api'
import type { AssessmentRecord } from '../types'
import { getAssessmentItem, type AssessmentItem, type MovementStep } from '../config/assessmentSteps'
import { playStartBeep, playEndBeep, playCountdownBeep, playFinalBeep } from '../utils/audio'
import { useMessage } from 'naive-ui'
import {
  NCard, NButton, NSpace, NText, NTag, NProgress, NIcon,
  NSteps, NStep, NResult, NSpin, NUpload, NUploadDragger, NGrid, NGridItem,
  NList, NListItem, NDivider, NEmpty
} from 'naive-ui'
import {
  CameraOutline, BodyOutline, CheckmarkCircleOutline,
  ArrowForwardOutline, ReloadOutline, CloudUploadOutline,
  PlayCircleOutline, ChevronForwardOutline, AlertCircleOutline,
  TrophyOutline, ShieldCheckmarkOutline, TimeOutline, CalendarOutline,
  BarChartOutline, DocumentTextOutline
} from '@vicons/ionicons5'

const router = useRouter()
const authStore = useAuthStore()
const message = useMessage()

type Phase = 'idle' | 'connecting' | 'capturing' | 'analyzing_capture' | 'preparing' | 'countdown' | 'running' | 'between_steps' | 'movement_done' | 'done'

interface StaticFinding {
  flag: string
  name: string
  severity: string
  value: number
  unit: string
  normal_range: string
  source_views: string[]
}

const phase = ref<Phase>('idle')
const loading = ref(false)
const error = ref('')
const result = ref<any>(null)

const currentViewIdx = ref(0)
const captureViews = ['front', 'back', 'side'] as const
const captureLabels: Record<string, string> = { front: '正面', back: '背面', side: '侧面' }
const capturedPreviews = ref<Record<string, string>>({})
const captureSkeletons = ref<Record<string, number[][]>>({})
const captureView = ref('front')
const captureInstruction = ref('')
const captureError = ref('')
const previewModalView = ref<string | null>(null)
const previewCanvasRef = ref<HTMLCanvasElement | null>(null)
const staticFindings = ref<StaticFinding[]>([])
const staticSummary = ref('')
const verificationPlan = ref<any[]>([])

const movements = ref<any[]>([])
const currentMovementIdx = ref(0)
const currentStep = ref(0)
const assessmentItem = ref<AssessmentItem | null>(null)
const countdown = ref(0)
const plateau = ref(false)
const transitionHint = ref('')

const videoRef = ref<HTMLVideoElement | null>(null)
const videoRefRunning = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const canvasRefRunning = ref<HTMLCanvasElement | null>(null)
const stream = ref<MediaStream | null>(null)

const angles = ref<Record<string, number>>({})
const guidance = ref('')
const keypoints = ref<any[]>([])

// History
const records = ref<AssessmentRecord[]>([])
const recordsLoading = ref(false)

let ws: WebSocket | null = null
let frameInterval: number | null = null
let captureCanvas: HTMLCanvasElement | null = null
let countdownTimer: number | null = null
let transitionTimer: number | null = null

const captureProgress = computed(() => {
  return Math.round(((currentViewIdx.value + 1) / captureViews.length) * 100)
})

const movementProgress = computed(() => {
  if (movements.value.length === 0) return 0
  const position = movements.value.findIndex(m => (m.index ?? movements.value.indexOf(m)) === currentMovementIdx.value)
  return Math.round((((position >= 0 ? position : currentMovementIdx.value) + 1) / movements.value.length) * 100)
})

const currentStepData = computed<MovementStep | undefined>(() => assessmentItem.value?.steps[currentStep.value])
const currentStepImages = computed(() => currentStepData.value?.imageUrls || [])
const isCapturePhase = computed(() => phase.value === 'capturing' || phase.value === 'analyzing_capture')
const isMovementPhase = computed(() => ['preparing', 'countdown', 'running', 'between_steps', 'movement_done'].includes(phase.value))
const latestRecord = computed(() => records.value[0])
const nextAssessmentItem = computed(() => {
  const position = movements.value.findIndex(m => (m.index ?? movements.value.indexOf(m)) === currentMovementIdx.value)
  const next = movements.value[position + 1]
  return next ? getAssessmentItem(next.index ?? position + 1) : undefined
})

watch(stream, (newStream) => {
  if (newStream) {
    if (videoRef.value) {
      videoRef.value.srcObject = newStream
      videoRef.value.play().catch(() => {})
    }
    if (videoRefRunning.value) {
      videoRefRunning.value.srcObject = newStream
      videoRefRunning.value.play().catch(() => {})
    }
  }
}, { flush: 'post' })

watch(phase, () => {
  nextTick(() => {
    if (stream.value) {
      if (videoRef.value && !videoRef.value.srcObject) {
        videoRef.value.srcObject = stream.value
        videoRef.value.play().catch(() => {})
      }
      if (videoRefRunning.value && !videoRefRunning.value.srcObject) {
        videoRefRunning.value.srcObject = stream.value
        videoRefRunning.value.play().catch(() => {})
      }
    }
  })
})

function resetAssessment() {
  cleanupSession()
  phase.value = 'idle'
  error.value = ''
  result.value = null
  capturedPreviews.value = {}
  captureSkeletons.value = {}
  captureView.value = 'front'
  captureInstruction.value = ''
  captureError.value = ''
  currentViewIdx.value = 0
  currentMovementIdx.value = 0
  currentStep.value = 0
  assessmentItem.value = null
  staticFindings.value = []
  staticSummary.value = ''
  verificationPlan.value = []
  movements.value = []
  angles.value = {}
  plateau.value = false
  transitionHint.value = ''
  keypoints.value = []
}

async function startCamera() {
  error.value = ''
  if (!navigator.mediaDevices?.getUserMedia) {
    error.value = '当前浏览器不支持摄像头访问'
    message.error(error.value)
    return
  }
  const token = authStore.token || localStorage.getItem('token')
  if (!token) {
    error.value = '请先登录'
    return
  }
  phase.value = 'connecting'
  loading.value = true
  try {
    stream.value = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'user' }
    })
    initWebSocket(token)
  } catch (err: any) {
    error.value = `无法访问摄像头${err?.message ? `：${err.message}` : '，请检查权限设置'}`
    phase.value = 'idle'
    message.error(error.value)
  } finally {
    loading.value = false
  }
}

function initWebSocket(token: string) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/assessment/ws?token=${encodeURIComponent(token)}`
  
  ws = new WebSocket(wsUrl)
  
  ws.onopen = () => {
    console.log('WebSocket connected')
    ws?.send(JSON.stringify({ type: 'start' }))
  }
  
  ws.onmessage = (event) => {
    try {
      handleWsMessage(JSON.parse(event.data))
    } catch (err) {
      console.error('[Assessment] WebSocket message parse error', err)
    }
  }
  
  ws.onerror = () => {
    error.value = 'WebSocket 连接失败，请确认后端已启动'
    phase.value = 'idle'
  }
  
  ws.onclose = (event) => {
    if (phase.value !== 'done' && phase.value !== 'idle' && event.code !== 1000 && event.code !== 1005) {
      error.value = error.value || `WebSocket 断开（code: ${event.code}）`
      phase.value = 'idle'
    }
  }
}

function clearOverlay() {
  for (const canvas of [canvasRef.value, canvasRefRunning.value]) {
    if (!canvas) continue
    canvas.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height)
  }
}

function handleWsMessage(msg: any) {
  switch (msg.type) {
    case 'capture_ready':
      currentViewIdx.value = msg.view_index ?? Math.max(0, captureViews.indexOf(msg.view))
      captureView.value = msg.view || captureViews[currentViewIdx.value]
      captureInstruction.value = msg.instruction || ''
      captureError.value = ''
      phase.value = 'capturing'
      clearFrameInterval()
      clearOverlay()
      break
    case 'capture_ok':
      if (msg.keypoints) captureSkeletons.value = { ...captureSkeletons.value, [msg.view || captureView.value]: msg.keypoints }
      phase.value = 'capturing'
      break
    case 'capture_error':
      captureError.value = msg.message || '未检测到完整人体，请调整后重试'
      phase.value = 'capturing'
      break
    case 'static_analysis':
      staticFindings.value = msg.findings || []
      staticSummary.value = msg.summary || ''
      break
    case 'verification_plan':
      verificationPlan.value = msg.movements || []
      movements.value = msg.movements || []
      clearOverlay()
      break
    case 'assessment_started':
      movements.value = msg.movements || []
      break
    case 'movement_ready':
      phase.value = 'preparing'
      currentMovementIdx.value = msg.index ?? 0
      currentStep.value = 0
      assessmentItem.value = getAssessmentItem(currentMovementIdx.value) || null
      angles.value = {}
      plateau.value = false
      transitionHint.value = ''
      guidance.value = msg.instruction || ''
      clearOverlay()
      break
    case 'angles_update':
      if (phase.value !== 'running' && phase.value !== 'between_steps') break
      if (currentStepData.value?.highlightAngles?.length) {
        const filtered: Record<string, number> = {}
        for (const name of currentStepData.value.highlightAngles) {
          if (msg.angles?.[name] !== undefined) filtered[name] = msg.angles[name]
        }
        angles.value = Object.keys(filtered).length ? filtered : (msg.angles || {})
      } else {
        angles.value = msg.angles || {}
      }
      plateau.value = Boolean(msg.plateau_detected)
      if (msg.keypoints) drawLiveSkeleton(msg.keypoints)
      break
    case 'movement_completed':
      phase.value = 'movement_done'
      clearFrameInterval()
      break
    case 'assessment_complete':
      playFinalBeep()
      phase.value = 'done'
      result.value = msg
      cleanupSession()
      loadHistory()
      break
    case 'error':
      message.error(msg.message || '评估发生错误')
      break
  }
}

function capturePhoto() {
  const video = videoRef.value
  if (!video?.videoWidth) {
    message.error('摄像头尚未就绪')
    return
  }
  captureCanvas = captureCanvas || document.createElement('canvas')
  captureCanvas.width = video.videoWidth
  captureCanvas.height = video.videoHeight
  captureCanvas.getContext('2d')?.drawImage(video, 0, 0)
  const dataUrl = captureCanvas.toDataURL('image/jpeg', 0.85)
  capturedPreviews.value = { ...capturedPreviews.value, [captureView.value]: dataUrl }
  captureError.value = ''
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'capture_view', view: captureView.value, data: dataUrl }))
    phase.value = 'analyzing_capture'
  } else {
    message.error('评估连接尚未建立')
  }
}

function handleFileUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) {
    message.error('请选择图片文件')
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    const dataUrl = String(reader.result)
    capturedPreviews.value = { ...capturedPreviews.value, [captureView.value]: dataUrl }
    captureError.value = ''
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'capture_view', view: captureView.value, data: dataUrl }))
      phase.value = 'analyzing_capture'
    }
  }
  reader.readAsDataURL(file)
}

function skipCapture() {
  phase.value = 'connecting'
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'skip_capture' }))
  } else {
    error.value = '评估连接尚未建立'
    phase.value = 'idle'
  }
}

function retryCaptureView() {
  captureError.value = ''
  phase.value = 'capturing'
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'retry_view', view: captureView.value }))
  }
}

function startRunning() {
  if (countdownTimer) window.clearInterval(countdownTimer)
  transitionHint.value = ''
  countdown.value = 3
  phase.value = 'countdown'
  playCountdownBeep()
  countdownTimer = window.setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      if (countdownTimer) window.clearInterval(countdownTimer)
      countdownTimer = null
      playStartBeep()
      phase.value = 'running'
      guidance.value = currentStepData.value?.instruction || guidance.value || '保持姿势，正在评估中...'
      window.setTimeout(startFrameSending, 100)
    } else {
      playCountdownBeep()
    }
  }, 1000)
}

function clearFrameInterval() {
  if (frameInterval) {
    window.clearInterval(frameInterval)
    frameInterval = null
  }
}

function startFrameSending() {
  clearFrameInterval()
  captureCanvas = captureCanvas || document.createElement('canvas')
  
  frameInterval = window.setInterval(() => {
    if (ws?.readyState !== WebSocket.OPEN || !videoRefRunning.value || phase.value !== 'running') {
      return
    }
    
    const video = videoRefRunning.value
    captureCanvas!.width = video.videoWidth || 640
    captureCanvas!.height = video.videoHeight || 480
    const ctx = captureCanvas!.getContext('2d')
    if (ctx) {
      ctx.drawImage(video, 0, 0)
      const dataUrl = captureCanvas!.toDataURL('image/jpeg', 0.6)
      ws!.send(JSON.stringify({ type: 'frame', data: dataUrl }))
    }
  }, 150)
}

function completeCurrentStep() {
  const item = assessmentItem.value
  if (!item) return
  if (currentStep.value < item.steps.length - 1) {
    playEndBeep()
    transitionHint.value = item.steps[currentStep.value].transitionHint
    clearFrameInterval()
    currentStep.value++
    angles.value = {}
    plateau.value = false
    guidance.value = currentStepData.value?.instruction || ''
    phase.value = 'preparing'
  } else {
    playEndBeep()
    clearFrameInterval()
    phase.value = 'movement_done'
    ws?.readyState === WebSocket.OPEN && ws.send(JSON.stringify({ type: 'movement_done' }))
  }
}

function skipMovement() {
  clearFrameInterval()
  angles.value = {}
  transitionHint.value = ''
  phase.value = 'movement_done'
  ws?.readyState === WebSocket.OPEN && ws.send(JSON.stringify({ type: 'movement_done' }))
}

function finishAssessment() {
  clearFrameInterval()
  ws?.readyState === WebSocket.OPEN && ws.send(JSON.stringify({ type: 'finish' }))
}

const skeletonConnections: [number, number][] = [
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16]
]

function drawFlatSkeleton(keypoints: number[][], canvas: HTMLCanvasElement, scaleX = 1, scaleY = 1) {
  const ctx = canvas.getContext('2d')
  if (!ctx || !keypoints.length) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.strokeStyle = '#00ff88'
  ctx.lineWidth = 2
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  for (const [i, j] of skeletonConnections) {
    if (i < keypoints.length && j < keypoints.length) {
      const [x1, y1] = keypoints[i]
      const [x2, y2] = keypoints[j]
      if (x1 <= 0 || y1 <= 0 || x2 <= 0 || y2 <= 0) continue
      ctx.beginPath()
      ctx.moveTo(x1 * scaleX, y1 * scaleY)
      ctx.lineTo(x2 * scaleX, y2 * scaleY)
      ctx.stroke()
    }
  }
  ctx.fillStyle = '#ff4466'
  for (const [x, y] of keypoints) {
    if (x <= 0 || y <= 0) continue
    ctx.beginPath()
    ctx.arc(x * scaleX, y * scaleY, 4, 0, Math.PI * 2)
    ctx.fill()
  }
}

function drawLiveSkeleton(keypointsList: any[]) {
  const canvas = canvasRefRunning.value
  const video = videoRefRunning.value
  if (!canvas || !video || !keypointsList?.length) return
  const width = canvas.clientWidth || video.videoWidth || 640
  const height = canvas.clientHeight || video.videoHeight || 480
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, width, height)
  const scaleX = width / (video.videoWidth || 640)
  const scaleY = height / (video.videoHeight || 480)
  for (const person of keypointsList) {
    const points = person.keypoints || person
    const confidences = person.confidences || Array(points.length).fill(1)
    if (!Array.isArray(points) || points.length < 17) continue
    ctx.strokeStyle = '#00ff88'
    ctx.lineWidth = 2
    for (const [i, j] of skeletonConnections) {
      if (confidences[i] <= 0.3 || confidences[j] <= 0.3) continue
      const [x1, y1] = points[i]
      const [x2, y2] = points[j]
      if (x1 <= 0 || y1 <= 0 || x2 <= 0 || y2 <= 0) continue
      ctx.beginPath()
      ctx.moveTo(x1 * scaleX, y1 * scaleY)
      ctx.lineTo(x2 * scaleX, y2 * scaleY)
      ctx.stroke()
    }
    ctx.fillStyle = '#ff4466'
    points.forEach(([x, y]: number[], index: number) => {
      if (confidences[index] <= 0.3 || x <= 0 || y <= 0) return
      ctx.beginPath()
      ctx.arc(x * scaleX, y * scaleY, 4, 0, Math.PI * 2)
      ctx.fill()
    })
  }
}

watch(previewModalView, async view => {
  if (!view) return
  await nextTick()
  const photo = capturedPreviews.value[view]
  const points = captureSkeletons.value[view]
  const canvas = previewCanvasRef.value
  if (!photo || !canvas) return
  const image = new Image()
  image.onload = () => {
    canvas.width = image.naturalWidth
    canvas.height = image.naturalHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(image, 0, 0)
    if (points?.length) {
      const scale = image.naturalWidth > 640 ? image.naturalWidth / 640 : 1
      drawFlatSkeleton(points, canvas, scale, scale)
      ctx.globalCompositeOperation = 'destination-over'
      ctx.drawImage(image, 0, 0)
      ctx.globalCompositeOperation = 'source-over'
    }
  }
  image.src = photo
})

function cleanupSession(closeSocket = true) {
  clearFrameInterval()
  if (countdownTimer) {
    window.clearInterval(countdownTimer)
    countdownTimer = null
  }
  if (transitionTimer) {
    window.clearTimeout(transitionTimer)
    transitionTimer = null
  }
  if (closeSocket && ws) {
    ws.onclose = null
    ws.close()
    ws = null
  }
  stream.value?.getTracks().forEach(track => track.stop())
  stream.value = null
}

function viewReport() {
  router.push(`/assessment/report/${result.value?.record_id || 1}`)
}

function retry() {
  resetAssessment()
}

function loadHistory() {
  recordsLoading.value = true
  assessmentApi.getRecords()
    .then(r => { records.value = r || [] })
    .catch(() => {})
    .finally(() => { recordsLoading.value = false })
}

function getRiskLabel(level: string) {
  const map: Record<string, string> = { low: '低风险', medium: '中风险', high: '高风险' }
  return map[level] || level
}

function getRiskType(level: string) {
  const map: Record<string, any> = { low: 'success', medium: 'warning', high: 'error' }
  return map[level] || 'default'
}

function goToReport(recordId: number) {
  router.push(`/assessment/report/${recordId}`)
}

function goToCompare(recordId: number) {
  router.push(`/assessment/compare/${recordId}`)
}

async function deleteRecord(recordId: number) {
  if (!window.confirm('删除后不可恢复，确定要删除此评估记录吗？')) return
  try {
    await assessmentApi.deleteRecord(recordId)
    message.success('评估记录已删除')
    await loadHistory()
  } catch (err: any) {
    message.error(err?.response?.data?.detail || '删除失败')
  }
}

function getScoreMeta(score: number, riskLevel: string) {
  if (riskLevel === 'low' || score >= 85) return { label: '良好', tone: 'good' }
  if (riskLevel === 'high' || score < 70) return { label: '需改善', tone: 'danger' }
  return { label: '一般', tone: 'warning' }
}

function getRecordProblem(record: AssessmentRecord) {
  const first = record.posture_problems?.[0]
  if (typeof first === 'string') return { title: first, desc: '建议结合评估报告进行针对性训练' }
  if (first && typeof first === 'object') {
    return {
      title: first.name || first.label || first.problem || first.title || '检测到体态偏差',
      desc: first.suggestion || first.description || first.advice || '建议结合评估报告进行针对性训练'
    }
  }
  if (record.risk_level === 'low') return { title: '整体体态表现良好', desc: '继续保持规律训练与日常活动' }
  return { title: '全身体态评估中', desc: '查看报告了解详细体态问题' }
}

function formatRecordDate(date: string) {
  const value = new Date(date)
  return {
    date: value.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).replaceAll('/', '/'),
    time: value.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
  }
}

onMounted(() => {
  resetAssessment()
  loadHistory()
})

onUnmounted(() => {
  cleanupSession()
})
</script>

<script lang="ts">
export default { name: 'AssessmentView' }
</script>

<template>
  <div class="assessment-page">
    <n-card :bordered="false" class="main-card" :class="{ 'idle-main-card': phase === 'idle' }" size="large">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <n-icon size="22" :component="BodyOutline" class="header-icon" />
            <span class="header-title">体态评估</span>
          </div>
          <n-tag v-if="phase !== 'idle' && phase !== 'done'" type="info" round>
            {{ movementProgress }}%
          </n-tag>
        </div>
      </template>

      <div v-if="phase === 'idle'" class="idle-section">
        <div v-if="error" class="error-message">
          <n-icon size="20" :component="AlertCircleOutline" />
          <span>{{ error }}</span>
        </div>

        <div class="assessment-intro">
          <div class="intro-content">
            <div class="intro-heading">
              <div class="intro-logo">
                <img src="/media/pictures/assessment.png" alt="体态评估" />
              </div>
              <div>
                <h2>开始体态评估</h2>
                <p>通过拍摄三张照片进行静态分析</p>
                <p>多角度评估，全身分析，科学准确</p>
              </div>
            </div>

            <div class="intro-features">
              <div class="intro-feature">
                <n-icon :component="BodyOutline" />
                <div><strong>3个角度</strong><span>正面/背面/侧面</span></div>
              </div>
              <div class="intro-feature">
                <n-icon :component="ShieldCheckmarkOutline" />
                <div><strong>隐私保障</strong><span>数据仅用于评估</span></div>
              </div>
              <div class="intro-feature">
                <n-icon :component="TimeOutline" />
                <div><strong>约2-3分钟</strong><span>快速完成评估</span></div>
              </div>
            </div>

            <n-button type="primary" size="large" class="start-btn" @click="startCamera">
              <template #icon><n-icon :component="CameraOutline" /></template>
              开启摄像头，开始评估
            </n-button>
          </div>

          <div class="capture-orbit" aria-hidden="true">
            <div class="orbit orbit-one"></div>
            <div class="orbit orbit-two"></div>
            <div class="orbit orbit-three"></div>
            <div class="orbit-center"><n-icon :component="CameraOutline" /></div>
            <div class="orbit-point orbit-front"><img src="/icons/assessment/front.png" alt="正面" /><span>正面</span></div>
            <div class="orbit-point orbit-side"><img src="/icons/assessment/side.png" alt="侧面" /><span>侧面</span></div>
            <div class="orbit-point orbit-back"><img src="/icons/assessment/back.png" alt="背面" /><span>背面</span></div>
          </div>
        </div>

        <div class="mobile-intro-features">
          <n-grid :cols="3" :x-gap="8">
            <n-grid-item>
            <div class="info-card">
              <n-icon :component="BodyOutline" /><strong>3个角度</strong><span>正/背/侧面</span>
            </div>
            </n-grid-item>
            <n-grid-item>
            <div class="info-card">
              <n-icon :component="ShieldCheckmarkOutline" /><strong>隐私保障</strong><span>仅用于评估</span>
            </div>
            </n-grid-item>
            <n-grid-item>
            <div class="info-card">
              <n-icon :component="TimeOutline" /><strong>约2-3分钟</strong><span>快速完成</span>
            </div>
            </n-grid-item>
          </n-grid>
        </div>
      </div>

      <div v-else-if="phase === 'connecting'" class="loading-section">
        <n-spin size="large" />
        <p class="loading-text">正在连接...</p>
      </div>

      <div v-else-if="isCapturePhase" class="capture-section">
        <div class="video-container">
          <video v-if="stream" ref="videoRef" class="camera-video" autoplay playsinline muted />
          <canvas v-if="stream" ref="canvasRef" class="skeleton-canvas" />
          <div v-else class="video-placeholder">
            <n-icon size="48" :component="CameraOutline" class="video-icon" />
            <p class="video-hint">摄像头预览区域</p>
          </div>
          <div v-if="phase === 'analyzing_capture'" class="capture-analyzing-overlay">
            <n-spin size="large" />
            <span>正在识别人体姿态...</span>
          </div>
        </div>

        <n-progress :percentage="captureProgress" :show-indicator="false" class="progress-bar" />

        <div class="view-tags">
          <n-tag
            v-for="(view, idx) in captureViews"
            :key="view"
            :type="capturedPreviews[view] ? 'success' : (idx === currentViewIdx ? 'info' : 'default')"
            round
            :class="{ 'clickable-tag': capturedPreviews[view] }"
            @click="capturedPreviews[view] && (previewModalView = view)"
          >
            {{ idx + 1 }}. {{ captureLabels[view] }}{{ capturedPreviews[view] ? ' ✓' : '' }}
          </n-tag>
        </div>

        <n-card :bordered="false" size="small" class="capture-hint-card">
          <div class="capture-hint-content">
            <n-icon size="20" :component="BodyOutline" />
            <span class="hint-text">{{ captureLabels[captureView] || captureLabels[captureViews[currentViewIdx]] }}照</span>
          </div>
          <p class="hint-desc">{{ captureInstruction || '请保持自然站立，全身入镜' }}</p>
        </n-card>

        <div v-if="captureError" class="capture-error-box">
          <n-icon :component="AlertCircleOutline" />
          <span>{{ captureError }}</span>
          <n-button size="small" @click="retryCaptureView">重新拍摄</n-button>
        </div>

        <div class="capture-actions">
          <n-button type="primary" size="large" :disabled="phase === 'analyzing_capture'" @click="capturePhoto">
            <template #icon><n-icon :component="CameraOutline" /></template>
            拍摄照片
          </n-button>
          <label class="upload-photo-btn" :class="{ disabled: phase === 'analyzing_capture' }">
            <input type="file" accept="image/*" :disabled="phase === 'analyzing_capture'" @change="handleFileUpload">
            <n-icon :component="CloudUploadOutline" />上传照片
          </label>
          <n-button size="large" @click="skipCapture">
            跳过拍照，进入实时评估
          </n-button>
        </div>
      </div>

      <div v-else-if="isMovementPhase" class="running-section">
        <n-card v-if="staticSummary || staticFindings.length" size="small" :bordered="false" class="static-summary-card">
          <strong>静态体态分析</strong>
          <p v-if="staticSummary">{{ staticSummary }}</p>
          <n-space v-if="staticFindings.length" wrap>
            <n-tag
              v-for="finding in staticFindings"
              :key="finding.flag"
              :type="finding.severity === 'severe' ? 'error' : finding.severity === 'moderate' ? 'warning' : 'info'"
            >
              {{ finding.name }}：{{ finding.severity === 'severe' ? '严重' : finding.severity === 'moderate' ? '中度' : '轻度' }}
            </n-tag>
          </n-space>
          <small v-if="verificationPlan.length">将进行 {{ verificationPlan.length }} 项定向验证</small>
        </n-card>
        <n-progress :percentage="movementProgress" :show-indicator="false" class="progress-bar" />

        <div class="movement-tags">
          <n-tag
            v-for="(m, idx) in movements"
            :key="idx"
            :type="idx < currentMovementIdx ? 'success' : (idx === currentMovementIdx ? 'info' : 'default')"
            round
          >
            {{ idx + 1 }}. {{ m.name }}
          </n-tag>
        </div>

        <n-steps v-if="assessmentItem && assessmentItem.steps.length > 1" size="small" :current="currentStep + 1" class="step-progress">
          <n-step v-for="step in assessmentItem.steps" :key="step.id" :title="step.name" />
        </n-steps>

        <div v-if="phase !== 'movement_done'" class="assessment-workspace">
          <section class="camera-panel">
            <div class="workspace-panel-title">
              <span>实时摄像头</span>
              <n-tag :type="phase === 'running' ? 'success' : 'info'" size="small" round>
                {{ phase === 'running' ? '检测中' : phase === 'countdown' ? '即将开始' : '准备中' }}
              </n-tag>
            </div>
            <div class="video-container">
              <video v-if="stream" ref="videoRefRunning" class="camera-video" autoplay playsinline muted />
              <canvas v-if="stream" ref="canvasRefRunning" class="skeleton-canvas" />
              <div v-else class="video-placeholder large">
                <n-icon size="64" :component="PlayCircleOutline" class="video-icon" />
                <p class="video-hint">{{ movements[currentMovementIdx]?.name }} - 摄像头画面</p>
              </div>
              <p v-if="guidance && phase === 'running'" class="guidance-text">{{ guidance }}</p>
              <div v-if="phase === 'countdown'" class="countdown-overlay">
                <strong>{{ countdown }}</strong>
                <span>秒后开始</span>
              </div>
            </div>
          </section>

          <aside class="movement-demo-card">
            <div class="workspace-panel-title demo-panel-title">
              <span>示范动作</span>
              <n-tag size="small" round>{{ currentStep + 1 }}/{{ assessmentItem?.steps.length || 1 }}</n-tag>
            </div>
            <div class="demo-title">{{ assessmentItem?.name || movements[currentMovementIdx]?.name }}</div>
            <div v-if="currentStepData" class="demo-step">{{ currentStepData.name }}</div>
            <div
              class="demo-media-grid"
              :class="{ 'single-media': currentStepImages.length === 1 && !currentStepData?.videoUrl }"
            >
              <div v-for="(imageUrl, imageIndex) in currentStepImages" :key="imageUrl" class="demo-placeholder demo-image">
                <img :src="imageUrl" :alt="`${currentStepData?.name || '评估动作'}示例图${imageIndex + 1}`">
              </div>
              <div v-if="currentStepData?.videoUrl" class="demo-placeholder">
                <video :src="currentStepData.videoUrl" controls muted playsinline />
              </div>
              <div v-if="currentStepImages.length === 0 && !currentStepData?.videoUrl" class="demo-placeholder">
                <n-icon size="42" :component="CameraOutline" />
                <span>示范媒体待补充</span>
              </div>
            </div>
            <div class="demo-instruction">💡 {{ currentStepData?.instruction || guidance }}</div>
            <div v-if="assessmentItem?.durationHint" class="demo-duration">预计耗时：{{ assessmentItem.durationHint }}</div>
          </aside>
        </div>

        <div v-if="phase === 'running' && Object.keys(angles).length > 0" class="angles-display">
          <n-grid :cols="3" :x-gap="12" :y-gap="12">
            <n-grid-item v-for="(value, key) in angles" :key="key">
              <div class="angle-card" :class="{ reached: plateau }">
                <div class="angle-value">{{ Math.round(value) }}°</div>
                <div class="angle-name">{{ key }}</div>
              </div>
            </n-grid-item>
          </n-grid>
          <n-tag v-if="plateau" type="success" round class="plateau-tag">已达到目标</n-tag>
        </div>

        <div v-if="transitionHint" class="transition-hint">⏭ {{ transitionHint }}</div>

        <div v-if="phase === 'movement_done'" class="movement-done-box">
          <n-icon :component="CheckmarkCircleOutline" />
          <strong>本项评估完成</strong>
          <span v-if="nextAssessmentItem">下一项：{{ nextAssessmentItem.name }}（{{ nextAssessmentItem.steps.length }} 个步骤）</span>
          <span v-else>正在生成最终评估结果...</span>
        </div>

        <div class="action-buttons">
          <n-button v-if="phase === 'preparing'" type="primary" size="large" @click="startRunning">
            <template #icon><n-icon :component="PlayCircleOutline" /></template>
            准备好了，开始检测
          </n-button>
          <template v-if="phase === 'running'">
            <n-button type="primary" size="large" @click="completeCurrentStep">
              <template #icon><n-icon :component="CheckmarkCircleOutline" /></template>
              {{ currentStep < (assessmentItem?.steps.length || 1) - 1 ? '完成此步骤，继续下一步' : '完成此评估项' }}
            </n-button>
            <n-button size="large" @click="skipMovement">
              <template #icon><n-icon :component="ArrowForwardOutline" /></template>
              跳过此项
            </n-button>
            <n-button size="large" type="error" ghost @click="finishAssessment">结束评估</n-button>
          </template>
          <n-button v-if="phase === 'movement_done'" size="large" disabled>
            <template #icon><n-icon :component="ArrowForwardOutline" /></template>
            等待下一项...
          </n-button>
        </div>
      </div>

      <div v-else-if="phase === 'done'" class="result-section">
        <n-result
          status="success"
          title="评估完成"
          :description="`综合评分 ${result?.overall_score?.toFixed(1)} / 100`"
        >
          <template #footer>
            <n-space justify="center">
              <n-button type="primary" @click="viewReport">查看详细报告</n-button>
              <n-button @click="retry">重新评估</n-button>
            </n-space>
          </template>
        </n-result>
      </div>
    </n-card>

    <!-- History Records -->
    <n-card v-if="phase === 'idle'" :bordered="false" class="history-card" size="large">
      <template #header>
        <div class="history-header">
          <div class="history-heading"><n-icon :component="CameraOutline" /><span class="history-title">历史评估记录</span></div>
        </div>
      </template>
      <n-spin :show="recordsLoading">
        <div v-if="latestRecord" class="history-summary">
          <div><small>总次数</small><strong>{{ records.length }}<em>次</em></strong></div>
          <div><small>最新得分</small><strong>{{ latestRecord.overall_score?.toFixed(0) }}<em>分</em></strong></div>
          <div><small>风险等级</small><strong>{{ getRiskLabel(latestRecord.risk_level) }}</strong></div>
          <div><small>最近日期</small><strong>{{ formatRecordDate(latestRecord.test_date).date }}</strong></div>
        </div>
        <div v-if="records.length === 0" class="history-empty">
          <div class="empty-illustration">
            <div class="empty-circle">
              <n-icon size="40" :component="BodyOutline" />
            </div>
          </div>
          <p class="empty-title">暂无评估记录</p>
          <p class="empty-desc">完成首次 AI 体态评估后，你的评估数据将在这里展示</p>
        </div>
        <div v-else class="history-table">
          <div class="history-table-header">
            <span class="ht-col ht-col-date">评估时间</span>
            <span class="ht-col ht-col-score">评分结果</span>
            <span class="ht-col ht-col-problem">问题分析</span>
            <span class="ht-col ht-col-action">操作</span>
          </div>
          <div
            v-for="record in records.slice(0, 5)"
            :key="record.id"
            class="history-row"
            @click="goToReport(record.id)"
          >
            <span class="ht-col ht-col-date">
              <span class="date-icon"><n-icon :component="CalendarOutline" /></span>
              <span class="date-copy"><strong>{{ formatRecordDate(record.test_date).date }}</strong><small>{{ formatRecordDate(record.test_date).time }}</small></span>
            </span>
            <span class="ht-col ht-col-score">
              <span class="score-ring" :class="getScoreMeta(record.overall_score, record.risk_level).tone">{{ record.overall_score?.toFixed(0) }}<small>分</small></span>
              <span class="score-copy"><strong :class="getScoreMeta(record.overall_score, record.risk_level).tone">{{ getScoreMeta(record.overall_score, record.risk_level).label }}</strong><small>{{ getRiskLabel(record.risk_level) }}</small></span>
            </span>
            <span class="ht-col ht-col-problem">
              <span class="problem-icon" :class="getScoreMeta(record.overall_score, record.risk_level).tone"><n-icon :component="BodyOutline" /></span>
              <span class="problem-copy"><strong>{{ getRecordProblem(record).title }}</strong><small>{{ getRecordProblem(record).desc }}</small></span>
            </span>
            <span class="ht-col ht-col-action">
              <n-button size="small" class="report-btn" @click.stop="goToReport(record.id)">
                <template #icon><n-icon :component="DocumentTextOutline" /></template>查看报告
              </n-button>
              <n-button size="small" type="primary" class="compare-btn" @click.stop="goToCompare(record.id)">
                <template #icon><n-icon :component="BarChartOutline" /></template>对比分析
              </n-button>
              <n-button size="small" type="error" ghost @click.stop="deleteRecord(record.id)">删除</n-button>
            </span>
          </div>
        </div>
      </n-spin>
    </n-card>

    <div v-if="previewModalView" class="preview-modal" @click="previewModalView = null">
      <div class="preview-dialog" @click.stop>
        <div class="preview-header">
          <strong>{{ captureLabels[previewModalView] }}照 · 骨架分析</strong>
          <n-button size="small" @click="previewModalView = null">关闭</n-button>
        </div>
        <canvas ref="previewCanvasRef" class="preview-canvas" />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── Page Layout ── */
.assessment-page {
  width: 100%;
  max-width: none;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.main-card {
  border-radius: 16px !important;
  overflow: hidden;
}

.main-card :deep(.n-card__content),
.main-card :deep(.n-card__body),
.main-card :deep(.n-card__content-wrapper),
.main-card :deep(.n-card__header-wrapper) {
  background: transparent !important;
  padding: 0 !important;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon {
  color: #3b82f6;
}

.header-title {
  font-size: 18px;
  font-weight: 700;
}

/* ── Idle: Hero Area ── */
.idle-section {
  position: relative;
  padding: 0;
  overflow: hidden;
  background: transparent;
}

.assessment-intro {
  position: relative;
  display: flex;
  gap: 32px;
  align-items: center;
  width: 100%;
  min-height: 420px;
  padding: 36px;
  border-radius: 28px;
  background: linear-gradient(135deg, #5b21b6 0%, #6d28d9 42%, #8b5cf6 100%);
  color: #f8f7ff;
  overflow: hidden;
}

.assessment-intro::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top right, rgba(255,255,255,0.18), transparent 28%), radial-gradient(circle at bottom left, rgba(255,255,255,0.08), transparent 20%);
  pointer-events: none;
  z-index: 0;
}

.assessment-intro::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(255,255,255,0.08), transparent 45%), linear-gradient(90deg, rgba(255,255,255,0.06), transparent 60%);
  pointer-events: none;
  z-index: 1;
}

.intro-content,
.capture-orbit {
  position: relative;
  z-index: 2;
}

.intro-content {
  flex: 1.05;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 24px;
  min-width: 320px;
}

.intro-heading {
  display: flex;
  align-items: flex-start;
  gap: 18px;
}

.intro-logo {
  width: 64px;
  height: 64px;
  border-radius: 20px;
  background: rgba(255,255,255,0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: white;
  box-shadow: 0 18px 38px rgba(0,0,0,0.18);
}

.intro-logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: 35% center;
  transform: scale(1.38);
  transform-origin: 35% center;
}

.intro-heading h2 {
  margin: 0;
  font-size: 38px;
  line-height: 1.05;
  letter-spacing: -0.04em;
}

.intro-heading p {
  margin: 8px 0 0;
  color: rgba(255,255,255,0.82);
  font-size: 15px;
  line-height: 1.7;
}

.intro-features {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.intro-feature {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px;
  border-radius: 22px;
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.14);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02);
}

.intro-feature n-icon,
.intro-feature svg {
  min-width: 44px;
  min-height: 44px;
  width: 44px;
  height: 44px;
  border-radius: 16px;
  background: rgba(255,255,255,0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.intro-feature strong {
  font-size: 15px;
  line-height: 1.3;
}

.intro-feature span {
  display: block;
  margin-top: 4px;
  color: rgba(255,255,255,0.8);
  font-size: 13px;
}

.capture-orbit {
  flex: 1;
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.orbit {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.24);
}

.orbit-one {
  width: 340px;
  height: 340px;
  top: 18px;
  right: 20px;
}

.orbit-two {
  width: 220px;
  height: 220px;
  bottom: 18px;
  left: 24px;
  border-color: rgba(255,255,255,0.16);
}

.orbit-three {
  width: 132px;
  height: 132px;
  top: 120px;
  left: 72px;
  border-color: rgba(255,255,255,0.14);
}

.orbit-center {
  position: absolute;
  width: 104px;
  height: 104px;
  border-radius: 50%;
  background: rgba(255,255,255,0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  box-shadow: 0 18px 42px rgba(0,0,0,0.18);
  color: white;
}

.orbit-point {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  text-align: center;
  color: white;
  font-size: 14px;
  font-weight: 700;
}

.orbit-point img {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  padding: 10px;
  background: rgba(255,255,255,0.12);
}

.orbit-point span {
  margin-top: 0;
  color: #f8f7ff;
}

.orbit-front {
  top: 20%;
  left: 18%;
}

.orbit-side {
  top: 40%;
  right: 18%;
  transform: translateY(-4%);
}

.orbit-back {
  bottom: 18%;
  left: 32%;
}

.mobile-intro-features {
  margin-top: 24px;
}

@media (max-width: 1200px) {
  .assessment-intro {
    flex-direction: column;
    min-height: auto;
    padding: 28px;
  }
  .intro-content,
  .capture-orbit {
    width: 100%;
  }
  .intro-features {
    grid-template-columns: 1fr;
  }
  .capture-orbit {
    min-height: 360px;
  }
  .orbit-front,
  .orbit-side,
  .orbit-back {
    position: relative;
    top: auto;
    left: auto;
    right: auto;
    bottom: auto;
    transform: none;
  }
}

@media (max-width: 768px) {
  .assessment-page {
    gap: 16px;
  }
  .assessment-intro {
    padding: 22px;
  }
  .intro-heading h2 {
    font-size: 30px;
  }
  .intro-features {
    gap: 12px;
  }
}

.idle-bg-decor {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.decor-circle {
  position: absolute;
  border-radius: 50%;
}

.decor-1 {
  width: 300px;
  height: 300px;
  top: -120px;
  right: -80px;
  background: radial-gradient(circle, rgba(102,126,234,0.08) 0%, transparent 70%);
}

.decor-2 {
  width: 200px;
  height: 200px;
  bottom: 40px;
  left: -60px;
  background: radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 70%);
}

.decor-3 {
  width: 120px;
  height: 120px;
  top: 60px;
  left: 30%;
  background: radial-gradient(circle, rgba(16,185,129,0.05) 0%, transparent 70%);
}

.error-message {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(239,68,68,0.08);
  border: 1px solid rgba(239,68,68,0.15);
  border-radius: 10px;
  color: #ef4444;
  margin: 0 20px 16px;
  font-size: 14px;
  position: relative;
  z-index: 1;
}

.idle-hero {
  text-align: center;
  padding: 20px 20px 0;
  position: relative;
  z-index: 1;
}

.idle-icon-wrap {
  position: relative;
  width: 110px;
  height: 110px;
  margin: 0 auto 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.idle-icon-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid rgba(102,126,234,0.15);
  animation: icon-pulse 3s ease-in-out infinite;
}

@keyframes icon-pulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.08); opacity: 1; }
}

.idle-icon-inner {
  width: 88px;
  height: 88px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 8px 32px -4px rgba(102,126,234,0.35);
}

.idle-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 10px;
  color: #1e293b;
  letter-spacing: -0.3px;
}

.idle-subtitle {
  font-size: 14px;
  color: #64748b;
  margin: 0;
  line-height: 1.7;
  max-width: 420px;
  margin: 0 auto;
}

/* ── Info Cards ── */
.info-grid {
  padding: 24px 20px 0;
  position: relative;
  z-index: 1;
}

.info-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid rgba(0,0,0,0.04);
  transition: all 0.2s;
}

.info-card:hover {
  background: #f1f5f9;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px -4px rgba(0,0,0,0.06);
}

.info-card-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.info-card-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-card-title {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.info-card-desc {
  font-size: 12px;
  color: #64748b;
}

/* ── CTA Button ── */
.idle-cta {
  text-align: center;
  padding: 28px 20px 16px;
  position: relative;
  z-index: 1;
}

.start-btn {
  height: 50px !important;
  padding: 0 36px !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  border-radius: 12px !important;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  border: none !important;
  box-shadow: 0 6px 24px -4px rgba(102,126,234,0.4);
  transition: all 0.3s ease;
}

.start-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 32px -4px rgba(102,126,234,0.55);
}

.start-btn:active {
  transform: translateY(0);
}

.idle-safe-note {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 12px;
  color: #94a3b8;
  margin: 12px 0 0;
}

/* ── History Section ── */
.history-card {
  border-radius: 16px !important;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.history-title {
  font-size: 16px;
  font-weight: 600;
}

.history-count {
  font-size: 12px;
  color: #94a3b8;
}

/* History Empty */
.history-empty {
  text-align: center;
  padding: 32px 16px 24px;
}

.empty-illustration {
  margin-bottom: 16px;
}

.empty-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(102,126,234,0.08) 0%, rgba(139,92,246,0.08) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  margin: 0 auto;
}

.empty-title {
  font-size: 15px;
  font-weight: 600;
  color: #64748b;
  margin: 0 0 6px;
}

.empty-desc {
  font-size: 13px;
  color: #94a3b8;
  margin: 0;
}

/* History Table */
.history-table {
  overflow-x: auto;
}

.history-table-header {
  display: flex;
  align-items: center;
  padding: 8px 12px 10px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.history-row {
  display: flex;
  align-items: center;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 1px solid rgba(0,0,0,0.03);
}

.history-row:last-child {
  border-bottom: none;
}

.history-row:hover {
  background: rgba(102,126,234,0.03);
  transform: translateX(4px);
}

.ht-col {
  display: flex;
  align-items: center;
}

.ht-col-date {
  width: 70px;
  flex-shrink: 0;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
}

.ht-date-day {
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
  color: #1e293b;
}

.ht-date-month {
  font-size: 12px;
  color: #94a3b8;
}

.ht-col-dims {
  flex: 1;
  flex-wrap: wrap;
  gap: 4px;
  padding: 0 12px;
  min-width: 0;
}

.ht-col-risk {
  width: 90px;
  flex-shrink: 0;
  gap: 6px;
  justify-content: center;
}

.ht-col-score {
  width: 80px;
  flex-shrink: 0;
  justify-content: center;
  gap: 2px;
}

.ht-col-action {
  width: 60px;
  flex-shrink: 0;
  justify-content: flex-end;
}

.dim-chip {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #64748b;
  white-space: nowrap;
}

.dim-more {
  background: #e2e8f0;
  color: #94a3b8;
  font-weight: 600;
}

.risk-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.risk-low { background: #10b981; }
.risk-medium { background: #f59e0b; }
.risk-high { background: #ef4444; }

.score-value {
  font-size: 22px;
  font-weight: 800;
  line-height: 1;
}

.score-low { color: #10b981; }
.score-medium { color: #f59e0b; }
.score-high { color: #ef4444; }

.score-unit {
  font-size: 12px;
  color: #94a3b8;
}

/* ── Dark Mode ── */
:deep(.dark) .idle-title { color: #e2e8f0; }
:deep(.dark) .idle-subtitle { color: #94a3b8; }
:deep(.dark) .info-card { background: rgba(255,255,255,0.03); border-color: rgba(255,255,255,0.06); }
:deep(.dark) .info-card:hover { background: rgba(255,255,255,0.06); }
:deep(.dark) .info-card-title { color: #e2e8f0; }
:deep(.dark) .info-card-desc { color: #94a3b8; }
:deep(.dark) .ht-date-day { color: #e2e8f0; }
:deep(.dark) .dim-chip { background: rgba(255,255,255,0.06); color: #94a3b8; }
:deep(.dark) .dim-more { background: rgba(255,255,255,0.1); }
:deep(.dark) .history-row { border-bottom-color: rgba(255,255,255,0.04); }
:deep(.dark) .history-row:hover { background: rgba(102,126,234,0.06); }
:deep(.dark) .history-table-header { border-bottom-color: rgba(255,255,255,0.06); }
:deep(.dark) .empty-circle { background: rgba(255,255,255,0.04); }

/* ── Responsive ── */
@media (max-width: 640px) {
  .idle-icon-wrap {
    width: 90px;
    height: 90px;
  }

  .idle-icon-inner {
    width: 72px;
    height: 72px;
  }

  .idle-title {
    font-size: 19px;
  }

  .idle-subtitle {
    font-size: 13px;
  }

  .start-btn {
    height: 46px !important;
    padding: 0 24px !important;
    font-size: 15px !important;
  }

  .ht-col-dims {
    display: none;
  }

  .ht-col-risk {
    width: 70px;
  }

  .ht-col-score {
    width: 60px;
  }

  .capture-actions {
    flex-direction: column;
  }
}

/* ── Shared: Loading / Video / Capture / Running ── */
.capture-section {
  width: min(100%, 700px);
  margin: 0 auto;
}

.running-section {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

.loading-section {
  text-align: center;
  padding: 60px 20px;
}

.loading-text {
  margin-top: 16px;
  color: #64748b;
}

.video-placeholder {
  width: 100%;
  aspect-ratio: 4 / 3;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #64748b;
  margin-bottom: 16px;
}

.video-container {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 3;
  border-radius: 12px;
  overflow: hidden;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  margin-bottom: 16px;
}

.camera-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.skeleton-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.video-container .video-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  margin-bottom: 0;
}

.video-container .guidance-text {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  margin-top: 0;
}

.video-icon {
  margin-bottom: 12px;
  opacity: 0.6;
}

.video-hint {
  font-size: 14px;
  margin: 0;
}

.guidance-text {
  margin-top: 12px;
  padding: 8px 20px;
  background: rgba(59,130,246,0.2);
  border-radius: 20px;
  color: #60a5fa;
  font-size: 14px;
}

.progress-bar {
  margin-bottom: 16px;
}

.view-tags,
.movement-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  justify-content: center;
}

.capture-hint-card {
  background: #eff6ff !important;
  margin-bottom: 16px;
  text-align: center;
}

.capture-hint-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #2563eb;
  font-weight: 600;
  margin-bottom: 4px;
}

.hint-text {
  font-size: 15px;
}

.hint-desc {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.capture-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.angles-display {
  margin-bottom: 20px;
}

.angle-card {
  background: #f8fafc;
  border-radius: 10px;
  padding: 12px;
  text-align: center;
}

.angle-value {
  font-size: 24px;
  font-weight: 700;
  color: #3b82f6;
}

.angle-name {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

.action-buttons {
  text-align: center;
}

.result-section {
  padding: 20px 0;
}

:deep(.dark) .capture-hint-card {
  background: rgba(59,130,246,0.08) !important;
}

:deep(.dark) .angle-card {
  background: rgba(255,255,255,0.03);
}

:deep(.dark) .loading-text {
  color: #94a3b8;
}

/* ── Reference layout: idle landing page ── */
.assessment-page {
  width: min(100%, 1200px);
  max-width: 1200px;
  gap: 28px;
  margin: 0 auto;
  padding: 0;
}

.main-card,
.history-card {
  width: 100%;
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}

.main-card :deep(.n-card),
.main-card :deep(.n-card__content),
.main-card :deep(.n-card__body),
.main-card :deep(.n-card__container),
.history-card :deep(.n-card),
.history-card :deep(.n-card__content),
.history-card :deep(.n-card__body),
.history-card :deep(.n-card__container),
.idle-main-card :deep(.n-card),
.idle-main-card :deep(.n-card__content),
.idle-main-card :deep(.n-card__body),
.idle-main-card :deep(.n-card__container) {
  padding: 0 !important;
  background: transparent !important;
}

.idle-main-card :deep(.n-card-header) {
  display: none;
}

.idle-section {
  padding: 0;
}

.assessment-intro {
  min-height: 420px;
  display: grid;
  grid-template-columns: 0.95fr 1.05fr;
  position: relative;
  overflow: hidden;
  background: #ffffff;
  border-radius: 32px;
  box-shadow: 0 22px 50px rgba(15, 23, 42, 0.08);
}

.assessment-intro::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top right, rgba(79, 70, 229, 0.08), transparent 34%), radial-gradient(circle at bottom left, rgba(139, 92, 246, 0.06), transparent 28%);
  pointer-events: none;
  z-index: 0;
}

.intro-content {
  padding: 44px 46px 38px;
  position: relative;
  z-index: 1;
}

.intro-heading {
  display: flex;
  align-items: center;
  gap: 18px;
}

.intro-logo {
  width: 66px;
  height: 66px;
  border-radius: 20px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  color: #ffffff;
  background: linear-gradient(135deg, #7c3aed, #8b5cf6);
  box-shadow: 0 18px 38px rgba(124, 58, 237, 0.2);
}

.intro-heading h2 {
  margin: 0;
  color: #0f172a;
  font-size: 36px;
  line-height: 1.05;
  font-weight: 700;
}

.intro-heading p {
  margin: 8px 0 0;
  color: #475569;
  font-size: 15px;
  line-height: 1.75;
}

.intro-features {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin: 38px 0 30px;
}

.intro-feature {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  gap: 8px;
  padding: 20px 18px;
  border-radius: 18px;
  background: #f8f9ff;
  border: 1px solid #eef2ff;
}

.intro-feature > .n-icon {
  width: 42px;
  height: 42px;
  min-width: 42px;
  min-height: 42px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: #eef2ff;
  color: #5b21b6;
  font-size: 20px;
}

.intro-feature div {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.intro-feature strong {
  color: #0f172a;
  font-size: 15px;
  line-height: 1.2;
}

.intro-feature span {
  color: #64748b;
  font-size: 13px;
}

.start-btn {
  height: 54px !important;
  width: 100%;
  max-width: 460px;
  padding: 0 34px !important;
  border-radius: 20px !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  background: linear-gradient(90deg, #6d28d9, #8b5cf6) !important;
  box-shadow: 0 18px 34px rgba(109, 40, 217, 0.24);
}

.capture-orbit {
  position: relative;
  min-height: 420px;
  z-index: 1;
  padding: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%);
  border-radius: 0 32px 32px 0;
  overflow: hidden;
}

.capture-orbit::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top right, rgba(255,255,255,0.18), transparent 20%), radial-gradient(circle at bottom left, rgba(255,255,255,0.10), transparent 18%);
  pointer-events: none;
  z-index: 0;
}

.orbit {
  position: absolute;
  left: 50%;
  top: 50%;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.24);
  transform: translate(-50%, -50%);
}

.orbit-one { width: 190px; height: 190px; }
.orbit-two { width: 280px; height: 280px; }
.orbit-three { width: 360px; height: 360px; }

.orbit-center {
  position: absolute;
  left: 50%;
  top: 52%;
  width: 132px;
  height: 132px;
  transform: translate(-50%, -50%);
  display: grid;
  place-items: center;
  border-radius: 28px;
  background: rgba(255,255,255,0.18);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.2);
  color: #f8f7ff;
  z-index: 2;
}

.orbit-center n-icon,
.orbit-center svg {
  width: 54px;
  height: 54px;
}

.orbit-point {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  z-index: 2;
}

.orbit-point img {
  width: 72px;
  height: 72px;
  border-radius: 22px;
  padding: 14px;
  background: rgba(255,255,255,0.16);
  border: 1px solid rgba(255,255,255,0.24);
  object-fit: contain;
}

.orbit-point span {
  margin-top: 0;
  font-size: 14px;
}

.orbit-front { left: 50%; top: 14%; transform: translateX(-50%); }
.orbit-side { left: 16%; top: 60%; transform: translateY(-50%); }
.orbit-back { right: 16%; top: 60%; transform: translateY(-50%); }

.mobile-intro-features {
  display: none;
}

/* ── Reference layout: history ── */
.history-card :deep(.n-card-header) {
  padding: 20px 28px 14px;
}

.history-card :deep(.n-card__content) {
  padding: 0 24px 20px !important;
}

.history-heading,
.history-filter {
  display: flex;
  align-items: center;
}

.history-heading { gap: 10px; }
.history-heading > .n-icon { color: #5666ed; font-size: 25px; }
.history-title { color: #171c3d; font-size: 19px; font-weight: 700; }

.history-filter {
  gap: 7px;
  height: 36px;
  padding: 0 13px;
  border: 1px solid #dee2ef;
  border-radius: 8px;
  color: #40465d;
  font-size: 13px;
}

.history-filter > .n-icon { color: #5e6eed; }
.history-filter span { margin-left: 7px; color: #6372ee; }

.history-table-header,
.history-row {
  display: grid;
  grid-template-columns: 1.05fr 1.1fr 1.55fr 1.25fr;
  align-items: center;
}

.history-table-header {
  padding: 11px 24px;
  border: none;
  border-radius: 7px;
  background: linear-gradient(90deg, #f6f7fb, #f9f8fd);
  color: #34394f;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0;
  text-transform: none;
}

.history-row {
  min-height: 80px;
  padding: 10px 14px;
  border-bottom: 1px solid #edf0f6;
  border-radius: 0;
}

.history-row:hover {
  transform: none;
  background: #fafaff;
}

.ht-col { width: auto; min-width: 0; }
.ht-col-date { flex-direction: row; align-items: center; gap: 11px; }

.date-icon,
.problem-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 10px;
  color: #6873ee;
  background: #f1f1ff;
  font-size: 20px;
}

.date-copy,
.score-copy,
.problem-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.date-copy strong,
.problem-copy strong { color: #30364e; font-size: 13px; font-weight: 500; }
.date-copy small,
.score-copy small,
.problem-copy small { margin-top: 3px; color: #9aa1b4; font-size: 12px; }

.ht-col-score { justify-content: flex-start; gap: 12px; }

.score-ring {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 4px solid currentColor;
  border-right-color: #e7e9ef;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 600;
}

.score-ring > small { margin-left: 1px; font-size: 9px; }
.score-copy strong { font-size: 13px; }
.good { color: #27bd67 !important; }
.warning { color: #f4ae28 !important; }
.danger { color: #ee5b64 !important; }

.ht-col-problem { gap: 12px; padding-right: 16px; }
.problem-icon.warning { background: #fff7e7; }
.problem-icon.danger { background: #fff0f1; }
.problem-icon.good { background: #eafaf1; }
.problem-copy strong,
.problem-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.ht-col-action { justify-content: flex-end; gap: 10px; }
.ht-col-action .n-button { height: 34px; border-radius: 8px; font-size: 12px; }
.report-btn { color: #5c6be9; }
.compare-btn { background: linear-gradient(90deg, #5368ee, #8b68e8) !important; border: none !important; }

@media (max-width: 1100px) {
  .assessment-intro { grid-template-columns: 1fr 0.7fr; }
  .intro-content { padding: 36px 30px; }
  .intro-features { gap: 8px; }
  .intro-feature { min-width: 0; padding: 0 11px; }
  .orbit-three { width: 280px; height: 280px; }
  .orbit-side { left: calc(50% - 135px); }
  .orbit-back { right: calc(50% - 135px); }
  .history-table-header,
  .history-row { grid-template-columns: 1fr 1fr 1.35fr; }
  .history-table-header .ht-col-action,
  .ht-col-action { display: none; }
}

@media (max-width: 760px) {
  .assessment-intro { display: block; min-height: 0; }
  .intro-content { padding: 28px 22px; }
  .intro-heading { gap: 15px; }
  .intro-logo { width: 58px; height: 58px; border-radius: 16px; font-size: 34px; }
  .intro-heading h2 { font-size: 21px; }
  .intro-heading p { font-size: 13px; }
  .intro-features,
  .capture-orbit { display: none; }
  .start-btn { width: 100%; margin-top: 24px; }
  .mobile-intro-features { display: block; padding: 0 14px 18px; }
  .mobile-intro-features .info-card {
    min-height: 92px;
    padding: 10px 6px;
    flex-direction: column;
    justify-content: center;
    gap: 2px;
    text-align: center;
  }
  .mobile-intro-features .n-icon { color: #846ce8; font-size: 22px; }
  .mobile-intro-features strong { font-size: 11px; }
  .mobile-intro-features span { color: #9aa1b4; font-size: 10px; }
  .history-card :deep(.n-card-header) { padding: 17px 16px 12px; }
  .history-card :deep(.n-card__content) { padding: 0 12px 14px !important; }
  .history-title { font-size: 16px; }
  .history-filter { display: none; }
  .history-table-header,
  .history-row { grid-template-columns: 1.2fr 0.8fr; }
  .history-table-header .ht-col-problem,
  .ht-col-problem { display: none; }
  .history-table-header { padding: 10px 12px; }
  .history-row { padding: 10px 4px; }
  .date-icon { width: 32px; height: 32px; }
  .score-ring { width: 43px; height: 43px; }
}

/* ── Final visual direction: light, wide assessment card ── */
@media (min-width: 761px) {
  .assessment-page {
    width: 100%;
    max-width: 1480px;
    gap: 26px;
  }

  .assessment-intro {
    min-height: 390px;
    padding: 0;
    grid-template-columns: 1.05fr 0.95fr;
    border: 1px solid #e5e7f3;
    border-radius: 18px;
    background:
      radial-gradient(circle at 82% 48%, rgba(116, 105, 231, 0.12) 0, rgba(116, 105, 231, 0.055) 25%, transparent 48%),
      linear-gradient(110deg, #ffffff 0%, #ffffff 55%, #faf9ff 100%);
    box-shadow: 0 8px 28px rgba(71, 79, 128, 0.08);
  }

  .assessment-intro::before {
    content: '';
    position: absolute;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background: none;
  }

  .assessment-intro::after {
    content: '';
    position: absolute;
    top: -32px;
    right: -18px;
    bottom: auto;
    left: auto;
    width: 210px;
    height: 180px;
    opacity: 0.5;
    background-image: radial-gradient(#d9d3ff 2px, transparent 2px);
    background-size: 20px 20px;
  }

  .intro-content {
    padding: 38px 42px 34px;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }

  .intro-heading {
    gap: 24px;
    align-items: center;
  }

  .intro-logo {
    width: 108px;
    height: 108px;
    padding: 0;
    border-radius: 24px;
    font-size: 40px;
    background: transparent;
    box-shadow: none;
  }

  .intro-logo img {
    width: 100%;
    height: 100%;
    border-radius: 24px;
    object-fit: contain;
    object-position: center;
    transform: none;
    background: transparent;
    mix-blend-mode: normal;
    filter: none;
  }

  .intro-heading h2 {
    color: #151a36;
    font-size: 27px;
    line-height: 1.3;
    letter-spacing: 0;
  }

  .intro-heading p {
    margin: 4px 0 0;
    color: #646c84;
    font-size: 14px;
    line-height: 1.55;
  }

  .intro-features {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin: 34px 0 26px;
  }

  .intro-feature {
    min-height: 72px;
    padding: 12px 14px;
    flex-direction: row;
    align-items: center;
    gap: 11px;
    border: 1px solid #e8eaf3;
    border-radius: 11px;
    background: rgba(255, 255, 255, 0.72);
  }

  .intro-feature > .n-icon {
    width: 34px;
    height: 34px;
    min-width: 34px;
    min-height: 34px;
    border-radius: 10px;
    color: #9472e9;
    background: #f4f1ff;
    font-size: 22px;
  }

  .intro-feature strong {
    color: #282d47;
    font-size: 13px;
    white-space: nowrap;
  }

  .intro-feature span {
    margin-top: 2px;
    color: #8a92a7;
    font-size: 11px;
    white-space: nowrap;
  }

  .start-btn {
    width: fit-content;
    min-width: 238px;
    height: 46px !important;
    padding: 0 24px !important;
    border-radius: 8px !important;
    font-size: 14px !important;
    box-shadow: 0 7px 17px rgba(91, 94, 230, 0.21);
    background: linear-gradient(90deg, #5168ef, #9269e8) !important;
  }

  .capture-orbit {
    min-height: 390px;
    padding: 0;
    overflow: visible;
    border-radius: 0 18px 18px 0;
    background:
      radial-gradient(circle at center, rgba(114, 104, 231, 0.12) 0%, rgba(114, 104, 231, 0.055) 36%, transparent 68%);
  }

  .capture-orbit::before {
    background: none;
  }

  .orbit {
    border-color: rgba(95, 101, 220, 0.12);
  }

  .orbit-one {
    width: 170px;
    height: 170px;
    background: rgba(105, 103, 229, 0.05);
  }

  .orbit-two { width: 250px; height: 250px; }
  .orbit-three { width: 330px; height: 330px; }

  .orbit-center {
    top: 51%;
    width: 110px;
    height: 110px;
    border-radius: 28px;
    color: #5765e9;
    background: rgba(255, 255, 255, 0.84);
    box-shadow: 0 14px 36px rgba(91, 94, 230, 0.13);
    font-size: 64px;
  }

  .orbit-center > .n-icon,
  .orbit-center svg {
    width: 64px !important;
    height: 64px !important;
    font-size: 64px !important;
  }

  .orbit-point {
    gap: 3px;
    color: #5566e7;
    font-size: 12px;
  }

  .orbit-point img {
    width: 60px;
    height: 60px;
    padding: 8px;
    border: 1px solid rgba(105, 105, 222, 0.12);
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.76);
    box-shadow: 0 5px 14px rgba(85, 92, 190, 0.08);
    object-fit: cover;
    mix-blend-mode: multiply;
  }

  .orbit-point span {
    color: #5364e7;
    font-size: 12px;
  }

  .orbit-front {
    left: 50%;
    top: 6%;
    transform: translateX(-50%);
  }

  .orbit-side {
    left: calc(50% - 142px);
    top: 73%;
    transform: translate(-50%, -50%);
  }

  .orbit-back {
    left: calc(50% + 142px);
    right: auto;
    top: 73%;
    transform: translate(-50%, -50%);
  }

  .history-card {
    width: calc(100% - 64px);
    margin: 0 32px;
    overflow: hidden;
    border: 1px solid #e6e9f2 !important;
    border-radius: 16px !important;
    background: #ffffff !important;
    box-shadow: 0 7px 24px rgba(71, 79, 128, 0.07) !important;
  }

  .history-card :deep(.n-card-header),
  .history-card :deep(.n-card__content) {
    background: #ffffff !important;
  }
}

/* ── Full assessment workflow ── */
.capture-analyzing-overlay,
.countdown-overlay {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #fff;
  background: rgba(15, 23, 42, 0.68);
  backdrop-filter: blur(2px);
}

.countdown-overlay strong {
  font-size: clamp(64px, 10vw, 108px);
  line-height: 1;
  text-shadow: 0 8px 28px rgba(0, 0, 0, 0.32);
}

.countdown-overlay span { font-size: 16px; }
.clickable-tag { cursor: pointer; }

.capture-error-box {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 16px;
  padding: 10px 14px;
  color: #b42318;
  border: 1px solid #fecdca;
  border-radius: 10px;
  background: #fef3f2;
}

.capture-error-box span { flex: 1; }

.upload-photo-btn {
  height: 40px;
  padding: 0 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  box-sizing: border-box;
  cursor: pointer;
  color: #334155;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  background: #fff;
  transition: border-color .2s, color .2s, background .2s;
}

.upload-photo-btn:hover { color: #5b67e8; border-color: #7c83ed; background: #f8f8ff; }
.upload-photo-btn.disabled { cursor: not-allowed; opacity: .5; }
.upload-photo-btn input { display: none; }

.static-summary-card {
  margin-bottom: 16px;
  border: 1px solid #dbeafe !important;
  background: #f0f7ff !important;
}

.static-summary-card p { margin: 7px 0 10px; color: #475569; line-height: 1.6; }
.static-summary-card small { display: block; margin-top: 10px; color: #64748b; }
.step-progress { margin-bottom: 16px; }

.assessment-workspace {
  display: grid;
  grid-template-columns: minmax(320px, 0.85fr) minmax(0, 1.65fr);
  gap: 18px;
  align-items: stretch;
  margin-bottom: 20px;
}

.camera-panel,
.movement-demo-card {
  min-width: 0;
  height: 100%;
  box-sizing: border-box;
  border: 1px solid #e7e9f3;
  border-radius: 14px;
  background: linear-gradient(145deg, #fff, #faf9ff);
  box-shadow: 0 8px 22px rgba(71, 79, 128, 0.06);
}

.camera-panel { order: 2; padding: 14px; }

.workspace-panel-title {
  min-height: 28px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #30364e;
  font-size: 15px;
  font-weight: 700;
}

.camera-panel .video-container { margin-bottom: 0; }

.movement-demo-card {
  order: 1;
  margin: 0;
  padding: 14px;
  text-align: center;
}

.demo-panel-title { text-align: left; }
.demo-title { color: #202744; font-size: 18px; font-weight: 700; }
.demo-step { margin-top: 4px; color: #616be8; font-weight: 600; }
.demo-duration { margin-top: 10px; color: #94a3b8; font-size: 12px; }

.demo-media-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  max-width: none;
  margin: 14px auto 0;
}

.demo-media-grid.single-media {
  grid-template-columns: minmax(0, 1fr);
  max-width: none;
}

.demo-placeholder {
  min-height: 130px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 7px;
  color: #7c83a5;
  border: 1px dashed #cdd2e5;
  border-radius: 12px;
  background: #f7f8fc;
  overflow: hidden;
}

.demo-placeholder img,
.demo-placeholder video { width: 100%; height: 280px; display: block; object-fit: contain; border-radius: 12px; background: #f4f1fb; }
.demo-media-grid.single-media .demo-placeholder img,
.demo-media-grid.single-media .demo-placeholder video { height: 360px; }
.demo-placeholder small { max-width: 520px; color: #475569; line-height: 1.6; }
.demo-instruction { max-width: none; margin: 12px auto 0; padding: 9px 14px; color: #1d4ed8; line-height: 1.6; border: 1px solid #bfdbfe; border-radius: 9px; background: #eff6ff; }
.angle-card.reached { border: 1px solid #86efac; background: #f0fdf4; }
.plateau-tag { margin-top: 10px; }

.transition-hint,
.movement-done-box {
  margin: 0 0 16px;
  padding: 12px 16px;
  text-align: center;
  border-radius: 10px;
}

.transition-hint { color: #92400e; border: 1px solid #fcd34d; background: #fffbeb; }
.movement-done-box { display: flex; align-items: center; justify-content: center; gap: 8px; color: #166534; border: 1px solid #86efac; background: #f0fdf4; }
.movement-done-box .n-icon { font-size: 22px; }
.movement-done-box span { color: #64748b; font-size: 13px; }
.action-buttons { display: flex; justify-content: center; gap: 12px; }

.preview-modal {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(2, 6, 23, .78);
}

.preview-dialog {
  width: fit-content;
  max-width: 92vw;
  max-height: 92vh;
  padding: 16px;
  overflow: auto;
  border-radius: 14px;
  background: #fff;
}

.preview-header { display: flex; align-items: center; justify-content: space-between; gap: 24px; margin-bottom: 10px; }
.preview-canvas { display: block; width: auto; height: auto; max-width: 84vw; max-height: 76vh; border-radius: 8px; }

.history-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.history-summary > div { padding: 12px 14px; border: 1px solid #e8eaf3; border-radius: 10px; background: #fafbff; }
.history-summary small { display: block; margin-bottom: 5px; color: #8a92a7; }
.history-summary strong { color: #262c49; font-size: 18px; }
.history-summary em { margin-left: 3px; color: #8a92a7; font-size: 12px; font-style: normal; font-weight: 400; }

@media (max-width: 640px) {
  .movement-done-box { flex-wrap: wrap; }
  .capture-actions { align-items: stretch; }
  .upload-photo-btn { width: 100%; }
  .demo-media-grid { grid-template-columns: 1fr; }
  .demo-placeholder img,
  .demo-placeholder video { height: 260px; }
  .history-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
