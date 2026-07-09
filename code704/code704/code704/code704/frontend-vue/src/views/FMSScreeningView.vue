<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fmsApi } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { FMSRecord } from '../types'
import MovementDemo from '../components/MovementDemo.vue'
import PipDemoVideo from '../components/PipDemoVideo.vue'
import {
  playCountdownBeep,
  playStartBeep,
  playEndBeep,
  playFinalBeep
} from '../utils/audio'
import {
  NCard, NButton, NSpace, NTag, NProgress, NIcon, NText,
  NResult, NSpin, NUpload, NList, NListItem, NDivider,
  NCollapse, NCollapseItem, NModal, NModalContent, NEmpty, useMessage
} from 'naive-ui'
import {
  AnalyticsOutline, VideocamOutline, CheckmarkCircleOutline,
  PlayCircleOutline, CloudUploadOutline, ChevronForwardOutline,
  AccessibilityOutline, CameraOutline, TrophyOutline,
  WarningOutline, ArrowForwardOutline, CheckmarkCircle,
  CloseCircleOutline, FileOutline, ArrowBackOutline,
  RefreshOutline, TrashOutline, EyeOutline
} from '@vicons/ionicons5'

const router = useRouter()
const authStore = useAuthStore()
const message = useMessage()

// ── FMS test definitions (matches React frontend) ──
const FMS_TESTS = [
  { id: 0, name: '闭眼单腿站立', desc: '闭上双眼，抬起单腿，尽量保持平衡', instruction: '闭上双眼，抬起单腿，尽量保持平衡（站立越久分数越高，满分60秒）' },
  { id: 1, name: '徒手过头深蹲', desc: '双手举过头顶，做深蹲至最低点保持', instruction: '双手举过头顶，做深蹲至最低点保持（膝盖弯曲角度越小分数越高）' },
  { id: 2, name: '肩关节活动度', desc: '一手从肩上、一手从腰后向背后靠拢', instruction: '一手从肩上、一手从腰后向背后靠拢（双手距离越近分数越高）' },
  { id: 3, name: '平板支撑', desc: '保持平板支撑姿势，尽量坚持', instruction: '保持平板支撑姿势，尽量坚持（坚持越久分数越高，满分120秒）' },
  { id: 4, name: '弓步蹲对称', desc: '先做左侧弓步蹲，再做右侧弓步蹲', instruction: '先做左侧弓步蹲，再做右侧弓步蹲（左右角度越对称分数越高）' }
]

// ── Demo media mapping (Vue public assets) ──
const FMS_MEDIA: Record<number, string[]> = {
  0: ['/media/fms/stand_left_fms.png', '/media/fms/stand_front_fms.png'],
  1: ['/media/fms/squat_left_fms.mp4'],
  2: ['/media/fms/shoulder_left.png'],
  3: ['/media/fms/stand_back_fms.png'],
  4: ['/media/fms/lunge_left_fms.mp4'],
}

type ScreenMode = 'idle' | 'camera' | 'upload' | 'done'
type TestPhase = 'preparing' | 'countdown' | 'running' | 'completed' | 'skipped'

const mode = ref<ScreenMode>('idle')
const loading = ref(false)
const records = ref<FMSRecord[]>([])
const result = ref<any>(null)

// Camera WebSocket state
const cameraPhase = ref<TestPhase>('preparing')
const currentTest = ref(-1)
const currentTestName = ref('')
const testInstruction = ref('')
const testMessage = ref('')
const testScore = ref<number | null>(null)
const countdown = ref(0)
const overallProgress = ref(0)
const allScores = ref<Record<number, number>>({})
const noPersonWarning = ref(false)
const skeletonVisible = ref(false)

// ── New real-time feedback state ──
const guidance = ref('')
const testDuration = ref(0)
const showScoreOverlay = ref(false)

const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const overlayCanvasRef = ref<HTMLCanvasElement | null>(null)
let ws: WebSocket | null = null
let stream: MediaStream | null = null
let captureTimer: number = 0
let countdownTimer: number = 0

// ── Picture-in-Picture demo video state ──
const demoSectionRef = ref<HTMLElement | null>(null)
const movementDemoRef = ref<InstanceType<typeof MovementDemo> | null>(null)
const pipVideoRef = ref<InstanceType<typeof PipDemoVideo> | null>(null)
const pipVisible = ref(false)
const pipMinimized = ref(false)
const pipClosed = ref(false)
const pipMuted = ref(true)
const pipCurrentTime = ref(0)
let pipObserver: IntersectionObserver | null = null

const pipMediaSrc = computed(() => {
  const media = FMS_MEDIA[currentTest.value]
  return media?.[0] || ''
})

const isCurrentMediaVideo = computed(() => /\.(mp4|webm|mov|avi)$/i.test(pipMediaSrc.value))

function syncPipCurrentTime() {
  if (!isCurrentMediaVideo.value) return
  const video = movementDemoRef.value?.videoRef
  if (video) {
    pipCurrentTime.value = video.currentTime
  }
}

function syncTimeBackToDemo() {
  if (!isCurrentMediaVideo.value) return
  const demoVideo = movementDemoRef.value?.videoRef
  const pipVideo = pipVideoRef.value?.videoRef
  const latestTime = pipVideo?.currentTime ?? pipCurrentTime.value
  if (demoVideo && Math.abs(demoVideo.currentTime - latestTime) > 0.3) {
    demoVideo.currentTime = latestTime
  }
}

function initPipObserver() {
  destroyPipObserver()
  if (!demoSectionRef.value) return
  pipObserver = new IntersectionObserver(
    ([entry]) => {
      if (!entry.isIntersecting && mode.value === 'camera' && !pipClosed.value && !pipMinimized.value) {
        syncPipCurrentTime()
        const demoVideo = movementDemoRef.value?.videoRef
        if (demoVideo) demoVideo.pause()
        pipVisible.value = true
      } else if (entry.isIntersecting && !pipClosed.value) {
        syncTimeBackToDemo()
        pipVisible.value = false
        pipMinimized.value = false
      }
    },
    { threshold: 0.15, rootMargin: '-80px 0px 0px 0px' }
  )
  pipObserver.observe(demoSectionRef.value)
}

function destroyPipObserver() {
  pipObserver?.disconnect()
  pipObserver = null
}

function onPipClose() {
  pipVisible.value = false
  pipClosed.value = true
}

function onPipMinimize() {
  pipVisible.value = false
  pipMinimized.value = true
}

function onPipTimeUpdate(time: number) {
  pipCurrentTime.value = time
}

function reopenPip() {
  syncPipCurrentTime()
  pipClosed.value = false
  pipMinimized.value = false
  pipVisible.value = true
}

// Upload state
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref('')
const uploadingTestIndex = ref<number | null>(null)
const uploadedResults = ref<Record<number, any>>({})
const fileInputRef = ref<HTMLInputElement | null>(null)
let pendingUploadTestIndex = -1

function triggerFileUpload(testIndex: number) {
  pendingUploadTestIndex = testIndex
  fileInputRef.value?.click()
}

function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file && pendingUploadTestIndex >= 0) {
    handleSingleTestUpload(pendingUploadTestIndex, file)
  }
  input.value = ''
  pendingUploadTestIndex = -1
}

// COCO skeleton connections
const SKELETON: [number, number][] = [
  [0, 1], [0, 2], [1, 3], [2, 4],
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  [5, 11], [6, 12], [11, 12],
  [11, 13], [13, 15], [12, 14], [14, 16]
]

// ── History ──
function loadHistory() {
  fmsApi.getRecords().then(r => { records.value = r }).catch(() => {})
}

async function deleteHistoryRecord(record: FMSRecord) {
  if (!window.confirm('确定删除这条 FMS 筛查记录吗？删除后无法恢复。')) return
  try {
    await fmsApi.deleteRecord(record.id)
    records.value = records.value.filter(r => r.id !== record.id)
    message.success('筛查记录已删除')
  } catch (err: any) {
    message.error(err?.response?.data?.detail || '删除失败，请重试')
  }
}

// ── Camera mode ──
async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'user' }
    })
    if (videoRef.value) {
      videoRef.value.srcObject = stream
      videoRef.value.play().catch(() => {})
    }
    return true
  } catch {
    return false
  }
}

// Attach stream when video element appears in DOM (after mode switch renders it)
watch(mode, async (newMode) => {
  if (newMode === 'camera' && stream) {
    await nextTick()
    if (videoRef.value) {
      videoRef.value.srcObject = stream
      videoRef.value.play().catch(() => {})
    }
  }
})

function stopCamera() {
  clearInterval(captureTimer)
  clearInterval(countdownTimer)
  stream?.getTracks().forEach(t => t.stop())
  stream = null
  ws?.close()
  ws = null
}

function drawSkeleton(keypointsList: any[]) {
  const canvas = overlayCanvasRef.value
  const video = videoRef.value
  if (!canvas || !video) return

  const displayW = canvas.clientWidth || video.videoWidth || 640
  const displayH = canvas.clientHeight || video.videoHeight || 480
  if (displayW === 0 || displayH === 0) return

  canvas.width = displayW
  canvas.height = displayH

  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const scaleX = displayW / (video.videoWidth || 640)
  const scaleY = displayH / (video.videoHeight || 480)

  for (const person of keypointsList) {
    const kps = person.keypoints || []
    const confs = person.confidences || Array(kps.length).fill(1)
    if (kps.length < 17) continue

    ctx.strokeStyle = '#00ff88'
    ctx.lineWidth = 2
    for (const [i, j] of SKELETON) {
      if (i < kps.length && j < kps.length && confs[i] > 0.3 && confs[j] > 0.3) {
        const [x1, y1] = kps[i]; const [x2, y2] = kps[j]
        if (x1 > 0 && y1 > 0 && x2 > 0 && y2 > 0) {
          ctx.beginPath()
          ctx.moveTo(x1 * scaleX, y1 * scaleY)
          ctx.lineTo(x2 * scaleX, y2 * scaleY)
          ctx.stroke()
        }
      }
    }

    for (let i = 0; i < kps.length; i++) {
      if (confs[i] > 0.3) {
        const [x, y] = kps[i]
        if (x > 0 && y > 0) {
          ctx.fillStyle = '#ff4466'
          ctx.beginPath()
          ctx.arc(x * scaleX, y * scaleY, 4, 0, Math.PI * 2)
          ctx.fill()
        }
      }
    }
  }
}

function startFrameCapture() {
  clearInterval(captureTimer)
  const canvas = canvasRef.value
  const video = videoRef.value
  if (!canvas || !video) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  captureTimer = window.setInterval(() => {
    if (!video.videoWidth) return
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    ctx.drawImage(video, 0, 0)
    const b64 = canvas.toDataURL('image/jpeg', 0.6)
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'frame', image: b64 }))
    }
  }, 200)
}

function scrollToCameraSection() {
  syncPipCurrentTime()
  const cameraSection = document.getElementById('camera-section')
  if (cameraSection) {
    cameraSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

function startCountdown() {
  if (ws?.readyState !== WebSocket.OPEN) {
    message.warning('摄像头服务未连接，请退出后重新开始筛查')
    return
  }
  skeletonVisible.value = true
  cameraPhase.value = 'countdown'
  countdown.value = 3
  noPersonWarning.value = false
  // Notify backend immediately so skeleton updates during countdown
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'start_test' }))
  }
  // Scroll user focus to the real-time camera area while keeping demo playing in PiP
  scrollToCameraSection()

  countdownTimer = window.setInterval(() => {
    countdown.value--
    playCountdownBeep()
    if (countdown.value <= 0) {
      clearInterval(countdownTimer)
      playStartBeep()
      cameraPhase.value = 'running'
      testMessage.value = '检测中...'
    }
  }, 1000)
}

function skipTest() {
  playEndBeep()
  cameraPhase.value = 'skipped'
  testMessage.value = '已跳过当前动作'
  noPersonWarning.value = false
  showScoreOverlay.value = false
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'skip_test' }))
  }
}

function completeCurrentTest() {
  if (ws?.readyState !== WebSocket.OPEN) {
    message.warning('摄像头连接已断开，请退出重试')
    return
  }
  message.info('正在计算分数...')
  ws!.send(JSON.stringify({ type: 'next_test' }))
}

function advanceToNextTest() {
  showScoreOverlay.value = false
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'next_test' }))
  }
}

function finishTests() {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'finish' }))
  }
}

function handleWSMessage(data: any) {
  if (data.type === 'test_ready') {
    currentTest.value = data.test
    currentTestName.value = ''
    testInstruction.value = data.instruction || ''
    testMessage.value = data.instruction || '准备开始'
    guidance.value = data.instruction || '准备开始'
    testScore.value = null
    testDuration.value = 0
    noPersonWarning.value = false
    showScoreOverlay.value = false
    overallProgress.value = (data.test / 5) * 100
    cameraPhase.value = 'preparing'
    skeletonVisible.value = false
    currentTestName.value = FMS_TESTS[data.test]?.name || ''
    nextTick(() => initPipObserver())

  } else if (data.type === 'test_skipped') {
    cameraPhase.value = 'skipped'

  } else if (data.type === 'frame_result') {
    if (data.fms_status === 'no_person') {
      noPersonWarning.value = true
      if (cameraPhase.value === 'running') {
        testMessage.value = '未检测到人体，请站在摄像头正前方'
      }
      return
    }

    noPersonWarning.value = false

    // Draw skeleton in all phases (preparing/countdown/running/completed)
    if (data.keypoints?.length) {
      drawSkeleton(data.keypoints)
    }

    if (data.guidance) {
      guidance.value = data.guidance
    }

    if (data.fms_status === 'started' || data.fms_status === 'running') {
      if (cameraPhase.value === 'countdown' || cameraPhase.value === 'running') {
        if (cameraPhase.value !== 'running') cameraPhase.value = 'running'
        testMessage.value = data.guidance || data.message || '检测中...'
      }
      if (data.duration !== undefined) {
        testDuration.value = data.duration
      }
    } else if (data.fms_status === 'completed') {
      if (cameraPhase.value === 'completed' || cameraPhase.value === 'skipped') return
      playEndBeep()
      cameraPhase.value = 'completed'
      showScoreOverlay.value = true
      testScore.value = data.score
      allScores.value = { ...allScores.value, [currentTest.value]: data.score }
      if (data.duration !== undefined && data.duration !== null) testMessage.value = `保持时间: ${data.duration}秒`
      else if (data.depth_angle !== undefined) testMessage.value = `深蹲深度: ${data.depth_angle}°, 躯干倾斜: ${data.trunk_tilt ?? '--'}°`
      else if (data.hand_distance !== undefined) testMessage.value = `双手距离: ${data.hand_distance}cm`
      else if (data.score !== undefined) testMessage.value = `得分: ${data.score}`
    } else if (data.fms_status === 'step_complete') {
      testMessage.value = data.guidance || '换边继续'
    }

  } else if (data.type === 'all_tests_complete') {
    overallProgress.value = 100
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'finish' }))
    }
  } else if (data.type === 'fms_result') {
    playFinalBeep()
    result.value = data
    mode.value = 'done'
    stopCamera()
  } else if (data.type === 'error') {
    testMessage.value = data.message || '发生错误'
    message.error(data.message || '发生错误')
    if (data.message?.includes('令牌') || data.message?.includes('认证')) {
      stopCamera()
      mode.value = 'idle'
      message.error('登录已过期，请重新登录')
    }
  }
}

async function startScreening() {
  const ok = await startCamera()
  if (!ok) {
    alert('无法访问摄像头，请使用 HTTPS 或 localhost 访问')
    return
  }
  if (!authStore.token) {
    alert('请先登录')
    return
  }
  mode.value = 'camera'
  cameraPhase.value = 'preparing'
  currentTest.value = -1
  allScores.value = {}
  overallProgress.value = 0
  noPersonWarning.value = false
  showScoreOverlay.value = false
  guidance.value = ''
  testDuration.value = 0
  pipClosed.value = false
  pipMinimized.value = false
  pipVisible.value = false
  nextTick(() => initPipObserver())

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${protocol}//${window.location.host}/api/fms/ws?token=${encodeURIComponent(authStore.token)}`)

  ws.onopen = () => {
    ws!.send(JSON.stringify({ type: 'start' }))
    setTimeout(() => startFrameCapture(), 300)
  }
  ws.onmessage = (e) => {
    try { handleWSMessage(JSON.parse(e.data)) } catch { /* ignore */ }
  }
  ws.onerror = () => { testMessage.value = 'WebSocket 连接失败' }
  ws.onclose = (e) => {
    if (mode.value !== 'camera') return
    message.error(`摄像头连接已断开${e.code ? ` (${e.code})` : ''}，请退出重试`)
    testMessage.value = '连接已断开，请退出重试'
    clearInterval(captureTimer)
  }
}

// ── Upload mode ──
function enterUploadMode() {
  mode.value = 'upload'
  uploadedResults.value = {}
}

async function handleSingleTestUpload(testIndex: number, file: File) {
  if (!file) return false
  uploadingTestIndex.value = testIndex
  uploading.value = true
  uploadProgress.value = 0
  uploadStatus.value = `正在上传「${FMS_TESTS[testIndex].name}」视频...`
  try {
    const res = await fmsApi.uploadSingleTestVideo(testIndex, file, (pct) => {
      uploadProgress.value = pct
      if (pct >= 100) uploadStatus.value = '正在分析视频（逐帧处理中，请稍候）...'
    })
    uploadStatus.value = `「${FMS_TESTS[testIndex].name}」分析完成！`
    uploadedResults.value = { ...uploadedResults.value, [testIndex]: res }
    return true
  } catch (e: any) {
    uploadStatus.value = `「${FMS_TESTS[testIndex].name}」上传失败`
    return false
  } finally {
    uploading.value = false
    uploadingTestIndex.value = null
    uploadProgress.value = 0
    uploadStatus.value = ''
  }
}

async function handleCombineResults() {
  uploadStatus.value = '正在生成综合报告...'
  uploading.value = true
  try {
    const res = await fmsApi.combineResults()
    playFinalBeep()
    result.value = res
    mode.value = 'done'
  } catch (e: any) {
    uploadStatus.value = '生成报告失败，请重试'
  } finally {
    uploading.value = false
    uploadStatus.value = ''
  }
}

function retry() {
  mode.value = 'idle'
  result.value = null
  stopCamera()
}

function viewReport() {
  const recordId = result.value?.record_id
  if (recordId) {
    router.push(`/fms/report/${recordId}`)
  }
}

// ── Fallback result when last test skipped and WS disconnected ──
function buildFallbackResult() {
  const dims = ['balance', 'flexibility', 'upper_limb', 'core', 'symmetry']
  const scoreList = dims.map((d, i) => ({ dimension: d, label: d, score: allScores.value[i] || 0 }))
  const avg = scoreList.reduce((a, b) => a + b.score, 0) / scoreList.length
  const risk = avg >= 70 ? 'low' : avg >= 40 ? 'medium' : 'high'
  result.value = {
    overall_score: Math.round(avg),
    risk_level: risk,
    scores: scoreList,
    problem_tags: [],
    posture_report: {}
  }
  mode.value = 'done'
  stopCamera()
}

onMounted(() => { loadHistory() })
onUnmounted(() => {
  stopCamera()
  destroyPipObserver()
})
</script>

<script lang="ts">
export default { name: 'FMSScreeningView' }
</script>

<template>
  <div class="fms-page">
    <!-- ═══ Idle: Intro + Actions ═══ -->
    <template v-if="mode === 'idle'">
      <n-card :bordered="false" class="main-card" size="large">
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <n-icon size="22" :component="AnalyticsOutline" class="header-icon" />
              <span class="header-title">FMS 功能性动作筛查</span>
            </div>
          </div>
        </template>

        <!-- FMS Intro -->
        <div class="intro-card">
          <div class="intro-icon">
            <n-icon size="48" :component="AccessibilityOutline" />
          </div>
          <div class="intro-content">
            <h3 class="intro-title">什么是 FMS？</h3>
            <p class="intro-desc">
              功能性动作筛查（Functional Movement Screen）是一套评估动作质量的系统，
              通过5个基础动作模式，识别身体在灵活性和稳定性方面的短板。
              系统将通过摄像头实时检测您的运动能力指标，全程约2-3分钟。
            </p>
          </div>
        </div>

        <!-- 5 Test Cards -->
        <div class="test-grid">
          <div v-for="test in FMS_TESTS" :key="test.id" class="test-item">
            <div class="test-num">{{ test.id + 1 }}</div>
            <div class="test-info">
              <div class="test-name">{{ test.name }}</div>
              <div class="test-desc">{{ test.desc }}</div>
            </div>
            <n-tag size="small" round :bordered="false" :color="{ color: '#8b5cf6', textColor: 'white' }">
              第{{ test.id + 1 }}项
            </n-tag>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="action-buttons">
          <n-space vertical size="medium" align="center">
            <n-button type="primary" size="large" @click="startScreening">
              <template #icon><n-icon :component="CameraOutline" /></template>
              开启摄像头，开始筛查
            </n-button>
            <n-text depth="3">— 或 —</n-text>
            <n-button size="large" @click="enterUploadMode">
              <template #icon><n-icon :component="CloudUploadOutline" /></template>
              上传视频进行筛查
            </n-button>
            <n-text depth="3" style="font-size: 12px;">
              为每个动作分别上传视频，系统将逐帧分析并评分
            </n-text>
          </n-space>
        </div>
      </n-card>

      <!-- History -->
      <n-card :bordered="false" class="history-card" size="large">
        <template #header>
          <span class="section-title">历史筛查记录</span>
        </template>
        <n-empty v-if="records.length === 0" description="暂无筛查记录，完成一次筛查后在此查看" />
        <n-list v-else clickable>
          <n-list-item
            v-for="record in records.slice(0, 5)"
            :key="record.id"
            @click="router.push(`/fms/report/${record.id}`)"
          >
            <div class="history-item">
              <div class="history-left">
                <div class="history-date">{{ new Date(record.test_date).toLocaleDateString('zh-CN') }}</div>
                <n-tag :type="record.risk_level === 'low' ? 'success' : record.risk_level === 'medium' ? 'warning' : 'error'" size="tiny" round style="margin-top: 4px;">
                  {{ record.risk_level === 'low' ? '低风险' : record.risk_level === 'medium' ? '中风险' : record.risk_level === 'high' ? '高风险' : record.risk_level }}
                </n-tag>
              </div>
              <div class="history-right">
                <span class="score-num">{{ record.overall_score?.toFixed(1) }}</span>
                <span class="score-label">分</span>
                <n-button
                  text
                  type="error"
                  title="删除记录"
                  style="margin-left: 10px;"
                  @click.stop="deleteHistoryRecord(record)"
                >
                  <template #icon><n-icon :component="TrashOutline" size="17" /></template>
                </n-button>
                <n-icon :component="ChevronForwardOutline" size="18" color="#94a3b8" style="margin-left: 4px;" />
              </div>
            </div>
          </n-list-item>
        </n-list>
      </n-card>
    </template>

    <!-- ═══ Camera Mode ═══ -->
    <template v-if="mode === 'camera'">
      <n-card :bordered="false" class="main-card" size="large">
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <n-icon size="22" :component="CameraOutline" class="header-icon" style="color: #ef4444;" />
              <span class="header-title">FMS 实时筛查</span>
            </div>
            <n-button size="small" text @click="retry">
              <template #icon><n-icon :component="ArrowBackOutline" /></template>
              退出
            </n-button>
          </div>
        </template>

        <n-progress :percentage="Math.round(overallProgress)" style="margin-bottom: 16px;" />

        <!-- ═══ 动作学习区 ═══ -->
        <div
          v-if="(cameraPhase === 'preparing' || cameraPhase === 'countdown') && currentTest >= 0"
          id="demo-section"
          ref="demoSectionRef"
          class="demo-section"
        >
          <div class="section-kicker">动作学习区</div>
          <MovementDemo
            ref="movementDemoRef"
            :movement-name="FMS_TESTS[currentTest]?.name || ''"
            :instruction="testInstruction || FMS_TESTS[currentTest]?.instruction || ''"
            :media-srcs="FMS_MEDIA[currentTest] || []"
          />
          <div v-if="cameraPhase === 'preparing'" class="demo-action-area">
            <n-button type="primary" size="large" @click="startCountdown">
              <template #icon><n-icon :component="ArrowForwardOutline" /></template>
              准备好了，开始检测
            </n-button>
            <p class="demo-hint">观看示范后，点击按钮开始实时检测</p>
          </div>
        </div>

        <!-- ═══ 实时检测区 ═══ -->
        <div id="camera-section" class="camera-section">
          <!-- No person warning -->
          <div v-if="noPersonWarning" class="no-person-warning">
          <n-icon size="20" :component="WarningOutline" />
          <span>未检测到人体，请站在摄像头正前方，确保全身可见</span>
        </div>

        <!-- Video area -->
        <div class="video-container">
          <video
            ref="videoRef"
            autoplay
            playsinline
            muted
            class="video-element"
          />
          <canvas
            ref="overlayCanvasRef"
            class="overlay-canvas"
          />

          <!-- Countdown overlay -->
          <div v-if="cameraPhase === 'countdown'" class="countdown-overlay">
            <span class="countdown-num">{{ countdown }}</span>
          </div>

          <!-- Real-time guidance overlay -->
          <div v-if="cameraPhase !== 'completed' && guidance && cameraPhase !== 'countdown'" class="guidance-overlay">
            {{ guidance }}
          </div>

          <!-- Score overlay after completion -->
          <div v-if="showScoreOverlay && testScore !== null" class="score-overlay">
            <div class="score-overlay-content">
              <n-icon size="48" :component="TrophyOutline" class="score-trophy" />
              <h3 class="score-title">{{ FMS_TESTS[currentTest]?.name }}</h3>
              <div class="score-number" :class="{ good: testScore >= 70, normal: testScore >= 40 && testScore < 70, poor: testScore < 40 }">
                {{ testScore }} 分
              </div>
              <n-tag
                size="large"
                :type="testScore >= 70 ? 'success' : testScore >= 40 ? 'warning' : 'error'"
                class="score-tag"
              >
                {{ testScore >= 70 ? '良好' : testScore >= 40 ? '一般' : '需加强' }}
              </n-tag>
              <p v-if="testMessage" class="score-detail">{{ testMessage }}</p>
              <n-button
                v-if="currentTest < 4"
                type="primary"
                size="large"
                @click="advanceToNextTest"
              >
                <template #icon><n-icon :component="ArrowForwardOutline" /></template>
                进入下一个动作
              </n-button>
              <n-button
                v-else
                type="primary"
                size="large"
                @click="finishTests"
              >
                <template #icon><n-icon :component="TrophyOutline" /></template>
                查看最终结果
              </n-button>
            </div>
          </div>
        </div>
        <canvas ref="canvasRef" style="display: none;" />

        <!-- Control card -->
        <n-card size="small" style="margin-top: 16px;">
          <div class="control-row">
            <div class="control-left">
              <n-text strong v-if="currentTest >= 0 && currentTest < 5">
                第 {{ currentTest + 1 }} 项 / 共 5 项: {{ FMS_TESTS[currentTest]?.name }}
              </n-text>
              <n-text v-else>等待开始...</n-text>
            </div>
            <template v-if="currentTest >= 0">
              <n-button
                v-if="cameraPhase === 'running'"
                type="primary"
                size="small"
                @click="completeCurrentTest"
                style="margin-right: 8px;"
              >
                <template #icon><n-icon :component="CheckmarkCircleOutline" /></template>
                完成此动作
              </n-button>
              <n-button
                size="small"
                @click="skipTest"
                :disabled="cameraPhase === 'completed' || cameraPhase === 'skipped'"
              >
                <template #icon><n-icon :component="ArrowForwardOutline" /></template>
                跳过此项
              </n-button>
            </template>
          </div>

          <!-- Timer display for hold-based tests -->
          <div v-if="(currentTest === 0 || currentTest === 3) && cameraPhase === 'running'" class="timer-display">
            {{ String(Math.floor(testDuration / 60)).padStart(2, '0') }}:{{ String(Math.floor(testDuration % 60)).padStart(2, '0') }}
          </div>

          <div class="phase-tags" style="margin-top: 8px;">
            <n-text>{{ testMessage }}</n-text>
            <div style="margin-top: 4px;">
              <n-tag v-if="cameraPhase === 'preparing'" type="info" round size="small">查看示范，准备好后点击按钮</n-tag>
              <n-tag v-if="cameraPhase === 'countdown'" type="warning" round size="small">倒计时 {{ countdown }} 秒...</n-tag>
              <n-tag v-if="cameraPhase === 'running' && !noPersonWarning" type="success" round size="small">
                <template #icon><n-icon :component="CameraOutline" /></template>
                检测中...
              </n-tag>
              <n-tag v-if="cameraPhase === 'running' && noPersonWarning" type="error" round size="small">
                <template #icon><n-icon :component="WarningOutline" /></template>
                等待人体入框
              </n-tag>
              <n-tag v-if="cameraPhase === 'completed' && testScore !== null" type="success" round size="small">
                <template #icon><n-icon :component="CheckmarkCircleOutline" /></template>
                完成！得分: {{ testScore }}
              </n-tag>
              <n-tag v-if="cameraPhase === 'skipped'" type="default" round size="small">已跳过</n-tag>
            </div>
          </div>
        </n-card>

        <!-- Skipped: advance / finish -->
        <n-button
          v-if="cameraPhase === 'skipped' && currentTest < 4"
          type="primary" block style="margin-top: 16px;"
          @click="advanceToNextTest"
        >
          <template #icon><n-icon :component="ArrowForwardOutline" /></template>
          进入下一个动作
        </n-button>

        <n-button
          v-if="cameraPhase === 'skipped' && currentTest === 4"
          type="primary" block style="margin-top: 16px;"
          @click="ws?.readyState === WebSocket.OPEN ? finishTests() : buildFallbackResult()"
        >
          <template #icon><n-icon :component="TrophyOutline" /></template>
          查看结果
        </n-button>
        </div><!-- /camera-section -->
      </n-card>

      <!-- 查看示范小按钮（PiP 收起/关闭后） -->
      <n-button
        v-if="mode === 'camera' && (pipMinimized || pipClosed)"
        class="reopen-pip-btn"
        size="small"
        type="primary"
        round
        @click="reopenPip"
      >
        <template #icon><n-icon :component="EyeOutline" /></template>
        查看示范
      </n-button>

      <!-- 画中画示范视频 -->
      <PipDemoVideo
        ref="pipVideoRef"
        :src="pipMediaSrc"
        :visible="pipVisible"
        :current-time="pipCurrentTime"
        :muted="pipMuted"
        @close="onPipClose"
        @minimize="onPipMinimize"
        @update:muted="pipMuted = $event"
        @timeupdate="onPipTimeUpdate"
      />
    </template>

    <!-- ═══ Upload Mode ═══ -->
    <template v-if="mode === 'upload'">
      <n-card :bordered="false" class="main-card" size="large">
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <n-icon size="22" :component="CloudUploadOutline" class="header-icon" style="color: #8b5cf6;" />
              <span class="header-title">上传各动作视频</span>
            </div>
            <n-button size="small" text @click="mode = 'idle'; uploadedResults = {}">
              <template #icon><n-icon :component="ArrowBackOutline" /></template>
              返回
            </n-button>
          </div>
        </template>

        <p style="font-size: 13px; color: #64748b; margin-bottom: 16px;">
          请为以下5个FMS动作分别上传对应的视频。每个视频请只包含该动作的完整过程。
        </p>

        <input
          ref="fileInputRef"
          type="file"
          accept="video/mp4,video/avi,video/mov,video/webm"
          style="display: none;"
          @change="onFileSelected"
        />

        <n-list>
          <n-list-item v-for="test in FMS_TESTS" :key="test.id">
            <div class="upload-test-row">
              <div class="upload-test-info">
                <div class="upload-test-header">
                  <span class="test-num-small">{{ test.id + 1 }}</span>
                  <n-tag size="small">{{ test.name }}</n-tag>
                  <n-tag v-if="uploadedResults[test.id]" type="success" size="small">
                    评分: {{ uploadedResults[test.id].score }} 分
                  </n-tag>
                </div>
                <p class="upload-test-desc">{{ test.instruction }}</p>
                <a
                  v-if="uploadedResults[test.id]?.processed_video_url"
                  :href="uploadedResults[test.id].processed_video_url"
                  download
                  class="processed-video-link"
                >
                  📹 下载分析视频（用本地播放器打开）
                </a>
              </div>
              <div class="upload-test-action">
                <n-button
                  size="small"
                  :type="uploadedResults[test.id] ? 'default' : 'primary'"
                  :disabled="uploading || !!uploadedResults[test.id]"
                  @click="triggerFileUpload(test.id)"
                >
                  <template #icon>
                    <n-icon :component="uploadedResults[test.id] ? CheckmarkCircle : CloudUploadOutline" />
                  </template>
                  {{ uploadedResults[test.id] ? '已上传' : '上传视频' }}
                </n-button>
              </div>
            </div>
          </n-list-item>
        </n-list>

        <!-- Upload progress -->
        <div v-if="uploading && uploadingTestIndex !== null" class="upload-progress-card">
          <n-spin size="small" />
          <n-text style="margin-left: 8px;">{{ uploadStatus }}</n-text>
          <n-progress
            v-if="uploadProgress > 0 && uploadProgress < 100"
            :percentage="uploadProgress"
            style="max-width: 400px; margin: 8px auto 0;"
          />
        </div>

        <n-divider />

        <div style="margin-bottom: 16px; text-align: center;">
          <n-text strong>已上传: {{ Object.keys(uploadedResults).length }} / 5 项</n-text>
          <div v-if="Object.keys(uploadedResults).length > 0" style="margin-top: 8px;">
            <n-tag v-for="[key, res] in Object.entries(uploadedResults)" :key="key" type="success" style="margin: 4px;">
              {{ FMS_TESTS[Number(key)].name }}: {{ res.score }}分
            </n-tag>
          </div>
        </div>

        <n-button
          type="primary"
          size="large"
          block
          :disabled="Object.keys(uploadedResults).length === 0 || uploading"
          @click="handleCombineResults"
        >
          <template #icon><n-icon :component="TrophyOutline" /></template>
          生成综合报告
        </n-button>
      </n-card>
    </template>

    <!-- ═══ Result ═══ -->
    <template v-if="mode === 'done' && result">
      <n-card :bordered="false" class="main-card" size="large">
        <n-result
          status="success"
          title="FMS 筛查完成！"
          :description="`综合评分: ${result.overall_score} 分 | 风险等级: ${result.risk_level}`"
        >
          <template #footer>
            <n-space justify="center">
              <n-button type="primary" @click="viewReport">
                <template #icon><n-icon :component="TrophyOutline" /></template>
                查看详细报告
              </n-button>
              <n-button @click="retry">
                <template #icon><n-icon :component="RefreshOutline" /></template>
                重新筛查
              </n-button>
            </n-space>
          </template>
        </n-result>
      </n-card>
    </template>
  </div>
</template>

<style scoped>
.fms-page {
  max-width: 700px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.main-card,
.history-card {
  border-radius: 16px !important;
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
  color: #8b5cf6;
}

.header-title {
  font-size: 17px;
  font-weight: 600;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
}

/* ── Intro ── */
.intro-card {
  display: flex;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(59, 130, 246, 0.08) 100%);
  border-radius: 12px;
  margin-bottom: 20px;
}

.intro-icon {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.intro-title { font-size: 16px; font-weight: 600; margin: 0 0 6px 0; }
.intro-desc { font-size: 13px; color: #64748b; margin: 0; line-height: 1.6; }

/* ── Test Grid ── */
.test-grid { margin-bottom: 24px; }

.test-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  background: #f8fafc;
  border-radius: 10px;
  margin-bottom: 8px;
  transition: all 0.2s;
}

:deep(.dark) .test-item { background: rgba(255, 255, 255, 0.04); }

.test-num {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.test-info { flex: 1; min-width: 0; }
.test-name { font-size: 14px; font-weight: 600; margin-bottom: 2px; }
.test-desc { font-size: 12px; color: #64748b; }

/* ── Actions ── */
.action-buttons { text-align: center; padding: 8px 0; }

/* ── Camera Mode ── */
.demo-section {
  margin-bottom: 24px;
  padding: 24px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.05) 0%, rgba(59, 130, 246, 0.04) 100%);
  border-radius: 16px;
  border: 1px solid rgba(139, 92, 246, 0.1);
}

.section-kicker {
  display: inline-block;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  color: #6d5df6;
  margin-bottom: 12px;
  padding: 4px 10px;
  background: rgba(109, 93, 246, 0.08);
  border-radius: 999px;
}

.demo-action-area {
  text-align: center;
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.demo-hint {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

.camera-section {
  scroll-margin-top: 80px;
  padding-bottom: 40px;
}

.no-person-warning {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  background: rgba(255, 77, 79, 0.12);
  border: 1px solid rgba(255, 77, 79, 0.35);
  border-radius: 8px;
  margin-bottom: 8px;
  color: #ef4444;
  font-size: 14px;
  font-weight: 500;
}

.video-container {
  position: relative;
  width: 100%;
  background: #000;
  border-radius: 12px;
  overflow: hidden;
  min-height: 420px;
  max-height: 70vh;
  isolation: isolate;
}

.video-element {
  width: 100%;
  height: 100%;
  min-height: 420px;
  max-height: 70vh;
  object-fit: cover;
  border-radius: 12px;
  background: #000;
}

.overlay-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 8px;
  pointer-events: none;
  z-index: 10;
}

.guidance-overlay {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.75);
  color: #fff;
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 16px;
  font-weight: 500;
  white-space: nowrap;
  pointer-events: none;
  z-index: 20;
}

.countdown-overlay {
  position: absolute;
  inset: 0;
  z-index: 25;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.countdown-num {
  font-size: 80px;
  font-weight: 900;
  color: #fff;
  text-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
  animation: countdown-pulse 1s ease-in-out infinite;
}

@keyframes countdown-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: 0.8; }
}

.score-overlay {
  position: absolute;
  inset: 0;
  z-index: 30;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
}

.score-overlay-content {
  text-align: center;
  color: #fff;
  padding: 32px;
  max-width: 400px;
}

.score-trophy {
  color: #fbbf24;
  margin-bottom: 16px;
}

.score-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #fff;
}

.score-number {
  font-size: 56px;
  font-weight: 700;
  margin-bottom: 8px;
}

.score-number.good { color: #52c41a; }
.score-number.normal { color: #faad14; }
.score-number.poor { color: #f5222d; }

.score-tag {
  font-size: 14px;
  padding: 4px 16px;
  margin-bottom: 16px;
}

.score-detail {
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 24px;
}

.timer-display {
  text-align: center;
  margin: 8px 0;
  font-size: 32px;
  font-weight: 700;
  font-family: monospace;
  color: #8b5cf6;
}

.control-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.phase-tags {
  display: flex;
  flex-direction: column;
}

/* ── Upload Mode ── */
.upload-test-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: 12px;
}

.upload-test-info { flex: 1; min-width: 0; }

.upload-test-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.test-num-small {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
  color: white;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 12px;
  flex-shrink: 0;
}

.upload-test-desc {
  font-size: 12px;
  color: #64748b;
  margin: 0;
}

.processed-video-link {
  font-size: 12px;
  color: #1677ff;
  text-decoration: none;
}

.processed-video-link:hover {
  text-decoration: underline;
}

.upload-progress-card {
  text-align: center;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  margin-top: 8px;
}

/* ── History ── */
.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.history-left {
  display: flex;
  flex-direction: column;
  min-width: 80px;
}

.history-date {
  font-size: 13px;
  font-weight: 500;
  color: #334155;
}

.history-scores {
  flex: 1;
  display: flex;
  gap: 12px;
  justify-content: center;
  font-size: 12px;
  color: #64748b;
}

.history-dim {
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 4px;
}

.history-right {
  display: flex;
  align-items: center;
}

.score-num {
  font-size: 20px;
  font-weight: 700;
  color: #8b5cf6;
}

.score-label {
  font-size: 12px;
  color: #64748b;
  margin-left: 2px;
}

/* ── PiP reopen button ── */
.reopen-pip-btn {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 9998;
  box-shadow: 0 6px 18px rgba(109, 93, 246, 0.24);
}

/* ── Dark mode ── */
:deep(.dark) .demo-section {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(59, 130, 246, 0.06) 100%);
  border-color: rgba(139, 92, 246, 0.15);
}
:deep(.dark) .section-kicker {
  color: #a78bfa;
  background: rgba(167, 139, 250, 0.12);
}
:deep(.dark) .demo-hint { color: #94a3b8; }
:deep(.dark) .no-person-warning { background: rgba(255, 77, 79, 0.08); }
:deep(.dark) .timer-display { color: #a78bfa; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .fms-page {
    gap: 12px;
  }
  .demo-section {
    padding: 16px;
    margin-bottom: 16px;
  }
  .demo-action-area {
    margin-top: 16px;
    gap: 8px;
  }
  .camera-section {
    scroll-margin-top: 64px;
    padding-bottom: 24px;
  }
  .video-container,
  .video-element {
    min-height: 340px;
    max-height: 60vh;
  }
  .guidance-overlay {
    font-size: 14px;
    padding: 6px 16px;
  }
  .countdown-num {
    font-size: 60px;
  }
  .score-number {
    font-size: 42px;
  }
  .score-overlay-content {
    padding: 24px;
  }
  .timer-display {
    font-size: 26px;
  }
  .reopen-pip-btn {
    right: 12px;
    bottom: 12px;
  }
  .intro-card {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
}

@media (max-width: 480px) {
  .video-container,
  .video-element {
    min-height: 280px;
    max-height: 50vh;
  }
  .demo-section {
    padding: 12px;
  }
  .control-row {
    flex-wrap: wrap;
    gap: 8px;
  }
  .score-number {
    font-size: 36px;
  }
  .score-title {
    font-size: 16px;
  }
}

@media (min-width: 1200px) {
  .video-container,
  .video-element {
    min-height: 520px;
    max-height: 75vh;
  }
}
</style>
