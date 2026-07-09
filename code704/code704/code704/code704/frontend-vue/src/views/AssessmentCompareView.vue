<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { LegendComponent, TooltipComponent } from 'echarts/components'
import { assessmentApi } from '../services/api'
import { NAlert, NButton, NEmpty, NIcon, NSelect, NSpin, NTag } from 'naive-ui'
import { ArrowBackOutline, DocumentTextOutline, RefreshOutline } from '@vicons/ionicons5'

use([CanvasRenderer, RadarChart, LegendComponent, TooltipComponent])

type AssessmentSummary = {
  id: number
  test_date: string
  overall_score: number
  risk_level: string
  balance_score: number
  flexibility_score: number
  upper_limb_score: number
  core_score: number
  symmetry_score: number
}

type Dimension = {
  key: keyof AssessmentSummary
  label: string
  before: number
  after: number
  delta: number
}

const route = useRoute()
const router = useRouter()
const records = ref<AssessmentSummary[]>([])
const baselineId = ref<number | null>(null)
const currentId = ref<number | null>(null)
const baseline = ref<any>(null)
const current = ref<any>(null)
const loading = ref(true)
const detailLoading = ref(false)
const error = ref('')
let requestVersion = 0

const riskLabels: Record<string, string> = {
  low: '低风险',
  medium: '中风险',
  high: '高风险'
}

const riskTypes: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
  low: 'success',
  medium: 'warning',
  high: 'error'
}

function formatDate(value: string) {
  if (!value) return '未知日期'
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}

function optionLabel(record: AssessmentSummary) {
  return `${formatDate(record.test_date)} · ${Number(record.overall_score || 0).toFixed(1)} 分`
}

const baselineOptions = computed(() => records.value.map(record => ({
  label: optionLabel(record),
  value: record.id,
  disabled: record.id === currentId.value
})))

const currentOptions = computed(() => records.value.map(record => ({
  label: optionLabel(record),
  value: record.id,
  disabled: record.id === baselineId.value
})))

const dimensions = computed<Dimension[]>(() => {
  if (!baseline.value || !current.value) return []
  const defs: Array<{ key: keyof AssessmentSummary; label: string }> = [
    { key: 'balance_score', label: '平衡能力' },
    { key: 'flexibility_score', label: '柔韧性' },
    { key: 'upper_limb_score', label: '上肢能力' },
    { key: 'core_score', label: '核心稳定' },
    { key: 'symmetry_score', label: '身体对称' }
  ]
  return defs.map(item => {
    const before = Number(baseline.value[item.key] || 0)
    const after = Number(current.value[item.key] || 0)
    return { ...item, before, after, delta: after - before }
  })
})

const overallDelta = computed(() => (
  Number(current.value?.overall_score || 0) - Number(baseline.value?.overall_score || 0)
))

const daysApart = computed(() => {
  if (!baseline.value || !current.value) return 0
  const diff = new Date(current.value.test_date).getTime() - new Date(baseline.value.test_date).getTime()
  return Math.abs(Math.round(diff / 86400000))
})

const improvedDimensions = computed(() => dimensions.value.filter(item => item.delta > 0.05).length)
const declinedDimensions = computed(() => dimensions.value.filter(item => item.delta < -0.05).length)

const radarOption = computed(() => ({
  animationDuration: 700,
  color: ['#94a3b8', '#6d5df6'],
  tooltip: { trigger: 'item' },
  legend: { bottom: 8, data: ['基准评估', '本次评估'] },
  radar: {
    center: ['50%', '46%'],
    radius: '63%',
    splitNumber: 5,
    indicator: dimensions.value.map(item => ({ name: item.label, max: 100 })),
    axisName: { color: '#475569', fontSize: 12, fontWeight: 600 },
    axisLine: { lineStyle: { color: 'rgba(109,93,246,.16)' } },
    splitLine: { lineStyle: { color: 'rgba(109,93,246,.14)' } },
    splitArea: { areaStyle: { color: ['#fff', '#faf9ff'] } }
  },
  series: [{
    type: 'radar',
    symbolSize: 6,
    data: [
      {
        name: '基准评估',
        value: dimensions.value.map(item => item.before),
        areaStyle: { color: 'rgba(148,163,184,.12)' },
        lineStyle: { width: 2 }
      },
      {
        name: '本次评估',
        value: dimensions.value.map(item => item.after),
        areaStyle: { color: 'rgba(109,93,246,.20)' },
        lineStyle: { width: 3 }
      }
    ]
  }]
}))

function problemName(problem: any) {
  return String(problem?.name || problem?.label || problem?.problem || '未命名问题')
}

const baselineProblemMap = computed(() => new Map(
  (baseline.value?.posture_problems || []).map((problem: any) => [problemName(problem), problem])
))
const currentProblemMap = computed(() => new Map(
  (current.value?.posture_problems || []).map((problem: any) => [problemName(problem), problem])
))

const resolvedProblems = computed(() => Array.from(baselineProblemMap.value.values())
  .filter((problem: any) => !currentProblemMap.value.has(problemName(problem))))
const newProblems = computed(() => Array.from(currentProblemMap.value.values())
  .filter((problem: any) => !baselineProblemMap.value.has(problemName(problem))))
const persistentProblems = computed(() => Array.from(currentProblemMap.value.values())
  .filter((problem: any) => baselineProblemMap.value.has(problemName(problem))))

function severityLabel(value: string) {
  return ({ severe: '严重', moderate: '中度', mild: '轻度' } as Record<string, string>)[value] || value || '待关注'
}

function severityType(value: string): 'error' | 'warning' | 'info' | 'default' {
  return value === 'severe' ? 'error' : value === 'moderate' ? 'warning' : value === 'mild' ? 'info' : 'default'
}

async function loadDetails() {
  if (!baselineId.value || !currentId.value || baselineId.value === currentId.value) return
  const version = ++requestVersion
  detailLoading.value = true
  error.value = ''
  try {
    const [before, after] = await Promise.all([
      assessmentApi.getRecord(baselineId.value),
      assessmentApi.getRecord(currentId.value)
    ])
    if (version !== requestVersion) return
    baseline.value = before
    current.value = after
  } catch (err) {
    console.error('加载评估对比失败', err)
    if (version === requestVersion) error.value = '评估详情加载失败，请稍后重试'
  } finally {
    if (version === requestVersion) detailLoading.value = false
  }
}

async function loadRecords() {
  loading.value = true
  error.value = ''
  try {
    records.value = await assessmentApi.getRecords() as AssessmentSummary[]
    const requestedId = Number(route.params.id)
    const requestedIndex = records.value.findIndex(item => item.id === requestedId)
    const currentIndex = requestedIndex >= 0 ? requestedIndex : 0
    currentId.value = records.value[currentIndex]?.id ?? null
    baselineId.value = records.value[currentIndex + 1]?.id
      ?? records.value.find(item => item.id !== currentId.value)?.id
      ?? null
    await loadDetails()
  } catch (err) {
    console.error('加载评估记录失败', err)
    error.value = '历史评估记录加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

watch([baselineId, currentId], ([nextBaseline, nextCurrent], [oldBaseline, oldCurrent]) => {
  if (nextBaseline && nextCurrent && (nextBaseline !== oldBaseline || nextCurrent !== oldCurrent)) loadDetails()
})

function viewReport(id: number | null) {
  if (id) router.push(`/assessment/report/${id}`)
}

onMounted(loadRecords)
</script>

<script lang="ts">
export default { name: 'AssessmentCompareView' }
</script>

<template>
  <div class="compare-page">
    <header class="page-header">
      <div>
        <span class="eyebrow">POSTURE PROGRESS</span>
        <h1>体态评估对比分析</h1>
        <p>选择两次评估，查看分数、能力维度与体态问题的真实变化。</p>
      </div>
      <n-button @click="router.push('/assessment')">
        <template #icon><n-icon :component="ArrowBackOutline" /></template>
        返回评估
      </n-button>
    </header>

    <n-alert v-if="error" type="error" :title="error" closable @close="error = ''">
      <template #action><n-button size="small" @click="loadRecords">重试</n-button></template>
    </n-alert>

    <n-spin :show="loading" description="正在加载历史评估...">
      <div v-if="records.length >= 2" class="content-stack">
        <section class="selector-card">
          <div class="selector-block">
            <span class="selector-index baseline-index">A</span>
            <div><label>基准评估</label><small>用于作为改善前参照</small></div>
            <n-select v-model:value="baselineId" :options="baselineOptions" filterable />
          </div>
          <div class="compare-arrow">→</div>
          <div class="selector-block">
            <span class="selector-index current-index">B</span>
            <div><label>本次评估</label><small>与基准评估进行比较</small></div>
            <n-select v-model:value="currentId" :options="currentOptions" filterable />
          </div>
        </section>

        <n-spin :show="detailLoading" description="正在计算对比结果...">
          <template v-if="baseline && current">
            <div class="comparison-results">
            <section class="summary-grid">
              <div class="summary-card score-card">
                <span>综合评分变化</span>
                <div class="score-comparison">
                  <b>{{ Number(baseline.overall_score || 0).toFixed(1) }}</b>
                  <i>→</i>
                  <strong>{{ Number(current.overall_score || 0).toFixed(1) }}</strong>
                </div>
                <em :class="overallDelta >= 0 ? 'positive' : 'negative'">
                  {{ overallDelta >= 0 ? '+' : '' }}{{ overallDelta.toFixed(1) }} 分
                </em>
              </div>
              <div class="summary-card">
                <span>评估间隔</span><strong>{{ daysApart }}</strong><small>天</small>
              </div>
              <div class="summary-card">
                <span>改善维度</span><strong class="positive">{{ improvedDimensions }}</strong><small>/ 5 项</small>
              </div>
              <div class="summary-card">
                <span>下降维度</span><strong :class="declinedDimensions ? 'negative' : 'positive'">{{ declinedDimensions }}</strong><small>/ 5 项</small>
              </div>
              <div class="summary-card risk-card">
                <span>风险变化</span>
                <div><n-tag :type="riskTypes[baseline.risk_level] || 'default'">{{ riskLabels[baseline.risk_level] || baseline.risk_level }}</n-tag><i>→</i><n-tag :type="riskTypes[current.risk_level] || 'default'">{{ riskLabels[current.risk_level] || current.risk_level }}</n-tag></div>
              </div>
            </section>

            <section class="analysis-grid">
              <div class="panel radar-panel">
                <div class="panel-heading"><div><span>ABILITY OVERLAY</span><h2>五维能力叠加</h2></div><small>面积越大，综合能力越好</small></div>
                <v-chart :option="radarOption" class="radar-chart" autoresize />
              </div>
              <div class="panel dimension-panel">
                <div class="panel-heading"><div><span>DIMENSION DELTA</span><h2>维度变化明细</h2></div></div>
                <div class="dimension-list">
                  <div v-for="item in dimensions" :key="item.key" class="dimension-row">
                    <div class="dimension-title"><strong>{{ item.label }}</strong><em :class="item.delta >= 0 ? 'positive' : 'negative'">{{ item.delta >= 0 ? '+' : '' }}{{ item.delta.toFixed(1) }}</em></div>
                    <div class="bar-row baseline-bar"><span>基准</span><div><i :style="{ width: `${item.before}%` }"></i></div><b>{{ item.before.toFixed(1) }}</b></div>
                    <div class="bar-row current-bar"><span>本次</span><div><i :style="{ width: `${item.after}%` }"></i></div><b>{{ item.after.toFixed(1) }}</b></div>
                  </div>
                </div>
              </div>
            </section>

            <section class="panel problem-panel">
              <div class="panel-heading"><div><span>ISSUE TRACKING</span><h2>体态问题变化</h2></div><small>根据两次详细报告中的问题清单计算</small></div>
              <div class="problem-columns">
                <div class="problem-column resolved">
                  <div class="problem-title"><span>✓</span><div><h3>已改善</h3><small>{{ resolvedProblems.length }} 项</small></div></div>
                  <div v-if="resolvedProblems.length" class="problem-list"><div v-for="problem in resolvedProblems" :key="problemName(problem)"><strong>{{ problemName(problem) }}</strong><n-tag size="small" type="success">本次未检出</n-tag></div></div>
                  <n-empty v-else size="small" description="暂无已改善问题" />
                </div>
                <div class="problem-column persistent">
                  <div class="problem-title"><span>!</span><div><h3>持续关注</h3><small>{{ persistentProblems.length }} 项</small></div></div>
                  <div v-if="persistentProblems.length" class="problem-list"><div v-for="problem in persistentProblems" :key="problemName(problem)"><strong>{{ problemName(problem) }}</strong><n-tag size="small" :type="severityType(problem.severity)">{{ severityLabel(problem.severity) }}</n-tag></div></div>
                  <n-empty v-else size="small" description="没有持续存在的问题" />
                </div>
                <div class="problem-column added">
                  <div class="problem-title"><span>+</span><div><h3>新增问题</h3><small>{{ newProblems.length }} 项</small></div></div>
                  <div v-if="newProblems.length" class="problem-list"><div v-for="problem in newProblems" :key="problemName(problem)"><strong>{{ problemName(problem) }}</strong><n-tag size="small" :type="severityType(problem.severity)">{{ severityLabel(problem.severity) }}</n-tag></div></div>
                  <n-empty v-else size="small" description="没有新增问题" />
                </div>
              </div>
            </section>

            <footer class="actions">
              <n-button @click="viewReport(baselineId)"><template #icon><n-icon :component="DocumentTextOutline" /></template>查看基准报告</n-button>
              <n-button type="primary" @click="viewReport(currentId)"><template #icon><n-icon :component="DocumentTextOutline" /></template>查看本次报告</n-button>
              <n-button @click="loadDetails"><template #icon><n-icon :component="RefreshOutline" /></template>刷新对比</n-button>
            </footer>
            </div>
          </template>
        </n-spin>
      </div>

      <section v-else-if="!loading" class="empty-card">
        <n-empty description="至少需要两次体态评估才能进行对比分析">
          <template #extra><n-button type="primary" @click="router.push('/assessment')">开始新的评估</n-button></template>
        </n-empty>
      </section>
    </n-spin>
  </div>
</template>

<style scoped>
.comparison-results{display:flex;flex-direction:column;gap:26px}
.compare-page{width:min(1320px,100%);margin:0 auto;padding:8px 8px 44px;color:#1e293b}.page-header{display:flex;align-items:flex-start;justify-content:space-between;gap:32px;margin-bottom:30px}.eyebrow,.panel-heading span{color:#6d5df6;font-size:11px;font-weight:800;letter-spacing:.14em}.page-header h1{margin:6px 0 9px;font-size:30px}.page-header p{margin:0;color:#64748b;line-height:1.7}.content-stack{display:flex;flex-direction:column;gap:26px}.selector-card,.panel,.summary-card,.empty-card{background:#fff;border:1px solid #ececf5;border-radius:20px;box-shadow:0 10px 30px rgba(54,60,110,.06)}.selector-card{display:grid;grid-template-columns:1fr 72px 1fr;align-items:center;padding:28px 32px}.selector-block{display:grid;grid-template-columns:46px minmax(135px,.7fr) minmax(210px,1.3fr);align-items:center;gap:16px}.selector-index{width:42px;height:42px;display:grid;place-items:center;border-radius:13px;font-weight:800}.baseline-index{color:#64748b;background:#eef2f7}.current-index{color:#fff;background:linear-gradient(135deg,#6d5df6,#8b78ff)}.selector-block label{display:block;font-weight:700;margin-bottom:3px}.selector-block small{color:#94a3b8;line-height:1.5}.compare-arrow{text-align:center;color:#8b78ff;font-size:26px}.summary-grid{display:grid;grid-template-columns:1.6fr repeat(3,1fr) 1.4fr;gap:18px}.summary-card{min-height:124px;padding:23px 22px;display:flex;flex-direction:column;justify-content:center}.summary-card>span{color:#8490a8;font-size:12px}.summary-card>strong{margin-top:9px;font-size:30px}.summary-card>small{margin-top:3px;color:#94a3b8}.score-comparison{display:flex;align-items:center;gap:12px;margin:10px 0 2px}.score-comparison b{color:#94a3b8;font-size:22px}.score-comparison strong{color:#6d5df6;font-size:30px}.score-comparison i,.risk-card i{color:#b5bdca;font-style:normal}.score-card em{font-style:normal;font-weight:700}.positive{color:#16a36a!important}.negative{color:#e05252!important}.risk-card>div{display:flex;align-items:center;gap:10px;margin-top:16px}.analysis-grid{display:grid;grid-template-columns:1fr 1fr;gap:26px}.panel{padding:30px 32px}.panel-heading{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;margin-bottom:20px}.panel-heading h2{margin:5px 0 0;font-size:20px}.panel-heading small{color:#94a3b8;line-height:1.6}.radar-chart{height:420px}.dimension-list{display:flex;flex-direction:column}.dimension-row{padding:17px 0;border-bottom:1px solid #f0f1f6}.dimension-row:last-child{border-bottom:0}.dimension-title{display:flex;justify-content:space-between;margin-bottom:12px}.dimension-title em{font-style:normal;font-weight:800}.bar-row{display:grid;grid-template-columns:38px 1fr 46px;align-items:center;gap:11px;margin:8px 0;font-size:11px;color:#8490a8}.bar-row>div{height:8px;overflow:hidden;border-radius:99px;background:#eef0f5}.bar-row i{display:block;height:100%;border-radius:inherit}.baseline-bar i{background:#a8b1c0}.current-bar i{background:linear-gradient(90deg,#6d5df6,#8b78ff)}.bar-row b{text-align:right;color:#475569}.problem-panel{padding:32px}.problem-columns{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}.problem-column{min-height:210px;padding:23px;border-radius:16px}.problem-column.resolved{background:#f0fbf6}.problem-column.persistent{background:#fff8eb}.problem-column.added{background:#fff2f2}.problem-title{display:flex;align-items:center;gap:13px;margin-bottom:19px}.problem-title>span{width:38px;height:38px;display:grid;place-items:center;border-radius:11px;background:#fff;font-size:19px;font-weight:800}.problem-title h3{margin:0 0 2px;font-size:16px}.problem-title small{color:#8490a8}.problem-list{display:flex;flex-direction:column;gap:11px}.problem-list>div{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 13px;border-radius:10px;background:rgba(255,255,255,.78)}.problem-list strong{font-size:13px;line-height:1.5}.actions{display:flex;justify-content:center;gap:14px;padding-top:2px}.empty-card{padding:90px 30px}@media(max-width:1050px){.selector-card{grid-template-columns:1fr;padding:26px}.compare-arrow{margin:5px 0;transform:rotate(90deg)}.selector-block{grid-template-columns:46px 1fr}.selector-block :deep(.n-select){grid-column:1/-1}.summary-grid{grid-template-columns:repeat(2,1fr)}.score-card,.risk-card{grid-column:span 2}.analysis-grid{grid-template-columns:1fr}}@media(max-width:700px){.compare-page{padding-inline:0}.page-header{flex-direction:column;margin-bottom:22px}.content-stack{gap:18px}.summary-grid,.problem-columns{grid-template-columns:1fr;gap:12px}.score-card,.risk-card{grid-column:auto}.panel,.problem-panel{padding:20px}.selector-card{padding:20px}.dimension-row{padding:14px 0}.actions{flex-direction:column}.actions :deep(.n-button){width:100%}}
</style>
