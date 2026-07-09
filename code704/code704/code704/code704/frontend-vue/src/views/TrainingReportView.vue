<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NSpin, NButton, NIcon, NResult } from 'naive-ui'
import { ArrowBackOutline } from '@vicons/ionicons5'
import dayjs from 'dayjs'

import ReportHero from '../components/trainingReport/ReportHero.vue'
import DataCards from '../components/trainingReport/DataCards.vue'
import AiAnalysisCard from '../components/trainingReport/AiAnalysisCard.vue'
import RadarChart from '../components/trainingReport/RadarChart.vue'
import TrendChart from '../components/trainingReport/TrendChart.vue'
import SuggestionsSection from '../components/trainingReport/SuggestionsSection.vue'
import BestPoseAnalysis from '../components/trainingReport/BestPoseAnalysis.vue'
import ActionFooter from '../components/trainingReport/ActionFooter.vue'

import { fetchMockStandardTrainingReport, type StandardTrainingReport } from '../mock/standardTrainingReportMock'
import { learningApi } from '../services/api'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref<string | null>(null)
const report = ref<StandardTrainingReport | null>(null)

const formattedCompletedAt = computed(() => {
  if (!report.value?.completedAt) return '-'
  return dayjs(report.value.completedAt).format('YYYY年MM月DD日 HH:mm')
})

// Joint labels — maps backend English keys to Chinese display names
const JOINT_LABELS: Record<string, string> = {
  trunk_tilt: '躯干倾斜', neck_tilt: '颈部倾斜',
  left_hip: '左髋角', right_hip: '右髋角',
  left_knee: '左膝角', right_knee: '右膝角',
  left_shoulder: '左肩角', right_shoulder: '右肩角',
  left_elbow: '左肘角', right_elbow: '右肘角',
  left_ankle: '左踝角', right_ankle: '右踝角',
}

function clamp(v: number, lo: number, hi: number): number { return Math.max(lo, Math.min(hi, v)) }

function mapRecordToReport(raw: any): StandardTrainingReport {
  // ── Extract raw data ──────────────────────────────────────
  const angleHistory: any[] = Array.isArray(raw.angle_history) ? raw.angle_history : []
  const rawSummary = raw.summary
  const summaryList: string[] = Array.isArray(rawSummary) ? rawSummary
    : (typeof rawSummary === 'string' && rawSummary ? [rawSummary] : [])
  const feedbackCounts: Record<string, number> = raw.feedback_counts || {}
  const duration = Number(raw.duration) || 0
  const bestScore = Math.round(Number(raw.best_score || 0))
  const totalScore = Math.round(Number(raw.total_score || raw.overall_score || raw.best_score || 0))
  const frameCount = raw.frame_count || 0

  // Best-frame data (from WebSocket learning_complete)
  const bestFrameAngles: Record<string, number> = raw.best_frame_angles || {}
  const bestFrameDiffs: any[] = Array.isArray(raw.best_frame_diffs) ? raw.best_frame_diffs : []
  const bestFrameFeedbacks: any[] = Array.isArray(raw.best_frame_feedbacks) ? raw.best_frame_feedbacks : []

  console.log('[Report] angleHistory:', angleHistory.length, 'frames, bestFrameDiffs:', bestFrameDiffs.length, 'joints, bestFrameAngles:', Object.keys(bestFrameAngles).length, 'joints')
  const hasRealData = angleHistory.length >= 5  // need at least 5 frames for meaningful stats
  const hasBestFrameData = bestFrameDiffs.length > 0

  // ── Helper: joint keys common to all entries ──────────────
  const commonJoints = (): string[] => {
    if (angleHistory.length === 0) return []
    const first = angleHistory[0]?.angles
    if (!first || typeof first !== 'object') return []
    const keys = Object.keys(first)
    return keys.filter(k =>
      angleHistory.every(e => e?.angles && typeof e.angles[k] === 'number')
    )
  }

  // ── Trend chart data ──────────────────────────────────────
  const trendWindow = angleHistory.slice(-10)
  let trendData: { index: number; score: number; standard: number; stability: number }[]

  if (hasRealData && trendWindow.length >= 2) {
    trendData = trendWindow.map((entry: any, i: number) => {
      // Quality: real per-frame score (or interpolate nulls)
      const rawScore = typeof entry.score === 'number' ? entry.score : null
      const score = rawScore ?? bestScore

      // Standard: avg deviation of this frame's angles from best_frame_angles
      let standard = Math.round(bestScore * 0.95)
      if (Object.keys(bestFrameAngles).length > 0 && entry.angles && typeof entry.angles === 'object') {
        let totalDev = 0, count = 0
        for (const [joint, refAngle] of Object.entries(bestFrameAngles)) {
          const frameAngle = entry.angles[joint]
          if (typeof frameAngle === 'number' && typeof refAngle === 'number') {
            totalDev += clamp(100 - Math.abs(frameAngle - refAngle) * 2.0, 0, 100)
            count++
          }
        }
        if (count > 0) standard = Math.round(totalDev / count)
      }

      // Stability: frame-to-frame angle change magnitude (compare with previous)
      let stability = standard
      if (i > 0) {
        const prev = trendWindow[i - 1]
        if (prev?.angles && entry.angles && typeof prev.angles === 'object' && typeof entry.angles === 'object') {
          let totalChange = 0, count = 0
          for (const k of Object.keys(entry.angles)) {
            const cur = entry.angles[k]
            const prv = prev.angles[k]
            if (typeof cur === 'number' && typeof prv === 'number') {
              totalChange += Math.abs(cur - prv)
              count++
            }
          }
          if (count > 0) stability = Math.round(clamp(100 - (totalChange / count) * 3.0, 0, 100))
        }
      }

      return { index: i + 1, score: Math.round(score), standard, stability }
    })
  } else {
    // Fallback: linear interpolation from bestScore
    trendData = trendWindow.map((_: any, i: number) => ({
      index: i + 1,
      score: Math.round(bestScore * (0.7 + 0.3 * (i / Math.max(trendWindow.length - 1, 1)))),
      standard: Math.round(bestScore * 0.95),
      stability: Math.round(bestScore * 0.9),
    }))
  }

  // ── Radar dimensions ──────────────────────────────────────
  let standardDim: number, stabilityDim: number, coordinationDim: number
  let controlDim: number, completionDim: number

  if (hasBestFrameData) {
    // Standard: average percent score across all joints at best frame
    standardDim = Math.round(
      bestFrameDiffs.reduce((s: number, d: any) => s + (d.percent ?? 100), 0) / bestFrameDiffs.length
    )
  } else {
    standardDim = Math.round(bestScore * 0.98)
  }

  if (hasRealData) {
    // Stability: standard deviation of joint angles across frames
    const joints = commonJoints()
    if (joints.length > 0) {
      const stdDevs = joints.map(joint => {
        const vals = angleHistory
          .map((e: any) => e?.angles?.[joint])
          .filter((v: any) => typeof v === 'number') as number[]
        if (vals.length < 3) return 0
        const mean = vals.reduce((s, v) => s + v, 0) / vals.length
        return Math.sqrt(vals.reduce((s, v) => s + (v - mean) ** 2, 0) / vals.length)
      })
      const avgStdDev = stdDevs.reduce((s, v) => s + v, 0) / stdDevs.length
      stabilityDim = Math.round(clamp(100 - avgStdDev * 2.5, 0, 100))
    } else {
      stabilityDim = Math.round(bestScore * 0.96)
    }
  } else {
    stabilityDim = Math.round(bestScore * 0.96)
  }

  if (hasBestFrameData && Object.keys(bestFrameAngles).length > 0) {
    // Coordination: left-right symmetry
    const pairs: [string, string][] = [
      ['left_knee', 'right_knee'], ['left_hip', 'right_hip'],
      ['left_shoulder', 'right_shoulder'], ['left_elbow', 'right_elbow'],
      ['left_ankle', 'right_ankle'],
    ]
    const pairScores: number[] = []
    for (const [l, r] of pairs) {
      const lv = bestFrameAngles[l], rv = bestFrameAngles[r]
      if (typeof lv === 'number' && typeof rv === 'number') {
        pairScores.push(clamp(100 - Math.abs(lv - rv) * 2, 0, 100))
      }
    }
    coordinationDim = pairScores.length > 0
      ? Math.round(pairScores.reduce((s, v) => s + v, 0) / pairScores.length)
      : Math.round(bestScore * 0.90)
  } else {
    coordinationDim = Math.round(bestScore * 0.90)
  }

  if (hasRealData) {
    // Control: average second-difference (jerk) of angles across frames
    const joints = commonJoints()
    if (joints.length > 0 && angleHistory.length >= 5) {
      const jerks = joints.map(joint => {
        const vals = angleHistory
          .map((e: any) => e?.angles?.[joint])
          .filter((v: any) => typeof v === 'number') as number[]
        if (vals.length < 3) return 0
        let sumJerk = 0, count = 0
        for (let i = 1; i < vals.length - 1; i++) {
          sumJerk += Math.abs((vals[i + 1] - vals[i]) - (vals[i] - vals[i - 1]))
          count++
        }
        return count > 0 ? sumJerk / count : 0
      })
      const avgJerk = jerks.reduce((s, v) => s + v, 0) / jerks.length
      controlDim = Math.round(clamp(100 - avgJerk * 1.5, 0, 100))
    } else {
      controlDim = Math.round(bestScore * 0.92)
    }
  } else {
    controlDim = Math.round(bestScore * 0.92)
  }

  // Completion: actual frames / expected frames (capture every ~200ms)
  const expectedFrames = duration > 0 ? duration / 0.2 : frameCount
  completionDim = duration > 0
    ? Math.round(Math.min(100, (frameCount / expectedFrames) * 100))
    : Math.min(100, Math.round(frameCount / 4))

  const radarDimensions = [
    { name: '标准度', value: standardDim, max: 100 },
    { name: '稳定性', value: stabilityDim, max: 100 },
    { name: '协调性', value: coordinationDim, max: 100 },
    { name: '控制力', value: controlDim, max: 100 },
    { name: '完成度', value: completionDim, max: 100 },
  ]

  // ── Encouragement ─────────────────────────────────────────
  const encouragement = bestScore >= 95
    ? `单次动作最高得分 ${bestScore} 分，关键关节角度全部在标准范围内，动作模式正确。`
    : bestScore >= 85
    ? `单次动作得分 ${bestScore} 分，整体到位，少数关节跟标准有点偏差，微调即可。`
    : bestScore >= 70
    ? `单次动作得分 ${bestScore} 分，大部分关节对上标准，但 1-2 处偏差较明显，建议逐项校准。`
    : bestScore >= 50
    ? `单次动作得分 ${bestScore} 分，多处关键位置偏离标准，建议放慢重做，先保证角度准确。`
    : `单次动作得分 ${bestScore} 分，与标准偏离较多，建议从分解练习逐步建立正确模式。`

  // ── BestPose (best-frame analysis) ────────────────────────
  let bestFrameQuality = Math.round(bestScore * 0.95)

  // keyAngles: top 5 joints with largest absolute deviation
  let keyAngles: any[] = []
  let detailedAngles: any[] = []
  let frameTip = ''

  if (hasBestFrameData) {
    bestFrameQuality = Math.round(
      bestFrameDiffs.reduce((s: number, d: any) => s + (d.percent ?? 100), 0) / bestFrameDiffs.length
    )

    keyAngles = bestFrameDiffs
      .filter((d: any) => d.user !== null && d.user !== undefined)
      .sort((a: any, b: any) => Math.abs(b.diff ?? 0) - Math.abs(a.diff ?? 0))
      .slice(0, 5)
      .map((d: any) => ({
        joint: JOINT_LABELS[d.joint] || d.joint,
        value: Math.round(d.user),
        status: (d.status || 'unknown') as 'good' | 'close' | 'warning' | 'bad',
      }))

    detailedAngles = bestFrameDiffs.map((d: any) => ({
      joint: JOINT_LABELS[d.joint] || d.joint,
      user: Math.round(d.user ?? 0),
      standard: d.standard_optimal,
      diff: Math.round(d.diff ?? 0),
      status: (d.status || 'unknown') as 'good' | 'close' | 'warning' | 'bad',
    }))

    frameTip = bestFrameFeedbacks.length > 0
      ? bestFrameFeedbacks.map((f: any) => f.message).join('；')
      : '系统自动抓拍最佳帧'
  } else if (Object.keys(bestFrameAngles).length > 0) {
    // Fallback 1: use best_frame_angles (without standard comparison)
    // Filter: exclude joints with very small angles (<15°) that are likely noise/irrelevant
    const joints = (Object.entries(bestFrameAngles) as [string, number][])
      .filter(([, value]) => Math.abs(value) >= 15)
    keyAngles = joints.slice(0, 5).map(([joint, value]) => ({
      joint: JOINT_LABELS[joint] || joint,
      value: Math.round(value),
      status: 'good' as const,
    }))
    detailedAngles = joints.map(([joint, value]) => ({
      joint: JOINT_LABELS[joint] || joint,
      user: Math.round(value),
      standard: 0,
      diff: 0,
      status: 'unknown' as const,
    }))
    frameTip = '最佳帧关节角度'
  } else if (angleHistory.length > 0) {
    // Fallback 2: use last frame's raw angles
    const last = angleHistory[angleHistory.length - 1]
    const angles: Record<string, number> = last?.angles || {}
    const jointEntries = Object.entries(angles).filter(([, value]) => Math.abs(value) >= 15)
    detailedAngles = jointEntries.map(([joint, value]) => ({
      joint: JOINT_LABELS[joint] || joint,
      user: Math.round(value),
      standard: 0,
      diff: 0,
      status: 'unknown' as const,
    }))
    frameTip = '最近一帧角度数据'
  }

  // ── Suggestions ───────────────────────────────────────────
  const feedbackEntries = Object.entries(feedbackCounts).sort((a, b) => Number(b[1]) - Number(a[1]))
  const goodItems: any[] = [{
    title: '数据采集情况',
    desc: `共采集 ${frameCount} 帧画面，跟标准动作逐帧比对关节角度。`,
    icon: 'CheckmarkCircleOutline', color: '#7c3aed'
  }]
  const improveItems = feedbackEntries.slice(0, 3).map(([name, count]) => ({
    title: name,
    desc: `出现 ${count} 次，下次做的时候注意这一点。`,
    icon: 'FitnessOutline', color: '#a78bfa'
  }))

  // ── Assemble ──────────────────────────────────────────────
  return {
    id: raw.id,
    actionName: raw.action_name || '未知动作',
    completedAt: raw.created_at || new Date().toISOString(),
    bestScore,
    totalScore,
    encouragement,
    metrics: [
      { name: '（有效动作）综合评分', value: totalScore, unit: '分', icon: 'TrophyOutline', color: '#7c3aed' },
      { name: '最佳分', value: bestScore, unit: '分', icon: 'StarOutline', color: '#f59e0b' },
      { name: '动作质量', value: bestFrameQuality, unit: '%', icon: 'ShieldCheckmarkOutline', color: '#a78bfa' },
      { name: '用时', value: `${Math.floor(duration / 60)}分${Math.round(duration % 60)}秒`, unit: '', icon: 'TimeOutline', color: '#a78bfa' },
      { name: '比对帧数', value: frameCount, unit: '帧', icon: 'VideocamOutline', color: '#a78bfa' }
    ],
    aiAnalysis: {
      text: summaryList.join('\n') || '',
      tags: bestScore >= 85
        ? ['关节角度达标', '身体稳定', '节奏均匀']
        : bestScore >= 70 ? ['基本完成', '部分偏差', '可校准'] : ['偏差明显', '需重点关注', '建议重新来'],
      mainIssue: feedbackEntries.length > 0 ? feedbackEntries[0][0] : '无明显问题',
      nextSuggestion: bestScore >= 85
        ? '这次动作已达到标准要求，后续可尝试不同姿势检验动作稳定性。'
        : bestScore >= 70
        ? '建议对照标准图逐关节校准，先慢做把角度对准，再逐步提速。'
        : '建议从分解动作开始，每个关节单独达标后再串联为完整动作。'
    },
    bestPose: {
      quality: bestFrameQuality,
      stability: stabilityDim,
      standard: standardDim,
      keyAngles,
      detailedAngles,
      frameTip,
    },
    radarDimensions,
    trendData,
    suggestions: [
      { title: '优势', icon: 'ThumbsUpOutline', color: '#7c3aed', items: goodItems },
      {
        title: '风险判断', icon: 'WarningOutline', color: '#d97706',
        items: improveItems
      },
      {
        title: '下一步策略', icon: 'BulbOutline', color: '#0d9488',
        items: [{
          title: '变式检验',
          desc: summaryList.length > 0 ? summaryList[summaryList.length - 1] : '在不同条件下执行同一动作，检验关节角度是否依然吻合标准。',
          icon: 'TrendingUpOutline', color: '#0d9488'
        }]
      }
    ]
  }
}

async function loadReport() {
  loading.value = true; error.value = null
  const recordId = route.params.id as string

  if (recordId === 'direct' || recordId === 'mock') {
    const stored = sessionStorage.getItem('learningCompleteData')
    if (stored) {
      try {
        const data = JSON.parse(stored)
        report.value = mapRecordToReport({
          id: 0, action_name: data.action_name || '',
          overall_score: data.total_score || data.best_score || 0,
          best_score: data.best_score || 0, frame_count: data.frame_count || 0,
          duration: data.duration || 0, summary: data.summary || [],
          feedback_counts: data.feedback_counts || {}, angle_history: data.angle_history || [],
          best_frame_angles: data.best_frame_angles || {},
          best_frame_diffs: data.best_frame_diffs || [],
          best_frame_feedbacks: data.best_frame_feedbacks || [],
          best_frame_kp: data.best_frame_kp || null,
          best_frame_conf: data.best_frame_conf || null,
          created_at: new Date().toISOString(),
        })
        loading.value = false; return
      } catch { /* fallback */ }
    }
    try { report.value = await fetchMockStandardTrainingReport(recordId) } catch (e) { error.value = e instanceof Error ? e.message : '加载失败' }
    loading.value = false; return
  }

  try {
    const raw = await learningApi.getReport(recordId)
    if (raw?.id) { report.value = mapRecordToReport(raw) } else { throw new Error('空数据') }
  } catch {
    try { report.value = await fetchMockStandardTrainingReport(recordId) } catch (e2) { error.value = e2 instanceof Error ? e2.message : '加载失败' }
  } finally { loading.value = false }
}

function handleRestart() { router.push({ path: '/training', query: { restart: report.value?.actionName || '' } }) }
function handleBackToPlan() {
  const planId = route.query.planId
  if (planId) router.push({ path: '/training', query: { planId } })
  else router.push('/training')
}
function handleViewAllPlans() { router.push('/prescription-training') }

onMounted(() => loadReport())
</script>

<script lang="ts">
export default { name: 'TrainingReportView' }
</script>

<template>
  <div class="page">
    <n-spin v-if="loading" class="loading" :show="true"><template #description>正在生成训练报告...</template></n-spin>

    <n-result v-else-if="error" status="error" title="报告加载失败" :description="error" class="error">
      <template #footer><n-button type="primary" @click="loadReport">重新加载</n-button></template>
    </n-result>

    <template v-else-if="report">
      <!-- 返回链接 -->
      <div class="back">
        <n-button text size="small" @click="handleBackToPlan">
          <template #icon><n-icon :component="ArrowBackOutline" /></template>
          返回训练计划
        </n-button>
      </div>

      <!-- 1. 主视觉结果区 —— 页面唯一焦点 -->
      <report-hero
        :action-name="report.actionName"
        :best-score="report.bestScore"
        :encouragement="report.encouragement"
        :completed-at="formattedCompletedAt"
      />

      <!-- 2. 核心指标区 -->
      <data-cards :metrics="report.metrics" />

      <!-- 3. AI 训练分析 -->
      <ai-analysis-card :analysis="report.aiAnalysis" />

      <!-- 3.5 最佳动作分析 -->
      <best-pose-analysis :data="report.bestPose" />

      <!-- 4. 能力分析：雷达图 + 趋势图 -->
      <div class="charts">
        <radar-chart :dimensions="report.radarDimensions" />
        <trend-chart :points="report.trendData" />
      </div>

      <!-- 5. 总结与建议 -->
      <suggestions-section :groups="report.suggestions" />

      <!-- 6. 操作区 -->
      <action-footer
        @restart="handleRestart"
        @back-to-plan="handleBackToPlan"
        @view-all-plans="handleViewAllPlans"
      />
    </template>
  </div>
</template>

<style scoped lang="scss">
.page {
  max-width: 920px;
  margin: 0 auto;
  padding: 0 0 48px;
  display: flex;
  flex-direction: column;
  gap: 24px; // 统一的大间距
}

.loading {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error { padding: 60px 0; }

.back { margin-bottom: -8px; }

.charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

@media (max-width: 1024px) {
  .charts { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .page { gap: 18px; padding: 0 0 32px; }
}
</style>
