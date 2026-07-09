<script setup lang="ts">
import { ref, onMounted, computed, h, watch } from 'vue'
import { useRouter } from 'vue-router'
import { prescriptionV2Api, assessmentApi, fmsApi } from '../services/api'
import type { PlanV2, AssessmentRecord, FMSRecord, ActionLibResponse } from '../types'
import {
  NCard, NButton, NSpace, NTag, NIcon, NTabs, NTabPane,
  NEmpty, NSpin, NSelect, NSwitch,
  NDescriptions, NDescriptionsItem, NDataTable,
  NPopconfirm, NInput, NText
} from 'naive-ui'
import {
  FlashOutline, RefreshOutline,
  FitnessOutline, AnalyticsOutline, SearchOutline,
  TrashOutline, CheckmarkCircleOutline, ChevronForwardOutline,
  HardwareChipOutline, TimeOutline, SparklesOutline
} from '@vicons/ionicons5'

const router = useRouter()

const activeTab = ref('prescription')
const generating = ref(false)
const recordsLoading = ref(false)

// ── Records ──
const assessments = ref<AssessmentRecord[]>([])
const fmsRecords = ref<FMSRecord[]>([])
const selectedAssessmentId = ref<number | null>(null)
const selectedFMSId = ref<number | null>(null)

// ── Generation ──
const trainingLevel = ref(1)
const forceLocal = ref(false)
const plan = ref<PlanV2 | null>(null)
const genMethod = ref('')
const plans = ref<PlanV2[]>([])

// ── Extended Generation Config ──
const trainingGoal = ref('comprehensive')
const trainingDuration = ref(15)
const trainingFrequency = ref(3)
const showGenerationAnimation = ref(false)
const generationStep = ref(0)
const generationSteps = [
  { icon: AnalyticsOutline, label: '能力分析', desc: '解析体态与FMS数据' },
  { icon: FitnessOutline, label: '动作匹配', desc: '匹配最佳训练动作' },
  { icon: FlashOutline, label: '处方生成', desc: 'AI 生成个性化方案' }
]

const goalOptions = [
  { label: '综合提升', value: 'comprehensive' },
  { label: '体态矫正', value: 'posture' },
  { label: '力量增强', value: 'strength' },
  { label: '柔韧恢复', value: 'flexibility' },
  { label: '减脂塑形', value: 'fatloss' }
]

const durationOptions = [
  { label: '10 分钟', value: 10 },
  { label: '15 分钟', value: 15 },
  { label: '20 分钟', value: 20 },
  { label: '25 分钟', value: 25 }
]

const frequencyOptions = [
  { label: '每周 2 次', value: 2 },
  { label: '每周 3 次', value: 3 },
  { label: '每周 4 次', value: 4 },
  { label: '每周 5 次', value: 5 }
]

// ── Action Library ──
const actionLib = ref<ActionLibResponse | null>(null)
const libLoading = ref(false)
const libSearch = ref('')

const levelOptions = [
  { label: '心血来潮', value: 1 },
  { label: '偶尔进行', value: 2 },
  { label: '渐入佳境', value: 3 },
  { label: '健身发烧友', value: 4 },
  { label: '肌肉掌控者', value: 5 }
]

function getRiskLabel(level: string) {
  const map: Record<string, string> = { low: '低风险', medium: '中风险', high: '高风险' }
  return map[level] || level
}

function getRiskColor(level: string) {
  const map: Record<string, string> = { low: '#10b981', medium: '#f59e0b', high: '#ef4444' }
  return map[level] || '#64748b'
}

// ── Load ──
function loadRecords() {
  recordsLoading.value = true
  Promise.all([
    assessmentApi.getRecords().catch(() => []),
    fmsApi.getRecords().catch(() => [])
  ]).then(([a, f]) => {
    assessments.value = a
    fmsRecords.value = f
  }).finally(() => { recordsLoading.value = false })
}

function loadPlans() {
  prescriptionV2Api.list()
    .then(r => { plans.value = r.plans || [] })
    .catch(() => {})
}

function loadActionLib() {
  libLoading.value = true
  prescriptionV2Api.getActions()
    .then(r => { actionLib.value = r })
    .catch(() => {})
    .finally(() => { libLoading.value = false })
}

// ── Generate ──
function handleGenerate() {
  if (!selectedAssessmentId.value && !selectedFMSId.value) {
    alert('请至少选择一项评估或筛查记录')
    return
  }
  showGenerationAnimation.value = true
  generationStep.value = 0
  generating.value = true

  const animate = (step: number) => {
    generationStep.value = step
    if (step < generationSteps.length) {
      setTimeout(() => animate(step + 1), 1200)
      return
    }
    prescriptionV2Api.generate({
      assessment_record_id: selectedAssessmentId.value || undefined,
      fms_record_id: selectedFMSId.value || undefined,
      training_level: trainingLevel.value,
      use_deepseek: !forceLocal.value,
        training_goal: trainingGoal.value,
        training_duration: trainingDuration.value,
        training_frequency: trainingFrequency.value,
    }).then(r => {
      plan.value = r.plan || null
      genMethod.value = r.generation_method || ''
      loadPlans()
    }).catch(() => {
      alert('生成失败')
    }).finally(() => {
      generating.value = false
      setTimeout(() => { showGenerationAnimation.value = false }, 500)
    })
  }
  animate(0)
}

function handleActivate(planId: number) {
  prescriptionV2Api.activate(planId)
    .then(() => { loadPlans() })
    .catch(() => { alert('激活失败') })
}

function handleDelete(planId: number) {
  prescriptionV2Api.delete(planId)
    .then(() => {
      if (plan.value?.id === planId) plan.value = null
      loadPlans()
    })
    .catch(() => { alert('删除失败') })
}

function goToPlanDetail(planId: number) {
  router.push(`/prescription-training/plan/${planId}`)
}

// ── Phase helpers ──
function getPhaseColor(phase: string) {
  const map: Record<string, string> = { warmup: '#3b82f6', main: '#ef4444', cooldown: '#10b981' }
  return map[phase] || '#64748b'
}

function getPhaseLabel(phase: string) {
  const map: Record<string, string> = { warmup: '热身', main: '主训练', cooldown: '冷身' }
  return map[phase] || phase
}

function getIntensityColor(intensity: string) {
  const map: Record<string, string> = { LOW: '#10b981', MEDIUM: '#f59e0b', HIGH: '#ef4444' }
  return map[intensity] || '#64748b'
}

function getIntensityType(intensity: string) {
  const map: Record<string, string> = { LOW: 'success', MEDIUM: 'warning', HIGH: 'error' }
  return map[intensity] || 'default'
}

function getPhaseType(phase: string) {
  const map: Record<string, string> = { warmup: 'info', main: 'error', cooldown: 'success' }
  return map[phase] || 'default'
}

const filteredLib = computed(() => {
  if (!actionLib.value) return []
  if (!libSearch.value) return actionLib.value.actions
  const q = libSearch.value.toLowerCase()
  return actionLib.value.actions.filter(a =>
    a.name.toLowerCase().includes(q) || a.family_name?.toLowerCase().includes(q)
  )
})

const selectedAssessment = computed(() =>
  assessments.value.find(a => a.id === selectedAssessmentId.value) || null
)
const selectedFMS = computed(() =>
  fmsRecords.value.find(f => f.id === selectedFMSId.value) || null
)

const latestAssessment = computed(() => assessments.value[0] || null)
const latestFMS = computed(() => fmsRecords.value[0] || null)

const stepperItems = [
  { title: 'FMS筛查', desc: '选择筛查记录' },
  { title: '体态评估', desc: '选择评估记录' },
  { title: 'AI分析', desc: '智能解析数据' },
  { title: '训练方案', desc: '生成个性化计划' }
]

const currentStepperStep = computed(() => {
  if (plan.value) return 4
  if (selectedAssessmentId.value || selectedFMSId.value) return 3
  return 1
})

const estimatedGenTime = computed(() => {
  const base = forceLocal.value ? 8 : 15
  const factor = trainingDuration.value / 30
  return Math.round(base * factor)
})

const outputModules = [
  { label: '热身激活', desc: '动态拉伸与关节激活', color: '#3b82f6' },
  { label: '主训练', desc: '针对性动作组合', color: '#ef4444' },
  { label: '拉伸放松', desc: '静态拉伸与恢复', color: '#10b981' },
  { label: '风险提示', desc: '注意事项与禁忌', color: '#f59e0b' }
]

function getTrend(score: number) {
  if (score >= 85) return { label: '优秀', color: '#10b981' }
  if (score >= 70) return { label: '良好', color: '#3b82f6' }
  if (score >= 60) return { label: '一般', color: '#f59e0b' }
  return { label: '需关注', color: '#ef4444' }
}

function getScoreCircumference(score: number) {
  const r = 18
  const c = 2 * Math.PI * r
  return `${(score / 100) * c} ${c}`
}

// ── Columns ──
const historyColumns = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '名称', key: 'plan_name', width: 180 },
  {
    title: '方式', key: 'generation_method', width: 90,
    render: (row: any) => row.generation_method === 'deepseek' ? 'DeepSeek AI' : '本地引擎'
  },
  {
    title: '状态', key: 'status', width: 70,
    render: (row: any) => row.status === 'active' ? '激活' : row.status
  },
  { title: '动作', key: 'items', width: 60, render: (row: any) => row.items?.length || 0 },
  {
    title: '创建时间', key: 'created_at', width: 130,
    render: (row: any) => row.created_at?.slice(0, 16) || '-'
  },
  {
    title: '操作', key: 'actions', width: 150,
    render: (row: any) => {
      const btns = [
        h(NButton, { size: 'tiny', text: true, onClick: () => setPlanFromHistory(row) }, { default: () => '查看' })
      ]
      if (row.status !== 'active') {
        btns.push(h(NButton, { size: 'tiny', text: true, onClick: () => handleActivate(row.id) }, { default: () => '激活' }))
      }
      btns.push(h(NPopconfirm, { onPositiveClick: () => handleDelete(row.id) }, {
        trigger: () => h(NButton, { size: 'tiny', text: true, type: 'error' }, { default: () => '删除' }),
        default: () => '确定要删除此训练计划吗？'
      }))
      return h(NSpace, { size: 0 }, { default: () => btns })
    }
  }
]

function setPlanFromHistory(row: PlanV2) {
  plan.value = row
}

onMounted(() => {
  loadRecords()
  loadPlans()
})

watch(activeTab, (tab) => {
  if (tab === 'actions' && !actionLib.value) loadActionLib()
})
</script>

<script lang="ts">
export default { name: 'PrescriptionTrainingView' }
</script>

<template>
  <div class="prescription-page">

    <!-- ═══ Background Decor ═══ -->
    <div class="bg-glow bg-glow-1"></div>
    <div class="bg-glow bg-glow-2"></div>

    <!-- ═══ Hero Banner ═══ -->
    <div class="hero-banner">
      <!-- AI decorative layers -->
      <div class="hero-mesh"></div>
      <div class="hero-skeleton">
        <svg viewBox="0 0 200 320" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="100" cy="28" r="14" stroke="currentColor" stroke-width="1.2" opacity="0.35"/>
          <line x1="100" y1="42" x2="100" y2="110" stroke="currentColor" stroke-width="1.2" opacity="0.35"/>
          <line x1="100" y1="60" x2="58" y2="90" stroke="currentColor" stroke-width="1.2" opacity="0.3"/>
          <line x1="100" y1="60" x2="142" y2="90" stroke="currentColor" stroke-width="1.2" opacity="0.3"/>
          <line x1="100" y1="110" x2="62" y2="170" stroke="currentColor" stroke-width="1.2" opacity="0.3"/>
          <line x1="100" y1="110" x2="138" y2="170" stroke="currentColor" stroke-width="1.2" opacity="0.3"/>
          <line x1="62" y1="170" x2="48" y2="250" stroke="currentColor" stroke-width="1.2" opacity="0.3"/>
          <line x1="138" y1="170" x2="152" y2="250" stroke="currentColor" stroke-width="1.2" opacity="0.3"/>
          <circle cx="58" cy="90" r="5" fill="currentColor" opacity="0.25"/>
          <circle cx="142" cy="90" r="5" fill="currentColor" opacity="0.25"/>
          <circle cx="62" cy="170" r="5" fill="currentColor" opacity="0.25"/>
          <circle cx="138" cy="170" r="5" fill="currentColor" opacity="0.25"/>
        </svg>
      </div>
      <div class="hero-neural">
        <svg viewBox="0 0 400 200" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="40" cy="100" r="5" fill="currentColor" opacity="0.4"/>
          <circle cx="140" cy="50" r="6" fill="currentColor" opacity="0.35"/>
          <circle cx="140" cy="150" r="6" fill="currentColor" opacity="0.35"/>
          <circle cx="260" cy="80" r="7" fill="currentColor" opacity="0.3"/>
          <circle cx="260" cy="140" r="7" fill="currentColor" opacity="0.3"/>
          <circle cx="360" cy="100" r="5" fill="currentColor" opacity="0.4"/>
          <line x1="45" y1="100" x2="134" y2="54" stroke="currentColor" stroke-width="0.8" opacity="0.25"/>
          <line x1="45" y1="100" x2="134" y2="146" stroke="currentColor" stroke-width="0.8" opacity="0.25"/>
          <line x1="146" y1="50" x2="253" y2="77" stroke="currentColor" stroke-width="0.8" opacity="0.2"/>
          <line x1="146" y1="150" x2="253" y2="123" stroke="currentColor" stroke-width="0.8" opacity="0.2"/>
          <line x1="267" y1="80" x2="355" y2="100" stroke="currentColor" stroke-width="0.8" opacity="0.2"/>
          <line x1="267" y1="140" x2="355" y2="100" stroke="currentColor" stroke-width="0.8" opacity="0.2"/>
        </svg>
      </div>
      <div class="hero-radar">
        <svg viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
          <polygon points="60,10 110,45 95,105 25,105 10,45" stroke="currentColor" stroke-width="0.6" opacity="0.25"/>
          <polygon points="60,28 92,52 82,88 38,88 28,52" stroke="currentColor" stroke-width="0.6" opacity="0.2"/>
          <polygon points="60,46 74,58 69,71 51,71 46,58" fill="currentColor" opacity="0.18"/>
          <line x1="60" y1="10" x2="60" y2="105" stroke="currentColor" stroke-width="0.5" opacity="0.15"/>
          <line x1="10" y1="45" x2="110" y2="45" stroke="currentColor" stroke-width="0.5" opacity="0.15"/>
          <line x1="25" y1="105" x2="95" y2="10" stroke="currentColor" stroke-width="0.5" opacity="0.15"/>
        </svg>
      </div>
      <div class="hero-datastream">
        <div class="data-bar" style="--h:24px;--d:0s"></div>
        <div class="data-bar" style="--h:40px;--d:0.3s"></div>
        <div class="data-bar" style="--h:18px;--d:0.6s"></div>
        <div class="data-bar" style="--h:32px;--d:0.9s"></div>
        <div class="data-bar" style="--h:28px;--d:1.2s"></div>
        <div class="data-bar" style="--h:14px;--d:1.5s"></div>
      </div>
      <div class="hero-particles">
        <span v-for="n in 18" :key="n" class="h-particle" :style="`--i:${n}`"></span>
      </div>

      <div class="hero-inner">
        <div class="hero-left">
          <div class="hero-badge">
            <n-icon size="16" :component="SparklesOutline" />
            <span>AI 智能训练方案</span>
          </div>
          <h1 class="hero-title">基于 FMS 筛查与体态评估，<br/>AI 自动生成个性化训练方案</h1>
          <div class="hero-tags">
            <span class="hero-tag"><n-icon size="12" :component="CheckmarkCircleOutline" /> 智能分析</span>
            <span class="hero-tag"><n-icon size="12" :component="CheckmarkCircleOutline" /> 动态训练</span>
            <span class="hero-tag"><n-icon size="12" :component="CheckmarkCircleOutline" /> 持续优化</span>
          </div>
        </div>
        <div class="hero-right">
          <div class="ai-status-card glow">
            <div class="ai-status-header">
              <span class="ai-status-dot"></span>
              <span class="ai-status-title">AI 引擎状态</span>
            </div>
            <div class="ai-status-row">
              <n-icon size="18" :component="HardwareChipOutline" />
              <span class="ai-status-label">当前模型</span>
              <span class="ai-status-value">{{ forceLocal ? '本地引擎' : 'DeepSeek' }}</span>
            </div>
            <div class="ai-status-row">
              <n-icon size="18" :component="FitnessOutline" />
              <span class="ai-status-label">训练目标</span>
              <span class="ai-status-value">{{ goalOptions.find(g => g.value === trainingGoal)?.label || '-' }}</span>
            </div>
            <div class="ai-status-row">
              <n-icon size="18" :component="TimeOutline" />
              <span class="ai-status-label">预计生成</span>
              <span class="ai-status-value">约 {{ estimatedGenTime }} 秒</span>
            </div>
            <div class="ai-status-row">
              <n-icon size="18" :component="FlashOutline" />
              <span class="ai-status-label">训练强度</span>
              <span class="ai-status-value">{{ levelOptions.find(l => l.value === trainingLevel)?.label || '-' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ Generating Progress Bar ═══ -->
    <div v-if="generating" class="gen-progress">
      <div class="gen-progress-bar"></div>
    </div>

    <!-- ═══ Tabs ═══ -->
    <n-tabs v-model:value="activeTab" type="line" size="large" class="prescription-tabs">
      <!-- ═══════ Tab 1: 训练方案生成 ═══════ -->
      <n-tab-pane name="prescription" tab="训练方案生成">
        <div class="tab-content">

          <!-- Assessment Record Cards -->
          <div class="record-cards">
            <!-- Posture Assessment Card -->
            <div class="record-card">
              <div class="record-card-top">
                <div class="record-card-icon" style="background:rgba(6,182,212,0.12);color:#06b6d4">
                  <n-icon size="22" :component="FitnessOutline" />
                </div>
                <div class="record-card-header">
                  <span class="record-card-title">体态评估</span>
                  <n-tag v-if="latestAssessment && !selectedAssessmentId" size="tiny" round :bordered="false" type="info">最近一次</n-tag>
                </div>
              </div>
              <div class="record-card-body" v-if="selectedAssessment || latestAssessment">
                <div class="record-main">
                  <div class="score-ring" :style="{ '--score-color': getRiskColor((selectedAssessment || latestAssessment).risk_level) }">
                    <svg viewBox="0 0 44 44" class="score-ring-svg">
                      <circle cx="22" cy="22" r="18" stroke="#e2e8f0" stroke-width="4" fill="none"/>
                      <circle cx="22" cy="22" r="18" stroke="var(--score-color)" stroke-width="4" fill="none" stroke-linecap="round"
                        :stroke-dasharray="getScoreCircumference((selectedAssessment || latestAssessment).overall_score)"
                        transform="rotate(-90 22 22)"/>
                    </svg>
                    <div class="score-value">
                      <span class="sv-num">{{ (selectedAssessment || latestAssessment).overall_score }}</span>
                      <span class="sv-label">综合评分</span>
                    </div>
                  </div>
                  <div class="record-stats">
                    <div class="rs-item">
                      <span class="rs-label">风险等级</span>
                      <span class="rs-value" :style="{ color: getRiskColor((selectedAssessment || latestAssessment).risk_level) }">
                        {{ getRiskLabel((selectedAssessment || latestAssessment).risk_level) }}
                      </span>
                    </div>
                    <div class="rs-item">
                      <span class="rs-label">异常问题</span>
                      <span class="rs-value">{{ (selectedAssessment || latestAssessment).posture_problems?.length || 0 }} 项</span>
                    </div>
                    <div class="rs-item">
                      <span class="rs-label">检测日期</span>
                      <span class="rs-value">{{ (selectedAssessment || latestAssessment).test_date?.slice(0, 10) || '-' }}</span>
                    </div>
                  </div>
                </div>
                <div class="record-trend">
                  <span class="rt-label">评估趋势</span>
                  <span class="rt-badge" :style="{ background: getTrend((selectedAssessment || latestAssessment).overall_score).color + '15', color: getTrend((selectedAssessment || latestAssessment).overall_score).color }">
                    {{ getTrend((selectedAssessment || latestAssessment).overall_score).label }}
                  </span>
                </div>
              </div>
              <div v-else class="record-card-empty">
                <n-empty description="暂无体态评估记录" size="small" />
              </div>
              <div class="record-card-select">
                <n-select
                  v-model:value="selectedAssessmentId"
                  :options="assessments.map(a => ({
                    label: `#${a.id} | ${a.test_date?.slice(0, 10)} | 总分${a.overall_score} | ${getRiskLabel(a.risk_level)}`,
                    value: a.id
                  }))"
                  placeholder="选择评估记录"
                  clearable
                />
              </div>
            </div>

            <!-- FMS Record Card -->
            <div class="record-card">
              <div class="record-card-top">
                <div class="record-card-icon" style="background:rgba(139,92,246,0.12);color:#8b5cf6">
                  <n-icon size="22" :component="AnalyticsOutline" />
                </div>
                <div class="record-card-header">
                  <span class="record-card-title">FMS 筛查</span>
                  <n-tag v-if="latestFMS && !selectedFMSId" size="tiny" round :bordered="false" type="info">最近一次</n-tag>
                </div>
              </div>
              <div class="record-card-body" v-if="selectedFMS || latestFMS">
                <div class="record-main">
                  <div class="score-ring" :style="{ '--score-color': getRiskColor((selectedFMS || latestFMS).risk_level) }">
                    <svg viewBox="0 0 44 44" class="score-ring-svg">
                      <circle cx="22" cy="22" r="18" stroke="#e2e8f0" stroke-width="4" fill="none"/>
                      <circle cx="22" cy="22" r="18" stroke="var(--score-color)" stroke-width="4" fill="none" stroke-linecap="round"
                        :stroke-dasharray="getScoreCircumference((selectedFMS || latestFMS).overall_score)"
                        transform="rotate(-90 22 22)"/>
                    </svg>
                    <div class="score-value">
                      <span class="sv-num">{{ (selectedFMS || latestFMS).overall_score }}</span>
                      <span class="sv-label">综合评分</span>
                    </div>
                  </div>
                  <div class="record-stats">
                    <div class="rs-item">
                      <span class="rs-label">风险等级</span>
                      <span class="rs-value" :style="{ color: getRiskColor((selectedFMS || latestFMS).risk_level) }">
                        {{ getRiskLabel((selectedFMS || latestFMS).risk_level) }}
                      </span>
                    </div>
                    <div class="rs-item">
                      <span class="rs-label">问题标签</span>
                      <span class="rs-value">{{ (selectedFMS || latestFMS).problem_tags?.length || 0 }} 项</span>
                    </div>
                    <div class="rs-item">
                      <span class="rs-label">检测日期</span>
                      <span class="rs-value">{{ (selectedFMS || latestFMS).test_date?.slice(0, 10) || '-' }}</span>
                    </div>
                  </div>
                </div>
                <div class="record-trend">
                  <span class="rt-label">筛查趋势</span>
                  <span class="rt-badge" :style="{ background: getTrend((selectedFMS || latestFMS).overall_score).color + '15', color: getTrend((selectedFMS || latestFMS).overall_score).color }">
                    {{ getTrend((selectedFMS || latestFMS).overall_score).label }}
                  </span>
                </div>
              </div>
              <div v-else class="record-card-empty">
                <n-empty description="暂无 FMS 筛查记录" size="small" />
              </div>
              <div class="record-card-select">
                <n-select
                  v-model:value="selectedFMSId"
                  :options="fmsRecords.map(f => ({
                    label: `#${f.id} | ${f.test_date?.slice(0, 10)} | 总分${f.overall_score} | ${getRiskLabel(f.risk_level)}`,
                    value: f.id
                  }))"
                  placeholder="选择FMS记录"
                  clearable
                />
              </div>
            </div>
          </div>

          <!-- Generation Config -->
          <div class="panel-card gen-config-card">
            <div class="panel-title-row">
              <span class="panel-section-title">方案生成配置</span>
            </div>
            <div class="gen-config-grid">
              <div class="gen-field">
                <label class="gen-label">训练目标</label>
                <n-select v-model:value="trainingGoal" :options="goalOptions" size="large" />
              </div>
              <div class="gen-field">
                <label class="gen-label">训练者类型</label>
                <n-select v-model:value="trainingLevel" :options="levelOptions" size="large" />
              </div>
              <div class="gen-field">
                <label class="gen-label">单次时长</label>
                <n-select v-model:value="trainingDuration" :options="durationOptions" size="large" />
              </div>
              <div class="gen-field">
                <label class="gen-label">每周频率</label>
                <n-select v-model:value="trainingFrequency" :options="frequencyOptions" size="large" />
              </div>
              <div class="gen-field gen-switch-field">
                <div class="gen-switch-wrap">
                  <div>
                    <label class="gen-label">本地引擎模式</label>
                    <p class="gen-hint">开启后优先调用本地 AI 模型，响应更快</p>
                  </div>
                  <n-switch v-model:value="forceLocal" size="large" />
                </div>
              </div>
            </div>
          </div>

          <!-- Generate Action Card -->
          <div class="panel-card generate-action-card">
            <div class="ga-left">
              <div class="ga-title">
                <n-icon size="22" :component="FlashOutline" />
                <span>生成 AI 训练方案</span>
              </div>
              <div class="ga-output-modules">
                <div v-for="mod in outputModules" :key="mod.label" class="ga-module" :style="{ '--m-color': mod.color }">
                  <span class="ga-module-dot"></span>
                  <div class="ga-module-info">
                    <span class="ga-module-label">{{ mod.label }}</span>
                    <span class="ga-module-desc">{{ mod.desc }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="ga-right">
              <div class="ga-meta">
                <span class="ga-meta-label">预计生成时间</span>
                <span class="ga-meta-value">{{ estimatedGenTime }} 秒</span>
              </div>
              <n-button
                class="generate-btn"
                size="large"
                :loading="generating"
                :disabled="generating"
                @click="handleGenerate"
              >
                <template #icon>
                  <n-icon v-if="!generating" :component="SparklesOutline" />
                </template>
                <span v-if="!generating">生成 AI 训练方案</span>
                <span v-else>AI 正在分析……</span>
              </n-button>
            </div>
          </div>

          <!-- Generated Plan -->
          <div v-if="plan" class="panel-card">
            <div class="panel-title-row">
              <span class="panel-section-title">{{ plan.plan_name }}</span>
              <n-space>
                <n-tag :type="genMethod === 'deepseek' ? 'info' : 'warning'" size="small" round :bordered="false">
                  {{ genMethod === 'deepseek' ? 'DeepSeek AI' : '本地引擎' }}
                </n-tag>
                <n-tag :type="plan.status === 'active' ? 'success' : 'default'" size="small" round :bordered="false">
                  {{ plan.status === 'active' ? '激活' : plan.status }}
                </n-tag>
              </n-space>
            </div>

            <div class="custom-steps" style="margin-bottom: 16px;">
              <div class="custom-step done">
                <div class="step-dot"></div>
                <span class="step-label">热身</span>
              </div>
              <div class="step-line"></div>
              <div class="custom-step active">
                <div class="step-dot"></div>
                <span class="step-label">主训练</span>
              </div>
              <div class="step-line"></div>
              <div class="custom-step">
                <div class="step-dot"></div>
                <span class="step-label">冷身</span>
              </div>
            </div>

            <n-card
              v-for="phase in ['warmup', 'main', 'cooldown']"
              v-show="(plan.items || []).filter(i => i.phase === phase).length > 0"
              :key="phase"
              size="small"
              style="margin-bottom: 8px;"
              :bordered="false"
            >
              <template #header>
                <n-tag :type="getPhaseType(phase)" round size="small" style="font-size: 13px;">
                  {{ getPhaseLabel(phase) }}
                </n-tag>
              </template>
              <div
                v-for="item in (plan.items || []).filter(i => i.phase === phase)"
                :key="item.id"
                style="margin-bottom: 8px;"
              >
                <n-space align="center">
                  <span style="font-weight: 600;">{{ item.order_index }}. {{ item.action_name }}</span>
                  <n-tag size="tiny">{{ item.sets }} 组 x {{ item.reps }} 次</n-tag>
                  <n-tag v-if="item.intensity" size="tiny" :type="getIntensityType(item.intensity)">
                    {{ item.intensity }}
                  </n-tag>
                  <n-tag v-if="item.alternative" size="tiny" type="warning">替代</n-tag>
                </n-space>
                <div style="font-size: 12px; color: #64748b; margin-top: 2px;">
                  {{ item.duration_seconds }}s | 难度: {{ '⭐'.repeat(item.difficulty || 1) }}
                </div>
                <div v-if="item.notes" style="font-size: 12px; color: #94a3b8;">
                  备注: {{ item.notes }}
                </div>
              </div>
            </n-card>

            <n-descriptions :column="4" bordered size="small" style="margin-top: 16px;">
              <n-descriptions-item label="动作总数">{{ plan.items?.length || 0 }}</n-descriptions-item>
              <n-descriptions-item label="总组数">{{ plan.items?.reduce((s, i) => s + i.sets, 0) || 0 }}</n-descriptions-item>
              <n-descriptions-item label="总次数">{{ plan.items?.reduce((s, i) => s + i.sets * i.reps, 0) || 0 }}</n-descriptions-item>
              <n-descriptions-item label="总时长">{{ ((plan.items?.reduce((s, i) => s + i.sets * i.duration_seconds, 0) || 0) / 60).toFixed(1) }} 分钟</n-descriptions-item>
            </n-descriptions>

            <div style="margin-top: 12px; text-align: right;">
              <n-button size="small" @click="goToPlanDetail(plan.id)">查看详情</n-button>
            </div>
          </div>
        </div>
      </n-tab-pane>

      <!-- ═══════ Tab 2: 历史计划训练 ═══════ -->
      <n-tab-pane name="history" :tab="`历史计划训练 (${plans.length})`">
        <div class="tab-content">
          <div v-if="plans.length === 0" class="history-empty-wrap">
            <div class="history-empty-circle">
              <n-icon size="44" :component="FitnessOutline" />
            </div>
            <p class="history-empty-title">暂无训练计划</p>
            <p class="history-empty-desc">生成 AI 训练方案后，你的历史计划将在这里展示</p>
            <n-button type="primary" size="medium" @click="activeTab = 'prescription'">
              去生成训练方案
            </n-button>
          </div>

          <div v-else class="history-cards">
            <div
              v-for="item in plans"
              :key="item.id"
              class="history-plan-card"
            >
              <div class="hpc-top">
                <div class="hpc-left">
                  <div class="hpc-icon" :style="{ background: (item.generation_method === 'deepseek' ? '#8b5cf6' : '#3b82f6') + '15', color: item.generation_method === 'deepseek' ? '#8b5cf6' : '#3b82f6' }">
                    <n-icon size="22" :component="FlashOutline" />
                  </div>
                  <div class="hpc-info">
                    <span class="hpc-name">{{ item.plan_name || `计划 #${item.id}` }}</span>
                    <span class="hpc-meta">
                      {{ item.generation_method === 'deepseek' ? 'DeepSeek AI 生成' : '本地引擎生成' }}
                      · {{ item.created_at?.slice(0, 16) || '-' }}
                    </span>
                  </div>
                </div>
                <div class="hpc-right">
                  <n-tag
                    :type="item.status === 'active' ? 'success' : item.status === 'completed' ? 'info' : 'default'"
                    round
                    size="small"
                    :bordered="false"
                  >
                    {{ item.status === 'active' ? '进行中' : item.status === 'completed' ? '已完成' : item.status === 'draft' ? '草稿' : item.status }}
                  </n-tag>
                </div>
              </div>

              <div class="hpc-phases">
                <div
                  v-for="phase in ['warmup', 'main', 'cooldown']"
                  :key="phase"
                  class="hpc-phase"
                  v-show="(item.items || []).filter((i: any) => i.phase === phase).length > 0"
                >
                  <span class="hpc-phase-dot" :style="{ background: getPhaseColor(phase) }" />
                  <span class="hpc-phase-label">{{ getPhaseLabel(phase) }}</span>
                  <span class="hpc-phase-count">{{ (item.items || []).filter((i: any) => i.phase === phase).length }} 个动作</span>
                </div>
              </div>

              <div class="hpc-stats">
                <div class="hpc-stat">
                  <span class="hpc-stat-value">{{ item.items?.length || 0 }}</span>
                  <span class="hpc-stat-label">动作总数</span>
                </div>
                <div class="hpc-stat">
                  <span class="hpc-stat-value">{{ item.items?.reduce((s: number, i: any) => s + i.sets, 0) || 0 }}</span>
                  <span class="hpc-stat-label">总组数</span>
                </div>
                <div class="hpc-stat">
                  <span class="hpc-stat-value">{{ ((item.items?.reduce((s: number, i: any) => s + i.sets * i.duration_seconds, 0) || 0) / 60).toFixed(0) }}</span>
                  <span class="hpc-stat-label">总时长(分)</span>
                </div>
                <div class="hpc-stat">
                  <span class="hpc-stat-value">{{ item.plan_meta?.training_config?.user_level_label || 'Lv.' + (item.plan_meta?.training_config?.user_level || '?') }}</span>
                  <span class="hpc-stat-label">训练水平</span>
                </div>
              </div>

              <div class="hpc-actions">
                <n-button size="small" @click="goToPlanDetail(item.id)">
                  查看详情
                </n-button>
                <n-button
                  v-if="item.status !== 'active'"
                  size="small"
                  type="primary"
                  ghost
                  @click="handleActivate(item.id)"
                >
                  激活计划
                </n-button>
                <n-popconfirm @positive-click="() => handleDelete(item.id)">
                  <template #trigger>
                    <n-button size="small" type="error" ghost>
                      <template #icon><n-icon size="14" :component="TrashOutline" /></template>
                    </n-button>
                  </template>
                  确定要删除此训练计划吗？
                </n-popconfirm>
              </div>
            </div>
          </div>
        </div>
      </n-tab-pane>

      <!-- ═══════ Tab 3: 动作库 ═══════ -->
      <n-tab-pane name="actions" :tab="`动作库 (${actionLib?.total || 0})`">
        <div class="tab-content">
          <div class="panel-card">
            <div class="panel-title-row">
              <span class="panel-section-title">标准动作库</span>
              <n-button size="small" :loading="libLoading" @click="loadActionLib" class="refresh-btn">
                <template #icon><n-icon :component="RefreshOutline" /></template>
                加载
              </n-button>
            </div>

            <template v-if="!actionLib">
              <n-empty description="点击「加载」获取标准动作列表" style="padding: 32px 0;" />
            </template>

            <template v-else>
              <div class="lib-header">
                <n-input
                  v-model:value="libSearch"
                  placeholder="搜索动作名称或家族"
                  clearable
                  style="width: 280px;"
                >
                  <template #prefix><n-icon :component="SearchOutline" /></template>
                </n-input>
                <span class="lib-count">
                  共 {{ actionLib.total }} 个动作，{{ actionLib.families?.length || 0 }} 个家族
                </span>
              </div>

              <div class="action-cards">
                <div
                  v-for="action in filteredLib"
                  :key="action.action_id || action.name"
                  class="action-card"
                >
                  <div class="action-card-top">
                    <div class="action-card-icon" :style="{ background: getIntensityColor(action.intensity || 'LOW') + '15', color: getIntensityColor(action.intensity || 'LOW') }">
                      <n-icon size="20" :component="FitnessOutline" />
                    </div>
                    <div class="action-card-info">
                      <span class="action-card-name">{{ action.name }}</span>
                      <span class="action-card-family">{{ action.family_name || '未分类' }}</span>
                    </div>
                  </div>
                  <div class="action-card-tags">
                    <n-tag size="tiny" round :bordered="false" type="info">{{ action.category || '-' }}</n-tag>
                    <n-tag size="tiny" round :bordered="false" :type="getIntensityType(action.intensity || 'LOW')">
                      {{ action.intensity || '-' }}
                    </n-tag>
                    <n-tag size="tiny" round :bordered="false" type="default">
                      {{ '⭐'.repeat(action.difficulty || 1) }}
                    </n-tag>
                    <n-tag size="tiny" round :bordered="false" type="default">
                      {{ (action.target_muscles || []).slice(0, 2).join('、') || '-' }}
                    </n-tag>
                  </div>
                </div>
                <n-empty v-if="filteredLib.length === 0 && libSearch" description="未找到匹配的动作" style="padding: 24px 0;" />
              </div>
            </template>
          </div>
        </div>
      </n-tab-pane>
    </n-tabs>

    <!-- ═══ AI Generation Animation Overlay ═══ -->
    <transition name="fade-scale">
      <div v-if="showGenerationAnimation" class="gen-animation-overlay">
        <div class="gen-animation-backdrop"></div>
        <div class="gen-animation-card">
          <div class="gen-animation-pulse">
            <div class="pulse-ring"></div>
            <div class="pulse-core">
              <n-icon size="36" :component="HardwareChipOutline" />
            </div>
          </div>
          <h3 class="gen-animation-title">AI 正在生成训练方案</h3>
          <div class="gen-animation-steps">
            <div
              v-for="(s, idx) in generationSteps"
              :key="idx"
              class="gen-animation-step"
              :class="{ active: generationStep === idx, done: generationStep > idx }"
            >
              <div class="gas-icon">
                <n-icon size="18" :component="s.icon" />
              </div>
              <div class="gas-info">
                <span class="gas-label">{{ s.label }}</span>
                <span class="gas-desc">{{ s.desc }}</span>
              </div>
            </div>
          </div>
          <div class="gen-animation-progress">
            <div class="gen-animation-progress-bar" :style="{ width: ((generationStep + 1) / generationSteps.length) * 100 + '%' }"></div>
          </div>
        </div>
      </div>
    </transition>

    <!-- ═══ Side Decorative Illustrations ═══ -->
    <div class="side-illustration side-left" aria-hidden="true">
      <div class="si-layer si-skeleton">
        <svg viewBox="0 0 120 200" fill="none"><circle cx="60" cy="20" r="10" stroke="currentColor" stroke-width="1" opacity="0.12"/><line x1="60" y1="30" x2="60" y2="70" stroke="currentColor" stroke-width="1" opacity="0.1"/><line x1="60" y1="40" x2="35" y2="60" stroke="currentColor" stroke-width="1" opacity="0.1"/><line x1="60" y1="40" x2="85" y2="60" stroke="currentColor" stroke-width="1" opacity="0.1"/><line x1="60" y1="70" x2="38" y2="110" stroke="currentColor" stroke-width="1" opacity="0.1"/><line x1="60" y1="70" x2="82" y2="110" stroke="currentColor" stroke-width="1" opacity="0.1"/></svg>
      </div>
      <div class="si-layer si-equipment">
        <svg viewBox="0 0 120 200" fill="none"><rect x="40" y="20" width="40" height="8" rx="4" stroke="currentColor" stroke-width="1" opacity="0.1"/><rect x="48" y="40" width="24" height="60" rx="4" stroke="currentColor" stroke-width="1" opacity="0.1"/><circle cx="60" cy="120" r="16" stroke="currentColor" stroke-width="1" opacity="0.1"/></svg>
      </div>
      <div class="si-layer si-pose">
        <svg viewBox="0 0 120 200" fill="none"><circle cx="60" cy="30" r="12" stroke="currentColor" stroke-width="1.2" opacity="0.12"/><path d="M60 42 L60 95 L45 130 M60 65 L85 85 M60 95 L75 130" stroke="currentColor" stroke-width="1.2" opacity="0.1" stroke-linecap="round"/></svg>
      </div>
      <div class="si-layer si-tree">
        <svg viewBox="0 0 120 200" fill="none"><path d="M60 180 L60 120" stroke="currentColor" stroke-width="2" opacity="0.12"/><path d="M60 150 Q30 120 40 90 Q60 110 80 90 Q90 120 60 150" fill="currentColor" opacity="0.08"/><path d="M60 120 Q40 90 50 60 Q60 80 70 60 Q80 90 60 120" fill="currentColor" opacity="0.1"/></svg>
      </div>
    </div>
    <div class="side-illustration side-right" aria-hidden="true">
      <div class="si-layer si-skeleton">
        <svg viewBox="0 0 120 200" fill="none"><circle cx="60" cy="20" r="10" stroke="currentColor" stroke-width="1" opacity="0.12"/><line x1="60" y1="30" x2="60" y2="70" stroke="currentColor" stroke-width="1" opacity="0.1"/><line x1="60" y1="40" x2="35" y2="60" stroke="currentColor" stroke-width="1" opacity="0.1"/><line x1="60" y1="40" x2="85" y2="60" stroke="currentColor" stroke-width="1" opacity="0.1"/><line x1="60" y1="70" x2="38" y2="110" stroke="currentColor" stroke-width="1" opacity="0.1"/><line x1="60" y1="70" x2="82" y2="110" stroke="currentColor" stroke-width="1" opacity="0.1"/></svg>
      </div>
      <div class="si-layer si-equipment">
        <svg viewBox="0 0 120 200" fill="none"><rect x="40" y="20" width="40" height="8" rx="4" stroke="currentColor" stroke-width="1" opacity="0.1"/><rect x="48" y="40" width="24" height="60" rx="4" stroke="currentColor" stroke-width="1" opacity="0.1"/><circle cx="60" cy="120" r="16" stroke="currentColor" stroke-width="1" opacity="0.1"/></svg>
      </div>
      <div class="si-layer si-pose">
        <svg viewBox="0 0 120 200" fill="none"><circle cx="60" cy="30" r="12" stroke="currentColor" stroke-width="1.2" opacity="0.12"/><path d="M60 42 L60 95 L45 130 M60 65 L85 85 M60 95 L75 130" stroke="currentColor" stroke-width="1.2" opacity="0.1" stroke-linecap="round"/></svg>
      </div>
      <div class="si-layer si-tree">
        <svg viewBox="0 0 120 200" fill="none"><path d="M60 180 L60 120" stroke="currentColor" stroke-width="2" opacity="0.12"/><path d="M60 150 Q30 120 40 90 Q60 110 80 90 Q90 120 60 150" fill="currentColor" opacity="0.08"/><path d="M60 120 Q40 90 50 60 Q60 80 70 60 Q80 90 60 120" fill="currentColor" opacity="0.1"/></svg>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ══════════════════════════════════════════════════════════════
   Page Shell
   ══════════════════════════════════════════════════════════════ */
.prescription-page {
  position: relative;
  max-width: 860px;
  margin: -24px auto 0;
  padding: 24px 32px 40px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  background: linear-gradient(180deg, #faf9ff 0%, #f5f4ff 55%, #ffffff 100%);
  min-height: calc(100vh - 64px - 56px);
}

.prescription-page::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(rgba(108,99,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(108,99,255,0.03) 1px, transparent 1px);
  background-size: 30px 30px, 30px 30px;
  pointer-events: none;
  z-index: 0;
}

.bg-glow {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
  filter: blur(100px);
}
.bg-glow-1 {
  width: 360px; height: 360px;
  top: -100px; right: -80px;
  background: rgba(108,99,255,0.05);
}
.bg-glow-2 {
  width: 300px; height: 300px;
  bottom: 10%; left: -90px;
  background: rgba(92,140,255,0.04);
}

/* ══════════════════════════════════════════════════════════════
   Hero Banner
   ══════════════════════════════════════════════════════════════ */
.hero-banner {
  position: relative;
  z-index: 1;
  background: linear-gradient(135deg, #5B4DFF 0%, #7B6CFF 50%, #4F8CFF 100%);
  border-radius: 24px;
  padding: 24px 28px;
  overflow: hidden;
  min-height: auto;
  display: flex;
  align-items: center;
  box-shadow: 0 20px 60px rgba(91,77,255,0.22);
}

.hero-banner::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 20% 120%, rgba(255,255,255,0.14), transparent 40%),
              radial-gradient(circle at 90% -20%, rgba(255,255,255,0.1), transparent 35%);
  pointer-events: none;
}

.hero-mesh {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px);
  background-size: 24px 24px;
  pointer-events: none;
}

.hero-skeleton {
  position: absolute;
  right: 24%;
  top: 50%;
  transform: translateY(-50%);
  width: 160px;
  height: 260px;
  color: #fff;
  opacity: 0.18;
  pointer-events: none;
  filter: blur(0.5px);
}

.hero-neural {
  position: absolute;
  left: -20px;
  bottom: -30px;
  width: 280px;
  height: 140px;
  color: #fff;
  opacity: 0.22;
  pointer-events: none;
}

.hero-radar {
  position: absolute;
  right: 18%;
  top: 16px;
  width: 80px;
  height: 80px;
  color: #fff;
  opacity: 0.18;
  pointer-events: none;
  animation: radar-spin 12s linear infinite;
}
@keyframes radar-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.hero-datastream {
  position: absolute;
  right: 6%;
  bottom: 18px;
  display: flex;
  align-items: flex-end;
  gap: 5px;
  height: 48px;
  pointer-events: none;
}
.data-bar {
  width: 4px;
  height: var(--h);
  background: rgba(255,255,255,0.35);
  border-radius: 2px;
  animation: data-pulse 1.6s ease-in-out infinite;
  animation-delay: var(--d);
}
@keyframes data-pulse {
  0%, 100% { opacity: 0.25; transform: scaleY(0.7); }
  50% { opacity: 0.7; transform: scaleY(1); }
}

.hero-particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}
.h-particle {
  position: absolute;
  width: 3px;
  height: 3px;
  background: rgba(255,255,255,0.5);
  border-radius: 50%;
  top: calc(20% + var(--i) * 4%);
  left: calc(10% + var(--i) * 5%);
  animation: float-particle 4s ease-in-out infinite;
  animation-delay: calc(var(--i) * 0.2s);
  opacity: 0;
}
@keyframes float-particle {
  0% { transform: translateY(0) scale(0); opacity: 0; }
  20% { opacity: 0.6; }
  80% { opacity: 0.6; }
  100% { transform: translateY(-60px) scale(1); opacity: 0; }
}

.hero-inner {
  position: relative;
  z-index: 1;
  width: 100%;
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 24px;
}

/* Hero Left */
.hero-left {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.22);
  border-radius: 20px;
  padding: 6px 14px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  width: fit-content;
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}
.hero-title {
  font-size: 16px;
  font-weight: 500;
  color: rgba(255,255,255,0.92);
  line-height: 1.7;
  margin: 0;
}
.hero-tags {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.hero-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: rgba(255,255,255,0.8);
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 5px 11px;
}

/* Hero Right - AI Status Card */
.hero-right {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
}
.ai-status-card {
  position: relative;
  background: rgba(255,255,255,0.1);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 20px;
  padding: 18px 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 210px;
  box-shadow: 0 0 30px rgba(123,108,255,0.35), inset 0 1px 0 rgba(255,255,255,0.15);
  overflow: hidden;
}
.ai-status-card.glow::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 20px;
  padding: 1px;
  background: linear-gradient(135deg, rgba(255,255,255,0.4), rgba(255,255,255,0.05));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}
.ai-status-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255,255,255,0.12);
}
.ai-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
  animation: status-pulse 2s ease-in-out infinite;
}
@keyframes status-pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 8px #10b981; }
  50% { opacity: 0.6; box-shadow: 0 0 16px #10b981; }
}
.ai-status-title {
  font-size: 13px;
  font-weight: 700;
  color: #fff;
}
.ai-status-row {
  display: flex;
  align-items: center;
  gap: 10px;
  color: rgba(255,255,255,0.8);
}
.ai-status-label {
  font-size: 12px;
  color: rgba(255,255,255,0.65);
  flex: 1;
}
.ai-status-value {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

/* ══════════════════════════════════════════════════════════════
   Generating Progress Bar
   ══════════════════════════════════════════════════════════════ */
.gen-progress {
  position: relative;
  z-index: 1;
  height: 3px;
  background: rgba(108,99,255,0.08);
  border-radius: 2px;
  overflow: hidden;
}
.gen-progress-bar {
  height: 100%;
  width: 30%;
  background: linear-gradient(90deg, #7B6CFF, #5C8CFF, #7B6CFF);
  background-size: 200% 100%;
  border-radius: 2px;
  animation: gen-slide 1.5s ease-in-out infinite;
}
@keyframes gen-slide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}

/* ══════════════════════════════════════════════════════════════
   Tabs
   ══════════════════════════════════════════════════════════════ */
.prescription-tabs {
  position: relative;
  z-index: 1;
}
.prescription-tabs :deep(.n-tabs-tab) {
  border-radius: 12px !important;
  padding: 9px 22px !important;
  margin-right: 8px !important;
  transition: all 0.25s ease !important;
  font-weight: 500;
}
.prescription-tabs :deep(.n-tabs-tab--active) {
  background: linear-gradient(135deg, #7B6CFF, #5C8CFF) !important;
  color: #fff !important;
  box-shadow: 0 4px 16px rgba(123,108,255,0.3) !important;
}
.prescription-tabs :deep(.n-tabs-tab:not(.n-tabs-tab--active):hover) {
  background: rgba(123,108,255,0.07) !important;
}
.prescription-tabs :deep(.n-tabs-bar) {
  display: none !important;
}
.prescription-tabs :deep(.n-tabs-nav) {
  margin-bottom: 18px;
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ══════════════════════════════════════════════════════════════
   Unified Panel Card
   ══════════════════════════════════════════════════════════════ */
.panel-card {
  position: relative;
  z-index: 1;
  background: rgba(255,255,255,0.88);
  backdrop-filter: blur(18px);
  border-radius: 24px;
  border: 1px solid rgba(255,255,255,0.85);
  box-shadow: 0 14px 48px rgba(108,99,255,0.09);
  padding: 24px 28px;
  transition: all 0.25s ease;
}
.panel-card:hover {
  box-shadow: 0 18px 56px rgba(108,99,255,0.13);
}
.panel-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}
.panel-section-title {
  font-size: 17px;
  font-weight: 700;
  color: #1e293b;
}
.refresh-btn {
  color: #94a3b8 !important;
  transition: color 0.2s;
}
.refresh-btn:hover {
  color: #7B6CFF !important;
}

/* ══════════════════════════════════════════════════════════════
   Record Cards
   ══════════════════════════════════════════════════════════════ */
.record-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.record-card {
  background: rgba(255,255,255,0.88);
  backdrop-filter: blur(18px);
  border-radius: 24px;
  border: 1px solid rgba(255,255,255,0.85);
  box-shadow: 0 14px 48px rgba(108,99,255,0.09);
  padding: 22px 26px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: all 0.25s ease;
}
.record-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 20px 60px rgba(108,99,255,0.14);
}
.record-card-top {
  display: flex;
  align-items: center;
  gap: 12px;
}
.record-card-icon {
  width: 46px; height: 46px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.record-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.record-card-title {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}
.record-card-empty {
  padding: 24px 0;
}
.record-card-body {
  padding: 16px;
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.record-main {
  display: flex;
  align-items: center;
  gap: 20px;
}
.score-ring {
  position: relative;
  width: 76px;
  height: 76px;
  flex-shrink: 0;
}
.score-ring-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.score-ring-svg circle:nth-child(2) {
  transition: stroke-dasharray 0.6s ease;
}
.score-value {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.sv-num {
  font-size: 20px;
  font-weight: 800;
  color: #1e293b;
  line-height: 1;
}
.sv-label {
  font-size: 10px;
  color: #94a3b8;
}
.record-stats {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.rs-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 7px 12px;
  background: rgba(255,255,255,0.7);
  border-radius: 10px;
}
.rs-label {
  font-size: 12px;
  color: #64748b;
}
.rs-value {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}
.record-trend {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px dashed #e2e8f0;
}
.rt-label {
  font-size: 12px;
  color: #64748b;
}
.rt-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;
}
.record-card-select {
  margin-top: -2px;
}

/* ══════════════════════════════════════════════════════════════
   Generation Config & Generate Action Card
   ══════════════════════════════════════════════════════════════ */
.gen-config-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
}
.gen-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.gen-switch-field {
  grid-column: span 2;
}
.gen-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}
.gen-hint {
  font-size: 11px;
  color: #94a3b8;
  margin: 0;
}
.gen-switch-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 14px;
  height: 100%;
}

.generate-action-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(245,244,255,0.92));
}
.ga-left {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.ga-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 800;
  color: #1e293b;
}
.ga-title .n-icon { color: #7B6CFF; }
.ga-output-modules {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.ga-module {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255,255,255,0.7);
  border-radius: 12px;
  border: 1px solid rgba(0,0,0,0.04);
}
.ga-module-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--m-color);
  box-shadow: 0 0 8px var(--m-color);
}
.ga-module-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.ga-module-label {
  font-size: 12px;
  font-weight: 700;
  color: #1e293b;
}
.ga-module-desc {
  font-size: 10px;
  color: #94a3b8;
}
.ga-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 14px;
  min-width: 180px;
}
.ga-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}
.ga-meta-label {
  font-size: 11px;
  color: #94a3b8;
}
.ga-meta-value {
  font-size: 18px;
  font-weight: 800;
  color: #7B6CFF;
}

/* AI Generate Button */
.generate-btn {
  background: linear-gradient(135deg, #7B6CFF, #5C8CFF) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 16px !important;
  padding: 14px 36px !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  height: 50px !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  box-shadow: 0 6px 24px rgba(123,108,255,0.35) !important;
}
.generate-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 32px rgba(123,108,255,0.45) !important;
}
.generate-btn:active:not(:disabled) {
  transform: translateY(0);
}
.generate-btn :deep(.n-button__border),
.generate-btn :deep(.n-button__state-border) {
  border: none !important;
}

/* ══════════════════════════════════════════════════════════════
   Custom Steps (in generated plan)
   ══════════════════════════════════════════════════════════════ */
.custom-steps {
  display: flex;
  align-items: center;
  gap: 0;
}
.custom-step {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.custom-step .step-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #e2e8f0;
  border: 2px solid #cbd5e1;
  transition: all 0.3s;
}
.custom-step.done .step-dot {
  background: #10b981;
  border-color: #10b981;
  position: relative;
}
.custom-step.done .step-dot::after {
  content: '';
  position: absolute;
  left: 7px;
  top: 3px;
  width: 6px;
  height: 11px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}
.custom-step.active .step-dot {
  background: #8b5cf6;
  border-color: #8b5cf6;
  box-shadow: 0 0 0 3px rgba(139,92,246,.25);
}
.custom-step .step-label {
  font-size: 13px;
  color: #94a3b8;
  white-space: nowrap;
}
.custom-step.done .step-label,
.custom-step.active .step-label {
  color: #334155;
  font-weight: 600;
}
.step-line {
  flex: 1;
  height: 2px;
  background: #e2e8f0;
  min-width: 24px;
  margin: 0 8px;
}

/* ══════════════════════════════════════════════════════════════
   AI Generation Animation Overlay
   ══════════════════════════════════════════════════════════════ */
.gen-animation-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.gen-animation-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(6px);
}
.gen-animation-card {
  position: relative;
  width: 420px;
  max-width: 100%;
  background: rgba(255,255,255,0.96);
  border-radius: 28px;
  padding: 36px 32px;
  box-shadow: 0 32px 80px rgba(0,0,0,0.18);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  text-align: center;
}
.gen-animation-pulse {
  position: relative;
  width: 90px;
  height: 90px;
}
.pulse-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: rgba(123,108,255,0.15);
  animation: pulse-ring 2s ease-out infinite;
}
.pulse-core {
  position: absolute;
  inset: 18px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7B6CFF, #5C8CFF);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 28px rgba(123,108,255,0.35);
}
@keyframes pulse-ring {
  0% { transform: scale(0.8); opacity: 0.6; }
  100% { transform: scale(1.6); opacity: 0; }
}
.gen-animation-title {
  font-size: 20px;
  font-weight: 800;
  color: #1e293b;
  margin: 0;
}
.gen-animation-steps {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.gen-animation-step {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  border-radius: 16px;
  background: #f8fafc;
  opacity: 0.5;
  transition: all 0.4s ease;
}
.gen-animation-step.active {
  opacity: 1;
  background: linear-gradient(135deg, rgba(123,108,255,0.08), rgba(92,140,255,0.08));
  box-shadow: 0 4px 16px rgba(123,108,255,0.1);
}
.gen-animation-step.done {
  opacity: 0.85;
  background: rgba(16,185,129,0.06);
}
.gas-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #e2e8f0;
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
}
.gen-animation-step.active .gas-icon {
  background: linear-gradient(135deg, #7B6CFF, #5C8CFF);
  color: #fff;
}
.gen-animation-step.done .gas-icon {
  background: #10b981;
  color: #fff;
}
.gas-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}
.gas-label {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}
.gas-desc {
  font-size: 11px;
  color: #94a3b8;
}
.gen-animation-progress {
  width: 100%;
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
}
.gen-animation-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #7B6CFF, #5C8CFF);
  border-radius: 3px;
  transition: width 0.4s ease;
}

.fade-scale-enter-active,
.fade-scale-leave-active {
  transition: all 0.35s ease;
}
.fade-scale-enter-from,
.fade-scale-leave-to {
  opacity: 0;
  transform: scale(0.96);
}

/* ══════════════════════════════════════════════════════════════
   Side Decorative Illustrations
   ══════════════════════════════════════════════════════════════ */
.side-illustration {
  position: fixed;
  top: 80px;
  bottom: 40px;
  width: 140px;
  pointer-events: none;
  z-index: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  opacity: 0.7;
}
.side-left { left: calc((100% - 1100px) / 2 - 120px); }
.side-right { right: calc((100% - 1100px) / 2 - 120px); }
.si-layer {
  width: 100%;
  color: #7B6CFF;
  transform: scale(0.9);
}
.si-layer svg { width: 100%; height: auto; }
.si-skeleton { opacity: 0.9; }
.si-equipment { opacity: 0.75; }
.si-pose { opacity: 0.8; }
.si-tree { opacity: 0.85; }

/* ══════════════════════════════════════════════════════════════
   History Plan Cards (shared between Tab 1 & Tab 2)
   ══════════════════════════════════════════════════════════════ */
.history-cards {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.history-plan-card {
  background: rgba(255,255,255,0.82);
  border-radius: 22px;
  border: 1px solid rgba(255,255,255,0.85);
  padding: 22px 26px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  box-shadow: 0 10px 36px rgba(108,99,255,0.06);
}
.history-plan-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 16px 48px rgba(108,99,255,0.12);
  border-color: rgba(108,99,255,0.12);
}

.hpc-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}
.hpc-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.hpc-icon {
  width: 46px; height: 46px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.hpc-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.hpc-name {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}
.hpc-meta {
  font-size: 12px;
  color: #94a3b8;
}
.hpc-right {
  flex-shrink: 0;
}

/* Phases Row */
.hpc-phases {
  display: flex;
  gap: 20px;
  margin-bottom: 14px;
  padding: 10px 14px;
  background: #f8fafc;
  border-radius: 12px;
}
.hpc-phase {
  display: flex;
  align-items: center;
  gap: 6px;
}
.hpc-phase-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.hpc-phase-label {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
}
.hpc-phase-count {
  font-size: 12px;
  color: #94a3b8;
}

/* Stats Row */
.hpc-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 14px;
}
.hpc-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.hpc-stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #334155;
}
.hpc-stat-label {
  font-size: 11px;
  color: #94a3b8;
}

/* Actions */
.hpc-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
}

/* ══════════════════════════════════════════════════════════════
   History Empty
   ══════════════════════════════════════════════════════════════ */
.history-empty-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  text-align: center;
}
.history-empty-circle {
  width: 90px; height: 90px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(102,126,234,0.12), rgba(118,75,162,0.12));
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8b5cf6;
  margin-bottom: 16px;
}
.history-empty-title {
  font-size: 17px;
  font-weight: 700;
  color: #334155;
  margin: 0 0 8px;
}
.history-empty-desc {
  font-size: 13px;
  color: #94a3b8;
  margin: 0 0 20px;
}

/* ══════════════════════════════════════════════════════════════
   Action Library
   ══════════════════════════════════════════════════════════════ */
.lib-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}
.lib-count {
  font-size: 12px;
  color: #94a3b8;
}
.action-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.action-card {
  background: rgba(255,255,255,0.7);
  border-radius: 18px;
  padding: 16px 18px;
  border: 1px solid rgba(255,255,255,0.8);
  transition: all 0.25s ease;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 4px 14px rgba(108,99,255,0.04);
}
.action-card:hover {
  background: rgba(255,255,255,0.95);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(108,99,255,0.1);
}
.action-card-top {
  display: flex;
  align-items: center;
  gap: 10px;
}
.action-card-icon {
  width: 38px; height: 38px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.action-card-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.action-card-name {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}
.action-card-family {
  font-size: 11px;
  color: #94a3b8;
}
.action-card-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* ══════════════════════════════════════════════════════════════
   Fade-in animation
   ══════════════════════════════════════════════════════════════ */
.panel-card, .record-card, .history-plan-card, .action-card {
  animation: fade-up 0.45s ease both;
}
@keyframes fade-up {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ══════════════════════════════════════════════════════════════
   Mobile
   ══════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
  .prescription-page {
    padding: 16px;
    margin: -16px auto 0;
    gap: 16px;
  }
  .hero-banner {
    padding: 22px 18px;
    min-height: auto;
  }
  .hero-inner {
    grid-template-columns: 1fr;
    gap: 18px;
  }
  .hero-title {
    font-size: 14px;
  }
  .hero-right { order: 2; justify-content: flex-start; }
  .ai-status-card { min-width: 0; width: 100%; }
  .hero-skeleton, .hero-neural, .hero-radar, .hero-datastream { display: none; }
  .record-cards {
    grid-template-columns: 1fr;
  }
  .gen-config-grid {
    grid-template-columns: 1fr 1fr;
  }
  .gen-switch-field { grid-column: span 2; }
  .generate-action-card {
    flex-direction: column;
    align-items: stretch;
  }
  .ga-right {
    align-items: stretch;
    min-width: 0;
  }
  .generate-btn {
    width: 100%;
  }
  .side-illustration { display: none; }
  .action-cards {
    grid-template-columns: 1fr;
  }
  .lib-header {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 480px) {
  .gen-config-grid {
    grid-template-columns: 1fr;
  }
  .gen-switch-field { grid-column: span 1; }
}
</style>
