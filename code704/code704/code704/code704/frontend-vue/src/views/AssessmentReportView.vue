<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { assessmentApi } from '../services/api'
import {
  NButton, NTag, NSpin, NResult, NCollapse, NCollapseItem, NIcon
} from 'naive-ui'
import {
  AlertOutline, BulbOutline, ArrowBackOutline, RefreshOutline,
  FitnessOutline, BodyOutline, FlashOutline
} from '@vicons/ionicons5'

use([CanvasRenderer, RadarChart, TooltipComponent])

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const record = ref<any>(null)

const RISK_COLORS: Record<string, string> = {
  high: '#ef6a6a',
  medium: '#f2a94a',
  low: '#56b98f'
}
const RISK_LABELS: Record<string, string> = {
  high: '高风险',
  medium: '中等风险',
  low: '良好'
}
const SEVERITY_LABELS: Record<string, string> = {
  severe: '严重',
  moderate: '中度',
  mild: '轻度'
}
const WEEK_STAGES = ['恢复灵活性', '激活核心', '姿态纠正', '综合强化']
const DIMENSION_ICONS = ['衡', '柔', '臂', '核', '称']

const riskColor = computed(() => RISK_COLORS[record.value?.risk_level] || '#7568f8')
const riskLabel = computed(() => RISK_LABELS[record.value?.risk_level] || record.value?.risk_level)
const severeProblemCount = computed(() => (
  record.value?.posture_problems?.filter((item: any) => item.severity === 'severe').length || 0
))

const abilityDimensions = computed(() => {
  if (Array.isArray(record.value?.dimensions) && record.value.dimensions.length) {
    return record.value.dimensions
  }

  if (!record.value) return []
  return [
    { label: '平衡能力', score: Number(record.value.balance_score ?? 0) },
    { label: '柔韧性', score: Number(record.value.flexibility_score ?? 0) },
    { label: '上肢力量', score: Number(record.value.upper_limb_score ?? 0) },
    { label: '核心力量', score: Number(record.value.core_score ?? 0) },
    { label: '对称性', score: Number(record.value.symmetry_score ?? 0) }
  ]
})

const chartOption = computed(() => {
  if (!abilityDimensions.value.length) return null
  return {
    animationDuration: 1200,
    tooltip: { trigger: 'item' },
    radar: {
      center: ['50%', '51%'],
      radius: '66%',
      splitNumber: 5,
      indicator: abilityDimensions.value.map((d: any) => ({
        name: `${d.label}\n${d.score}`,
        max: 100
      })),
      axisName: {
        color: '#465068',
        fontSize: 13,
        fontWeight: 600,
        lineHeight: 20
      },
      axisLine: { lineStyle: { color: 'rgba(117,104,248,.18)' } },
      splitLine: { lineStyle: { color: 'rgba(117,104,248,.16)' } },
      splitArea: {
        areaStyle: {
          color: ['rgba(117,104,248,.015)', 'rgba(117,104,248,.045)']
        }
      }
    },
    series: [{
      type: 'radar',
      symbol: 'circle',
      symbolSize: 7,
      data: [{
        value: abilityDimensions.value.map((d: any) => d.score),
        name: '能力得分',
        areaStyle: { color: 'rgba(117,104,248,.22)' },
        lineStyle: { color: riskColor.value, width: 2.5 },
        itemStyle: { color: '#ffffff', borderColor: riskColor.value, borderWidth: 2 }
      }]
    }]
  }
})

onMounted(() => {
  const id = route.params.id as string
  if (id) {
    assessmentApi.getRecord(Number(id))
      .then(r => { record.value = r })
      .catch(() => {})
      .finally(() => { loading.value = false })
  } else {
    record.value = {
      id: 1,
      overall_score: 78.5,
      risk_level: 'medium',
      test_date: new Date().toISOString(),
      dimensions: [
        { label: '平衡能力', score: 75 },
        { label: '柔韧性', score: 82 },
        { label: '上肢力量', score: 70 },
        { label: '核心力量', score: 78 },
        { label: '对称性', score: 85 }
      ],
      posture_problems: [
        {
          name: '圆肩', severity: 'moderate',
          tight: ['胸大肌', '胸小肌', '上斜方肌'],
          weak: ['前锯肌', '中斜方肌', '下斜方肌'],
          cause: '长期伏案工作，缺乏背部训练',
          exercises: {
            stretch: [{ name: '胸部拉伸', sets: '3组 × 30秒' }],
            strength: [{ name: 'YTWL训练', sets: '3组 × 12次' }]
          }
        },
        {
          name: '骨盆前倾', severity: 'mild',
          tight: ['髂腰肌', '竖脊肌'],
          weak: ['腹直肌', '臀大肌'],
          cause: '久坐导致髋屈肌紧张',
          exercises: {
            stretch: [{ name: '髋屈肌拉伸', sets: '3组 × 30秒' }],
            strength: [{ name: '桥式', sets: '3组 × 15次' }]
          }
        }
      ],
      asymmetry_findings: [
        { joint: '肩关节', severity: 'mild', diff_pct: 8, side_limited: 'left' },
        { joint: '髋关节', severity: 'mild', diff_pct: 5, side_limited: 'right' }
      ],
      muscle_analysis: {
        tight_count: 5,
        weak_count: 4,
        tight_muscles: [
          { name: '胸大肌', en: 'Pectoralis Major' },
          { name: '上斜方肌', en: 'Upper Trapezius' },
          { name: '髂腰肌', en: 'Iliopsoas' }
        ],
        weak_muscles: [
          { name: '前锯肌', en: 'Serratus Anterior' },
          { name: '中斜方肌', en: 'Middle Trapezius' },
          { name: '臀大肌', en: 'Gluteus Maximus' }
        ]
      },
      suggestions: [
        '建议每周进行3-4次针对性训练，每次30-45分钟',
        '注意工作姿势，每小时起身活动5分钟',
        '优先改善圆肩问题，加强背部肌肉训练',
        '配合呼吸训练，改善核心稳定性'
      ],
      summary: '整体体态中等，主要问题为圆肩和轻度骨盆前倾。建议加强背部和核心肌群训练，注意日常姿势矫正。坚持训练4-6周后可进行复查评估。'
    }
    loading.value = false
  }
})

function goBack() {
  router.push('/assessment')
}

function retry() {
  router.push('/assessment')
}

function getSeverityType(severity: string) {
  switch (severity) {
    case 'severe': return 'error'
    case 'moderate': return 'warning'
    case 'mild': return 'info'
    default: return 'default'
  }
}

function getAbilityMeta(score: number) {
  if (score >= 85) return { label: '优秀', color: '#56b98f', soft: '#eaf8f1' }
  if (score >= 70) return { label: '良好', color: '#7568f8', soft: '#efedff' }
  if (score >= 50) return { label: '中等', color: '#f2a94a', soft: '#fff5e6' }
  return { label: '待改善', color: '#ef6a6a', soft: '#fff0f0' }
}

function getMuscleCount(type: 'tight' | 'weak') {
  const analysis = record.value?.muscle_analysis
  if (!analysis) return 0
  const muscles = analysis[`${type}_muscles`]
  if (Array.isArray(muscles) && muscles.length) return muscles.length
  const count = Number(analysis[`${type}_count`])
  return Number.isFinite(count) && count > 0 ? count : 0
}
</script>

<script lang="ts">
export default { name: 'AssessmentReportView' }
</script>

<template>
  <div class="report-page">
    <div class="tech-grid" aria-hidden="true"></div>

    <n-spin v-if="loading" class="loading-state">
      <template #description>加载中...</template>
    </n-spin>

    <template v-else-if="record">
      <section class="hero-banner report-card reveal-card">
        <div class="hero-copy">
          <div class="eyebrow">AI POSTURE ANALYSIS</div>
          <h1>体态评估报告</h1>
          <p class="report-date">评估时间 · {{ new Date(record.test_date).toLocaleDateString() }}</p>

          <div class="hero-score-row">
            <div
              class="score-ring"
              :style="{
                '--score-color': riskColor,
                '--score-angle': `${Math.min(Number(record.overall_score) || 0, 100) * 3.6}deg`
              }"
            >
              <div class="score-ring-inner">
                <strong :style="{ color: riskColor }">{{ record.overall_score?.toFixed(1) }}</strong>
                <span>/ 100</span>
              </div>
            </div>
            <div class="score-copy">
              <n-tag round size="large" class="risk-pill" :style="{ color: riskColor, borderColor: riskColor + '55', background: riskColor + '12' }">
                {{ riskLabel }}
              </n-tag>
              <p>{{ record.summary || '本次AI体态分析已完成，请结合下方能力与问题分析制定改善方案。' }}</p>
            </div>
          </div>
        </div>

        <div class="hero-visual">
          <div class="hero-glow"></div>
          <img src="/media/pictures/gesture_report_head.png" alt="体态评估报告示意图">
        </div>
      </section>

      <section class="report-card analysis-card reveal-card delay-1">
        <div class="section-heading">
          <div>
            <span class="section-kicker">ABILITY PROFILE</span>
            <h2>五维能力分析</h2>
          </div>
          <p>雷达趋势与分项表现一目了然</p>
        </div>

        <div class="analysis-layout">
          <div class="radar-panel">
            <v-chart v-if="chartOption" :option="chartOption" class="radar-chart" autoresize />
          </div>
          <div class="ability-overview">
            <h3>能力概览</h3>
            <div v-for="(dimension, index) in abilityDimensions" :key="dimension.label" class="ability-item">
              <div class="ability-icon" :style="{ color: getAbilityMeta(dimension.score).color, background: getAbilityMeta(dimension.score).soft }">
                {{ DIMENSION_ICONS[index] || '能' }}
              </div>
              <div class="ability-main">
                <div class="ability-title-row">
                  <strong>{{ dimension.label }}</strong>
                  <span class="ability-status" :style="{ color: getAbilityMeta(dimension.score).color, background: getAbilityMeta(dimension.score).soft }">
                    {{ getAbilityMeta(dimension.score).label }}
                  </span>
                  <b>{{ dimension.score }}</b>
                </div>
                <div class="progress-track">
                  <span :style="{ width: `${Math.min(dimension.score, 100)}%`, background: getAbilityMeta(dimension.score).color }"></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section v-if="record.posture_problems?.length" class="report-card reveal-card delay-2">
        <div class="section-heading">
          <div>
            <span class="section-kicker">POSTURE FINDINGS</span>
            <h2>体态问题分析</h2>
          </div>
          <p>点击问题卡片查看原因、肌群与训练重点</p>
        </div>

        <n-collapse accordion class="issue-collapse">
          <n-collapse-item v-for="(problem, index) in record.posture_problems" :key="index" :name="index">
            <template #header>
              <div class="issue-header">
                <span class="severity-dot" :class="`severity-${problem.severity}`"></span>
                <div class="issue-title">
                  <strong>{{ problem.name }}</strong>
                  <span>{{ problem.cause || '已检测到姿态偏差，建议进行针对性改善' }}</span>
                </div>
                <n-tag :type="getSeverityType(problem.severity)" round size="small">
                  {{ SEVERITY_LABELS[problem.severity] || problem.severity }}
                </n-tag>
              </div>
            </template>

            <div class="issue-detail-grid">
              <div v-if="problem.cause" class="detail-block cause-block">
                <span>形成原因</span>
                <p>{{ problem.cause }}</p>
              </div>
              <div v-if="problem.impact" class="detail-block impact-block">
                <span>可能影响</span>
                <p>{{ problem.impact }}</p>
              </div>
              <div v-if="problem.tight?.length" class="detail-block">
                <span>紧张肌群</span>
                <div class="tag-list">
                  <n-tag v-for="(muscle, i) in problem.tight" :key="i" type="error" size="small" round>{{ muscle }}</n-tag>
                </div>
              </div>
              <div v-if="problem.weak?.length" class="detail-block">
                <span>薄弱肌群</span>
                <div class="tag-list">
                  <n-tag v-for="(muscle, i) in problem.weak" :key="i" type="info" size="small" round>{{ muscle }}</n-tag>
                </div>
              </div>
            </div>

            <div v-if="problem.exercises" class="exercise-area">
              <div v-if="problem.exercises.stretch?.length" class="exercise-column">
                <h4>拉伸放松</h4>
                <div v-for="(exercise, i) in problem.exercises.stretch" :key="i" class="exercise-row">
                  <span>{{ exercise.name || exercise }}</span><b v-if="exercise.sets">{{ exercise.sets }}</b>
                </div>
              </div>
              <div v-if="problem.exercises.strength?.length" class="exercise-column">
                <h4>激活强化</h4>
                <div v-for="(exercise, i) in problem.exercises.strength" :key="i" class="exercise-row">
                  <span>{{ exercise.name || exercise }}</span><b v-if="exercise.sets">{{ exercise.sets }}</b>
                </div>
              </div>
            </div>
          </n-collapse-item>
        </n-collapse>
      </section>

      <section v-if="record.muscle_analysis" class="report-card reveal-card">
        <div class="section-heading">
          <div>
            <span class="section-kicker">MUSCLE BALANCE</span>
            <h2>肌肉分析</h2>
          </div>
          <p>识别影响姿态稳定性的关键肌群</p>
        </div>

        <div class="muscle-layout">
          <div class="muscle-card tight-card">
            <div class="muscle-card-head">
              <div class="muscle-symbol"><n-icon :component="FitnessOutline" /></div>
              <div><span>需要放松</span><h3>紧张肌群</h3></div>
              <strong v-if="getMuscleCount('tight')" class="muscle-count">{{ getMuscleCount('tight') }}<small>处</small></strong>
              <span v-else class="muscle-clear">暂无异常</span>
            </div>
            <div class="muscle-chip-list">
              <div v-for="(muscle, i) in record.muscle_analysis.tight_muscles" :key="i" class="muscle-chip">
                <b>{{ muscle.name }}</b><span v-if="muscle.area || muscle.region">{{ muscle.area || muscle.region }}</span><small v-else>{{ muscle.en }}</small>
              </div>
            </div>
          </div>

          <div class="muscle-card weak-card">
            <div class="muscle-card-head">
              <div class="muscle-symbol"><n-icon :component="FlashOutline" /></div>
              <div><span>需要激活</span><h3>薄弱肌群</h3></div>
              <strong v-if="getMuscleCount('weak')" class="muscle-count">{{ getMuscleCount('weak') }}<small>处</small></strong>
              <span v-else class="muscle-clear">暂无异常</span>
            </div>
            <div class="muscle-chip-list">
              <div v-for="(muscle, i) in record.muscle_analysis.weak_muscles" :key="i" class="muscle-chip">
                <b>{{ muscle.name }}</b><span v-if="muscle.area || muscle.region">{{ muscle.area || muscle.region }}</span><small v-else>{{ muscle.en }}</small>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section v-if="record.suggestions?.length" class="report-card reveal-card">
        <div class="section-heading">
          <div>
            <span class="section-kicker">AI TRAINING PATH</span>
            <h2>训练建议</h2>
          </div>
          <p>循序渐进完成阶段改善</p>
        </div>

        <div class="training-timeline">
          <div v-for="(suggestion, index) in record.suggestions" :key="index" class="timeline-step">
            <div class="week-marker"><span>WEEK</span><strong>{{ index + 1 }}</strong></div>
            <div class="timeline-line"><i></i></div>
            <div class="timeline-copy">
              <h3>{{ WEEK_STAGES[index] || '持续巩固' }}</h3>
              <p>{{ suggestion }}</p>
            </div>
          </div>
        </div>
      </section>

      <section v-if="record.summary" class="ai-summary-card reveal-card">
        <div class="ai-summary-icon"><n-icon :component="BulbOutline" /></div>
        <div class="ai-summary-content">
          <span>AI综合建议</span>
          <h2>保持耐心，身体会回应每一次正确训练</h2>
          <div class="summary-metrics">
            <div><small>综合评分</small><strong>{{ record.overall_score?.toFixed(1) }}</strong></div>
            <div><small>当前风险</small><strong :style="{ color: riskColor }">{{ riskLabel }}</strong></div>
            <div><small>严重问题</small><strong>{{ severeProblemCount }} 项</strong></div>
          </div>
          <p>{{ record.summary }}</p>
        </div>
      </section>

      <footer class="action-footer">
        <n-button size="large" class="primary-action" @click="retry">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          重新评估
        </n-button>
        <n-button size="large" class="secondary-action" @click="goBack">
          <template #icon><n-icon :component="ArrowBackOutline" /></template>
          返回
        </n-button>
      </footer>
    </template>

    <n-result v-else status="404" title="未找到评估记录">
      <template #footer>
        <n-button @click="goBack">返回体态评估</n-button>
      </template>
    </n-result>
  </div>
</template>

<style scoped>
.report-page {
  position: relative;
  isolation: isolate;
  width: min(1280px, calc(100% - 48px));
  margin: 0 auto;
  padding: 8px 0 40px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  color: #19213a;
}

.tech-grid {
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background:
    radial-gradient(circle at 13% 18%, rgba(117, 104, 248, .10) 0 2px, transparent 3px),
    radial-gradient(circle at 86% 32%, rgba(95, 188, 204, .10) 0 2px, transparent 3px),
    linear-gradient(rgba(117, 104, 248, .025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(117, 104, 248, .025) 1px, transparent 1px);
  background-size: 130px 130px, 170px 170px, 46px 46px, 46px 46px;
}

.loading-state { display: flex; justify-content: center; padding: 100px 0; }

.report-card {
  background: rgba(255, 255, 255, .96);
  border: 1px solid rgba(110, 118, 150, .09);
  border-radius: 16px;
  box-shadow: 0 12px 34px rgba(43, 50, 83, .065);
  padding: 30px 34px;
  transition: transform .25s ease, box-shadow .25s ease;
}

.report-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 42px rgba(43, 50, 83, .10);
}

.hero-banner {
  min-height: 300px;
  display: grid;
  grid-template-columns: 58% 42%;
  align-items: center;
  overflow: hidden;
  padding: 30px 42px;
  background: linear-gradient(135deg, #ffffff 0%, #f2f4ff 100%);
}

.hero-copy { position: relative; z-index: 2; }
.eyebrow, .section-kicker {
  display: block;
  color: #7568f8;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .16em;
}

.hero-copy h1 {
  margin: 7px 0 4px;
  font-size: clamp(30px, 3vw, 44px);
  line-height: 1.15;
  letter-spacing: -.03em;
}

.report-date { margin: 0; color: #8490a8; font-size: 14px; }
.hero-score-row { display: flex; align-items: center; gap: 22px; margin-top: 22px; }

.score-ring {
  --score-color: #7568f8;
  --score-angle: 0deg;
  width: 116px;
  height: 116px;
  flex: 0 0 116px;
  border-radius: 50%;
  padding: 8px;
  background: conic-gradient(var(--score-color) var(--score-angle), rgba(117, 104, 248, .10) 0);
  box-shadow: 0 10px 26px rgba(86, 79, 164, .12);
}

.score-ring-inner {
  width: 100%; height: 100%; border-radius: 50%; background: #fff;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.score-ring strong { font-size: 30px; line-height: 1; white-space: nowrap; }
.score-ring span { margin-top: 5px; color: #9aa3b5; font-size: 11px; }
.score-copy { max-width: 440px; }
.risk-pill { font-weight: 700; }
.score-copy p { margin: 10px 0 0; color: #59657b; font-size: 14px; line-height: 1.75; }

.hero-visual { position: relative; height: 252px; display: flex; align-items: center; justify-content: center; }
.hero-glow { position: absolute; width: 76%; aspect-ratio: 1; border-radius: 50%; background: rgba(133, 119, 255, .14); filter: blur(42px); }
.hero-visual img { position: relative; z-index: 1; width: 100%; height: 250px; object-fit: contain; filter: saturate(.86); mix-blend-mode: multiply; opacity: 0.5; }

.section-heading { display: flex; justify-content: space-between; align-items: end; gap: 24px; margin-bottom: 24px; }
.section-heading h2 { margin: 5px 0 0; font-size: 23px; letter-spacing: -.02em; }
.section-heading p { margin: 0; color: #929bad; font-size: 13px; }
.compact-heading { margin-bottom: 18px; }

.analysis-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(420px, .95fr); gap: 28px; align-items: stretch; }
.radar-panel { min-height: 390px; border-radius: 14px; background: linear-gradient(145deg, #fbfbff, #f6f7ff); border: 1px solid #efeffa; }
.radar-chart { width: 100%; height: 390px; }
.ability-overview { padding: 22px 24px; border-radius: 14px; background: #fafaff; }
.ability-overview h3 { margin: 0 0 16px; font-size: 16px; }
.ability-item { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid #eceef5; }
.ability-item:last-child { border-bottom: 0; }
.ability-icon { width: 36px; height: 36px; border-radius: 11px; display: grid; place-items: center; font-size: 13px; font-weight: 800; }
.ability-main { flex: 1; min-width: 0; }
.ability-title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.ability-title-row strong { flex: 1; font-size: 14px; }
.ability-title-row b { width: 28px; text-align: right; font-size: 16px; }
.ability-status { padding: 3px 8px; border-radius: 999px; font-size: 11px; font-weight: 700; }
.progress-track { height: 7px; overflow: hidden; border-radius: 99px; background: #e9ebf2; }
.progress-track span { display: block; height: 100%; border-radius: inherit; animation: grow-bar 1.15s cubic-bezier(.22, 1, .36, 1) both; }

.issue-collapse { display: flex; flex-direction: column; gap: 12px; }
:deep(.issue-collapse .n-collapse-item) { margin: 0; padding: 0 20px; border: 1px solid #eceef5; border-radius: 14px; background: #fbfbfd; transition: border-color .2s, background .2s; }
:deep(.issue-collapse .n-collapse-item:hover) { border-color: rgba(117, 104, 248, .28); background: #fff; }
:deep(.issue-collapse .n-collapse-item__header) { padding: 17px 0; }
:deep(.issue-collapse .n-collapse-item__content-inner) { padding: 0 0 20px; }
.issue-header { flex: 1; display: flex; align-items: center; gap: 12px; padding-right: 10px; }
.severity-dot { width: 10px; height: 10px; flex: 0 0 10px; border-radius: 50%; box-shadow: 0 0 0 5px rgba(117, 104, 248, .08); }
.severity-severe { background: #ef6a6a; }
.severity-moderate { background: #f2a94a; }
.severity-mild { background: #6f9eea; }
.issue-title { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.issue-title strong { font-size: 16px; color: #222a42; }
.issue-title span { overflow: hidden; color: #8b94a8; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.issue-detail-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.detail-block { padding: 14px 16px; border-radius: 12px; background: #f6f7fb; }
.detail-block > span { color: #8a93a7; font-size: 11px; font-weight: 700; }
.detail-block p { margin: 6px 0 0; color: #47536a; font-size: 13px; line-height: 1.65; }
.cause-block { background: #fff7eb; }
.impact-block { background: #fff0f0; }
.tag-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.exercise-area { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 12px; }
.exercise-column { padding: 14px 16px; border-radius: 12px; background: #f1efff; }
.exercise-column:nth-child(2) { background: #ebf8f2; }
.exercise-column h4 { margin: 0 0 8px; font-size: 13px; }
.exercise-row { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; color: #4d5870; font-size: 13px; }
.exercise-row b { color: #7568f8; font-size: 12px; white-space: nowrap; }

.muscle-layout { display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; }
.muscle-card { padding: 22px; border-radius: 15px; border: 1px solid transparent; }
.tight-card { background: #fff4f2; border-color: #fde5e1; }
.weak-card { background: #f1efff; border-color: #e4e0ff; }
.muscle-card-head { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
.muscle-symbol { width: 46px; height: 46px; display: grid; place-items: center; border-radius: 13px; color: #e16a5f; background: #fff; font-size: 22px; box-shadow: 0 6px 16px rgba(135, 73, 63, .08); }
.weak-card .muscle-symbol { color: #7568f8; }
.muscle-card-head > div:nth-child(2) { flex: 1; }
.muscle-card-head span { color: #939bad; font-size: 11px; }
.muscle-card-head h3 { margin: 2px 0 0; font-size: 18px; }
.muscle-card-head > strong { font-size: 31px; color: #e16a5f; }
.weak-card .muscle-card-head > strong { color: #7568f8; }
.muscle-count { display: inline-flex; align-items: baseline; gap: 3px; }
.muscle-count small { font-size: 11px; font-weight: 600; }
.muscle-clear { padding: 6px 10px; border-radius: 999px; color: #4d9f7b !important; background: rgba(255,255,255,.76); font-size: 11px !important; font-weight: 700; }
.muscle-chip-list { display: flex; flex-wrap: wrap; gap: 8px; }
.muscle-chip { min-width: 128px; display: flex; flex-direction: column; padding: 9px 12px; border-radius: 10px; background: rgba(255,255,255,.76); }
.muscle-chip b { font-size: 13px; }
.muscle-chip span, .muscle-chip small { margin-top: 2px; color: #9aa1b1; font-size: 10px; }

.training-timeline { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0; }
.timeline-step { position: relative; text-align: center; padding: 0 10px; }
.week-marker { position: relative; z-index: 2; width: 58px; height: 58px; margin: 0 auto 14px; border-radius: 18px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #fff; background: linear-gradient(135deg, #6d5df6, #8e79ff); box-shadow: 0 10px 22px rgba(109, 93, 246, .22); }
.week-marker span { font-size: 8px; letter-spacing: .1em; }
.week-marker strong { font-size: 20px; line-height: 1.1; }
.timeline-line { position: absolute; top: 28px; left: 0; right: 0; height: 2px; background: #e5e2ff; }
.timeline-step:first-child .timeline-line { left: 50%; }
.timeline-step:last-child .timeline-line { right: 50%; }
.timeline-copy h3 { margin: 0 0 7px; font-size: 15px; }
.timeline-copy p { margin: 0; color: #818b9f; font-size: 12px; line-height: 1.65; }

.ai-summary-card { display: flex; gap: 22px; padding: 28px 32px; border-radius: 16px; background: linear-gradient(135deg, #fff7e9, #fffaf2); border: 1px solid #fae7c9; box-shadow: 0 12px 32px rgba(152, 106, 38, .07); }
.ai-summary-icon { width: 52px; height: 52px; flex: 0 0 52px; display: grid; place-items: center; border-radius: 15px; color: #e69a2e; background: #fff; font-size: 25px; box-shadow: 0 8px 18px rgba(151, 101, 28, .10); }
.ai-summary-content { flex: 1; }
.ai-summary-content > span { color: #d98923; font-size: 12px; font-weight: 800; }
.ai-summary-content h2 { margin: 4px 0 16px; font-size: 20px; }
.summary-metrics { display: flex; gap: 12px; margin-bottom: 15px; }
.summary-metrics div { min-width: 112px; padding: 9px 12px; border-radius: 10px; background: rgba(255,255,255,.72); display: flex; flex-direction: column; }
.summary-metrics small { color: #a18d70; font-size: 10px; }
.summary-metrics strong { margin-top: 2px; font-size: 15px; }
.ai-summary-content > p { margin: 0; color: #685b49; line-height: 1.75; }

.action-footer { display: flex; justify-content: center; gap: 12px; padding: 10px 0 2px; }
.primary-action, .secondary-action { min-width: 190px; height: 50px; border-radius: 12px !important; font-weight: 700; transition: transform .2s ease, box-shadow .2s ease; }
.primary-action { color: #fff !important; border: 0 !important; background: linear-gradient(135deg, #6d5df6, #8e79ff) !important; box-shadow: 0 10px 24px rgba(109, 93, 246, .24); }
.secondary-action { color: #6358d9 !important; border-color: #d9d5ff !important; background: #fff !important; }
.primary-action:hover, .secondary-action:hover { transform: translateY(-2px); }

.reveal-card { animation: card-enter .62s cubic-bezier(.22, 1, .36, 1) both; }
.delay-1 { animation-delay: .08s; }
.delay-2 { animation-delay: .16s; }
@keyframes card-enter { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }
@keyframes grow-bar { from { width: 0; } }

@media (max-width: 980px) {
  .hero-banner { grid-template-columns: 1fr; }
  .hero-visual { display: none; }
  .analysis-layout { grid-template-columns: 1fr; }
  .training-timeline { grid-template-columns: repeat(2, 1fr); gap: 28px 0; }
  .timeline-line { display: none; }
}

@media (max-width: 720px) {
  .report-page { width: min(100% - 24px, 1280px); }
  .report-card, .hero-banner { padding: 22px 18px; }
  .hero-score-row, .section-heading { align-items: flex-start; flex-direction: column; }
  .analysis-layout, .issue-detail-grid, .exercise-area, .muscle-layout { grid-template-columns: 1fr; }
  .training-timeline { grid-template-columns: 1fr; }
  .ai-summary-card { padding: 22px 18px; }
  .summary-metrics { flex-wrap: wrap; }
  .action-footer { flex-direction: column; }
  .primary-action, .secondary-action { width: 100%; }
}
</style>
