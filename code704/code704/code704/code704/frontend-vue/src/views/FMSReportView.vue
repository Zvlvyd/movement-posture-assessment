<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fmsApi, learningApi } from '../services/api'
import type { FMSRecord } from '../types'
import { NButton, NTag, NSpin, NResult, NIcon, NModal, NSpace, NDescriptions, NDescriptionsItem, NDivider } from 'naive-ui'
import {
  AlertOutline, CheckmarkCircleOutline, BulbOutline,
  ArrowBackOutline
} from '@vicons/ionicons5'

type DimensionAnalysis = {
  dimension?: string
  label?: string
  score?: number
  detail?: string
  advice?: string | string[]
  problem_detail?: string
  recommended_actions?: Array<{
    name?: string
    difficulty?: number
    category?: string
    description?: string
  }>
}

type ReportRecord = FMSRecord & {
  recommendations?: string[]
  scores?: DimensionAnalysis[]
}

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const record = ref<ReportRecord | null>(null)

// ── Action detail modal ──
const detailVisible = ref(false)
const detailAction = ref<any>(null)
const detailLoading = ref(false)
async function openActionDetail(action: any) {
  detailVisible.value = true
  detailLoading.value = true
  try {
    detailAction.value = await learningApi.getLearnableDetail(action.name)
  } catch {
    detailAction.value = { name: action.name, description: action.description || '', difficulty: action.difficulty, category: action.category || '' }
  } finally {
    detailLoading.value = false
  }
}

const RISK_COLORS: Record<string, string> = { high: '#ef4444', medium: '#f59e0b', low: '#10b981' }
const RISK_LABELS: Record<string, string> = { high: '高风险', medium: '中等风险', low: '低风险' }

const riskColor = computed(() => RISK_COLORS[record.value?.risk_level || ''] || '#6D5DF6')
const riskLabel = computed(() => RISK_LABELS[record.value?.risk_level || ''] || record.value?.risk_level)
const riskTagType = computed(() => {
  if (record.value?.risk_level === 'high') return 'error'
  if (record.value?.risk_level === 'medium') return 'warning'
  if (record.value?.risk_level === 'low') return 'success'
  return 'default'
})

function getScoreMeta(score: number) {
  if (score >= 85) {
    return {
      status: '优秀', color: '#55B894', type: 'success',
      tagBackground: '#EEF8F4', tagBorder: '#B9E1D2'
    }
  }
  if (score >= 70) {
    return {
      status: '良好', color: '#D6A93C', type: 'warning',
      tagBackground: '#FFF8E7', tagBorder: '#EED894'
    }
  }
  if (score >= 60) {
    return {
      status: '需关注', color: '#D99452', type: 'warning',
      tagBackground: '#FFF5EA', tagBorder: '#EECDAA'
    }
  }
  return {
    status: '待改善', color: '#E8757D', type: 'error',
    tagBackground: '#FFF1F2', tagBorder: '#F1BEC3'
  }
}

const DIMENSION_GUIDANCE: Record<string, { description: string; focus: string }> = {
  balance: {
    description: '反映身体在静态与动态状态下维持重心、控制姿势变化的能力。',
    focus: '可通过单腿站立、重心转移和不稳定平面训练提升下肢控制。'
  },
  flexibility: {
    description: '反映髋、膝、踝及躯干在动作中的活动范围与协调伸展能力。',
    focus: '优先进行髋踝灵活性、后侧链拉伸和深蹲活动度练习。'
  },
  upper_limb: {
    description: '反映肩带活动度、上肢力量以及肩胛与躯干协同控制水平。',
    focus: '建议结合肩胛稳定、肩关节活动度和渐进式推拉力量练习。'
  },
  core: {
    description: '反映躯干在支撑和肢体运动过程中维持稳定、传递力量的能力。',
    focus: '可采用死虫式、鸟狗式、平板支撑等动作强化抗伸展与抗旋转能力。'
  },
  symmetry: {
    description: '反映身体左右两侧在活动度、力量和动作控制方面的一致程度。',
    focus: '建议增加单侧动作和弱侧专项练习，并持续观察左右差异变化。'
  }
}

function getAdviceText(advice?: string | string[]) {
  if (Array.isArray(advice)) return advice.filter(Boolean).slice(-1)[0] || ''
  return advice || ''
}

function getPerformanceText(label: string, score: number) {
  if (score >= 85) return `${label}表现突出，动作控制和完成质量处于较好水平，可继续保持。`
  if (score >= 70) return `${label}整体表现良好，基础能力较稳定，仍可通过专项练习进一步提升。`
  if (score >= 60) return `${label}存在一定提升空间，复杂动作或疲劳状态下可能出现控制下降。`
  return `${label}是当前需要优先改善的能力，建议降低动作难度并循序进行基础训练。`
}

const dimensions = computed(() => {
  if (!record.value) return []
  return [
    { key: 'balance', label: '平衡能力', score: record.value.balance_score },
    { key: 'flexibility', label: '柔韧性', score: record.value.flexibility_score },
    { key: 'upper_limb', label: '上肢力量', score: record.value.upper_limb_score },
    { key: 'core', label: '核心力量', score: record.value.core_score },
    { key: 'symmetry', label: '对称性', score: record.value.symmetry_score }
  ].map(item => {
    const richDetail = record.value?.scores?.find(score => score.dimension === item.key)
    const numericScore = Number(item.score) || 0
    const guidance = DIMENSION_GUIDANCE[item.key]
    return {
      ...item,
      score: numericScore,
      ...getScoreMeta(numericScore),
      description: richDetail?.detail || guidance.description,
      performance: richDetail?.problem_detail || getPerformanceText(item.label, numericScore),
      trainingFocus: getAdviceText(richDetail?.advice) || guidance.focus,
      recommendedActions: richDetail?.recommended_actions || []
    }
  })
})

const weakestDimension = computed(() => {
  if (!dimensions.value.length) return null
  return dimensions.value.reduce((lowest, item) => item.score < lowest.score ? item : lowest)
})

const recommendations = computed(() => {
  const value = record.value?.recommendations
  return Array.isArray(value) ? value.filter(Boolean) : []
})

const reportSummary = computed(() => {
  if (record.value?.risk_level === 'low') return '整体表现稳定，建议保持规律训练并定期复查。'
  if (record.value?.risk_level === 'high') return '当前存在需要重点关注的能力短板，建议在专业指导下循序改善。'
  return '部分能力仍有提升空间，建议结合问题标签进行针对性训练。'
})

const RADAR_CENTER_X = 190
const RADAR_CENTER_Y = 158
const RADAR_RADIUS = 108

function createRadarPoints(values: number[]) {
  return values.map((value, index) => {
    const angle = (-90 + index * 72) * Math.PI / 180
    const radius = RADAR_RADIUS * Math.max(0, Math.min(100, Number(value) || 0)) / 100
    const x = RADAR_CENTER_X + Math.cos(angle) * radius
    const y = RADAR_CENTER_Y + Math.sin(angle) * radius
    return `${x.toFixed(2)},${y.toFixed(2)}`
  }).join(' ')
}

const radarGridPolygons = [100, 75, 50, 25].map(level =>
  createRadarPoints(Array(5).fill(level))
)

const radarScaleLabels = [0, 25, 50, 75, 100].map(level => ({
  level,
  x: RADAR_CENTER_X + 8,
  y: RADAR_CENTER_Y - RADAR_RADIUS * level / 100 + 3
}))

const radarDataPoints = computed(() =>
  createRadarPoints(dimensions.value.map(item => item.score))
)

const radarAxes = computed(() => dimensions.value.map((item, index) => {
  const angle = (-90 + index * 72) * Math.PI / 180
  const axisX = RADAR_CENTER_X + Math.cos(angle) * RADAR_RADIUS
  const axisY = RADAR_CENTER_Y + Math.sin(angle) * RADAR_RADIUS
  const labelRadius = 137
  const labelX = RADAR_CENTER_X + Math.cos(angle) * labelRadius
  const labelY = RADAR_CENTER_Y + Math.sin(angle) * labelRadius
  const pointRadius = RADAR_RADIUS * Math.max(0, Math.min(100, Number(item.score) || 0)) / 100
  return {
    ...item,
    axisX,
    axisY,
    pointX: RADAR_CENTER_X + Math.cos(angle) * pointRadius,
    pointY: RADAR_CENTER_Y + Math.sin(angle) * pointRadius,
    labelX,
    labelY,
    anchor: Math.abs(Math.cos(angle)) < 0.2 ? 'middle' : Math.cos(angle) > 0 ? 'start' : 'end'
  }
}))

onMounted(() => {
  const id = route.params.id as string
  if (id && id !== '0') {
    fmsApi.getRecord(Number(id))
      .then(r => { record.value = r })
      .catch(() => {})
      .finally(() => { loading.value = false })
  } else {
    record.value = {
      id: 1,
      user_id: 1,
      test_date: new Date().toISOString(),
      balance_score: 75,
      flexibility_score: 82,
      upper_limb_score: 70,
      core_score: 78,
      symmetry_score: 85,
      overall_score: 78,
      risk_level: 'medium',
      problem_tags: [
        { name: '髋部灵活性不足', severity: 'moderate' },
        { name: '核心稳定性有待提高', severity: 'mild' },
        { name: '肩关节活动度受限', severity: 'mild' }
      ]
    }
    loading.value = false
  }
})

function goBack() {
  router.push('/fms')
}

function getSeverityType(severity: string) {
  switch (severity) {
    case 'severe': return 'error'
    case 'moderate': return 'warning'
    case 'mild': return 'info'
    default: return 'default'
  }
}
</script>

<script lang="ts">
export default { name: 'FMSReportView' }
</script>

<template>
  <div class="report-page">
    <n-spin v-if="loading" class="report-loading">
      <template #description>加载中...</template>
    </n-spin>

    <template v-else-if="record">
      <section class="hero-banner report-card fade-in">
        <div class="hero-copy">
          <div class="hero-eyebrow">
            <span class="eyebrow-dot"></span>
            FUNCTIONAL MOVEMENT SCREEN
          </div>
          <h1 class="report-title">FMS 筛查报告</h1>
          <div class="report-meta">
            <span>筛查时间 {{ new Date(record.test_date).toLocaleDateString() }}</span>
            <span class="meta-divider"></span>
            <span>受测用户 #{{ record.user_id }}</span>
          </div>

          <div class="hero-score-area">
            <div
              class="score-ring"
              :style="{
                background: `conic-gradient(${riskColor} ${Math.max(0, Math.min(100, record.overall_score || 0))}%, rgba(255, 255, 255, 0.42) 0)`
              }"
            >
              <div class="score-ring-inner">
                <span class="score-value" :style="{ color: riskColor }">{{ record.overall_score?.toFixed(1) }}</span>
                <span class="score-max">/ 100</span>
              </div>
            </div>
            <div class="score-copy">
              <span class="score-label">综合评分</span>
              <n-tag :type="riskTagType" round size="large" class="risk-tag">{{ riskLabel }}</n-tag>
              <p>{{ reportSummary }}</p>
            </div>
          </div>
        </div>

        <div class="hero-visual" aria-hidden="true">
          <div class="visual-glow"></div>
          <img src="/media/pictures/report_head.png" alt="FMS 报告插画" />
        </div>
      </section>

      <section class="analysis-card report-card fade-in fade-in-delay-1">
        <div class="section-heading">
          <div>
            <span class="section-kicker">ABILITY PROFILE</span>
            <h2>5维度能力分析</h2>
          </div>
          <span class="section-note">满分 100 分</span>
        </div>

        <div class="analysis-grid">
          <div class="radar-panel">
            <div class="panel-title">能力雷达图</div>
            <div class="radar-chart">
              <svg viewBox="0 0 380 320" role="img" aria-label="五维能力雷达图" class="radar-svg">
                <polygon
                  v-for="(points, index) in radarGridPolygons"
                  :key="index"
                  :points="points"
                  class="radar-grid-polygon"
                />
                <line
                  v-for="axis in radarAxes"
                  :key="axis.key + '-axis'"
                  :x1="RADAR_CENTER_X"
                  :y1="RADAR_CENTER_Y"
                  :x2="axis.axisX"
                  :y2="axis.axisY"
                  class="radar-axis-line"
                />
                <text
                  v-for="scale in radarScaleLabels"
                  :key="'scale-' + scale.level"
                  :x="scale.x"
                  :y="scale.y"
                  class="radar-scale-label"
                >{{ scale.level }}</text>
                <polygon
                  :points="radarDataPoints"
                  :style="{ fill: riskColor, stroke: riskColor }"
                  class="radar-data-polygon"
                />
                <g v-for="axis in radarAxes" :key="axis.key + '-point'" class="radar-value-marker">
                  <rect
                    :x="axis.pointX - 14"
                    :y="axis.pointY - 10"
                    width="28"
                    height="20"
                    rx="10"
                    :style="{ stroke: riskColor }"
                    class="radar-value-bg"
                  />
                  <text
                    :x="axis.pointX"
                    :y="axis.pointY + 0.5"
                    text-anchor="middle"
                    class="radar-value-text"
                  >{{ Number(axis.score).toFixed(0) }}</text>
                </g>
                <g v-for="axis in radarAxes" :key="axis.key + '-label'">
                  <text
                    :x="axis.labelX"
                    :y="axis.labelY"
                    :text-anchor="axis.anchor"
                    class="radar-label"
                  >{{ axis.label }}</text>
                </g>
              </svg>
            </div>
          </div>

          <div class="dimension-overview">
            <div class="panel-title">能力概览</div>
            <div v-for="item in dimensions" :key="item.key" class="dimension-row">
              <div class="dimension-topline">
                <span class="dimension-name">{{ item.label }}</span>
                <div class="dimension-result">
                  <strong>{{ Number(item.score).toFixed(0) }}</strong>
                  <n-tag
                    :type="item.type"
                    :color="{ color: item.tagBackground, borderColor: item.tagBorder, textColor: item.color }"
                    round
                    size="small"
                  >{{ item.status }}</n-tag>
                </div>
              </div>
              <div class="progress-track">
                <div
                  class="progress-fill"
                  :style="{ width: Math.max(0, Math.min(100, item.score)) + '%', background: item.color }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="dimension-details-section fade-in fade-in-delay-3">
        <div class="section-heading section-heading-outside">
          <div>
            <span class="section-kicker">DETAILED INTERPRETATION</span>
            <h2>各维度详细分析</h2>
          </div>
          <span class="section-note">结合测试表现与训练方向综合解读</span>
        </div>

        <div class="dimension-detail-list">
          <article
            v-for="(item, index) in dimensions"
            :key="item.key + '-detail'"
            class="dimension-analysis-card report-card"
            :style="{ '--dimension-color': item.color }"
          >
            <div class="dimension-analysis-summary">
              <span class="dimension-index">0{{ index + 1 }}</span>
              <div>
                <h3>{{ item.label }}</h3>
                <p>{{ item.description }}</p>
              </div>
              <div class="dimension-score-badge">
                <strong :style="{ color: item.color }">{{ Number(item.score).toFixed(0) }}</strong>
                <span>分</span>
                <n-tag
                  :type="item.type"
                  :color="{ color: item.tagBackground, borderColor: item.tagBorder, textColor: item.color }"
                  round
                  size="small"
                >{{ item.status }}</n-tag>
              </div>
            </div>

            <div class="dimension-analysis-body">
              <div class="analysis-block">
                <span class="analysis-block-label">表现解读</span>
                <p>{{ item.performance }}</p>
              </div>
              <div class="analysis-block training-block">
                <span class="analysis-block-label">训练重点</span>
                <p>{{ item.trainingFocus }}</p>
              </div>
            </div>

            <div v-if="item.recommendedActions.length" class="recommended-actions">
              <span>推荐动作</span>
              <n-button
                v-for="(action, actionIndex) in item.recommendedActions"
                :key="actionIndex"
                size="tiny"
                round
                type="info"
                @click="openActionDetail(action)"
              >
                {{ action.name }}<template v-if="action.difficulty"> · Lv.{{ action.difficulty }}</template>
              </n-button>
            </div>
          </article>
        </div>
      </section>

      <section class="insights-section fade-in fade-in-delay-3">
        <div class="section-heading section-heading-outside">
          <div>
            <span class="section-kicker">AI INSIGHTS</span>
            <h2>AI 分析报告</h2>
          </div>
        </div>

        <div class="insight-grid">
          <article class="insight-card insight-warning report-card">
            <div class="insight-icon">
              <n-icon size="22" :component="AlertOutline" />
            </div>
            <div class="insight-content">
              <h3>问题标签</h3>
              <p class="insight-intro">根据本次筛查结果标记的重点问题</p>
              <div v-if="record.problem_tags?.length" class="problem-tags">
                <n-tag
                  v-for="(tag, i) in record.problem_tags"
                  :key="i"
                  :type="getSeverityType(tag.severity)"
                  size="medium"
                  round
                >
                  {{ tag.name || tag.dimension }}
                </n-tag>
              </div>
              <p v-else class="empty-copy">本次筛查暂未标记明显问题。</p>
            </div>
          </article>

          <article class="insight-card insight-purple report-card">
            <div class="insight-icon">
              <n-icon size="22" :component="BulbOutline" />
            </div>
            <div class="insight-content">
              <h3>能力解读</h3>
              <p class="insight-intro">从五项能力中快速定位优先关注方向</p>
              <div v-if="weakestDimension" class="focus-dimension">
                <span>当前相对薄弱项</span>
                <strong>{{ weakestDimension.label }} · {{ Number(weakestDimension.score).toFixed(0) }} 分</strong>
              </div>
              <p class="analysis-copy">{{ reportSummary }}</p>
            </div>
          </article>

          <article class="insight-card insight-success report-card">
            <div class="insight-icon">
              <n-icon size="22" :component="CheckmarkCircleOutline" />
            </div>
            <div class="insight-content">
              <h3>训练建议</h3>
              <p class="insight-intro">结合报告数据生成的已有训练建议</p>
              <ul v-if="recommendations.length" class="recommendation-list">
                <li v-for="(item, index) in recommendations" :key="index">{{ item }}</li>
              </ul>
              <p v-else class="empty-copy">暂无独立建议数据，请结合问题标签进行针对性训练。</p>
            </div>
          </article>
        </div>
      </section>

      <div class="action-footer">
        <n-button size="large" class="back-button" @click="goBack">
          <template #icon><n-icon :component="ArrowBackOutline" /></template>
          返回
        </n-button>
      </div>
    </template>

    <n-result v-else status="404" title="未找到筛查记录" />
  </div>

  <!-- Action Detail Modal -->
  <n-modal v-model:show="detailVisible" preset="card" title="动作详情" style="width:min(620px,94vw)">
    <n-spin :show="detailLoading">
      <template v-if="detailAction">
        <n-descriptions :column="2" size="small" bordered>
          <n-descriptions-item label="动作名">{{ detailAction.name }}</n-descriptions-item>
          <n-descriptions-item label="难度">{{ detailAction.difficulty || '-' }}</n-descriptions-item>
          <n-descriptions-item label="分类">{{ detailAction.category || '-' }}</n-descriptions-item>
          <n-descriptions-item label="家族">{{ detailAction.family_name || '-' }}</n-descriptions-item>
          <n-descriptions-item label="强度">{{ detailAction.intensity || '-' }}</n-descriptions-item>
          <n-descriptions-item label="视角">{{ (detailAction.views || ['正面']).join('、') }}</n-descriptions-item>
        </n-descriptions>
        <n-divider />
        <p v-if="detailAction.description" style="color:#64748b;font-size:13px;line-height:1.6">{{ detailAction.description }}</p>
        <div v-if="detailAction.steps?.length" style="margin-top:12px">
          <strong style="font-size:13px">动作步骤</strong>
          <ol style="font-size:13px;color:#64748b;padding-left:18px;margin:6px 0">
            <li v-for="(s, i) in detailAction.steps" :key="i">{{ s }}</li>
          </ol>
        </div>
        <div v-if="detailAction.cues?.length" style="margin-top:12px">
          <strong style="font-size:13px">动作要点</strong>
          <ul style="font-size:13px;color:#64748b;padding-left:18px;margin:6px 0">
            <li v-for="(c, i) in detailAction.cues" :key="i">{{ c }}</li>
          </ul>
        </div>
        <div v-if="detailAction.target_body_parts?.length" style="margin-top:12px">
          <strong style="font-size:13px">目标肌群</strong>
          <n-space style="margin-top:4px">
            <n-tag v-for="(p, i) in detailAction.target_body_parts" :key="i" size="tiny" round type="success">{{ p }}</n-tag>
          </n-space>
        </div>
        <div v-if="detailAction.common_errors?.length" style="margin-top:12px">
          <strong style="font-size:13px">常见错误</strong>
          <ul style="font-size:13px;color:#e74c3c;padding-left:18px;margin:6px 0">
            <li v-for="(e, i) in detailAction.common_errors" :key="i">{{ e.feedback || e.name }}</li>
          </ul>
        </div>
      </template>
      <n-empty v-else description="暂无详情" />
    </n-spin>
    <template #footer><n-button @click="detailVisible = false">关闭</n-button></template>
  </n-modal>
</template>

<style scoped>
.report-page {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 4px 0 28px;
  background: #F7F8FC;
  display: flex;
  flex-direction: column;
  gap: 22px;
  color: #202333;
}

.report-loading {
  display: flex;
  justify-content: center;
  padding: 80px;
}

.report-card {
  background: #fff;
  border: 1px solid rgba(109, 93, 246, 0.07);
  border-radius: 16px;
  box-shadow: 0 10px 32px rgba(42, 35, 92, 0.07);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.report-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 40px rgba(42, 35, 92, 0.11);
}

.hero-banner {
  position: relative;
  min-height: 224px;
  padding: 20px 34px;
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  align-items: center;
  gap: 20px;
  overflow: hidden;
  background:
    radial-gradient(circle at 5% 10%, rgba(142, 121, 255, 0.15), transparent 34%),
    linear-gradient(135deg, #ffffff 0%, #f5f2ff 58%, #eef2ff 100%);
}

.hero-banner::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 5px;
  background: linear-gradient(180deg, #6D5DF6, #8E79FF);
}

.hero-copy,
.hero-visual {
  position: relative;
  z-index: 1;
}

.hero-copy {
  z-index: 2;
}

.hero-eyebrow,
.section-kicker {
  color: #6D5DF6;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.4px;
}

.hero-eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
}

.eyebrow-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #8E79FF;
  box-shadow: 0 0 0 5px rgba(142, 121, 255, 0.12);
}

.report-title {
  margin: 0;
  color: #242238;
  font-size: clamp(26px, 2.7vw, 34px);
  line-height: 1.18;
  font-weight: 800;
  letter-spacing: -0.8px;
}

.report-meta {
  margin-top: 7px;
  display: flex;
  align-items: center;
  gap: 11px;
  color: #737a8d;
  font-size: 13px;
}

.meta-divider {
  width: 1px;
  height: 13px;
  background: #d9d8e7;
}

.hero-score-area {
  margin-top: 14px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.score-ring {
  width: 94px;
  height: 94px;
  padding: 6px;
  border-radius: 50%;
  flex: 0 0 auto;
  box-shadow: 0 12px 24px rgba(109, 93, 246, 0.14);
}

.score-ring-inner {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.96);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}

.score-value {
  font-size: 27px;
  line-height: 1;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: -1px;
}

.score-max {
  margin-top: 4px;
  color: #9a9fb0;
  font-size: 12px;
  font-weight: 600;
}

.score-copy {
  min-width: 0;
}

.score-label {
  display: block;
  margin-bottom: 7px;
  color: #777d90;
  font-size: 12px;
  font-weight: 600;
}

.risk-tag {
  font-weight: 700;
}

.score-copy p {
  max-width: 380px;
  margin: 6px 0 0;
  color: #62697b;
  font-size: 13px;
  line-height: 1.65;
}

.hero-visual {
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: visible;
  pointer-events: none;
}

.hero-visual img {
  position: absolute;
  z-index: 1;
  top: 50%;
  right: -125px;
  width: 700px;
  max-width: none;
  height: 350px;
  object-fit: contain;
  object-position: center;
  opacity: 0.36;
  filter: saturate(0.68) contrast(0.9);
  mix-blend-mode: multiply;
  transform: translateY(-50%);
  -webkit-mask-image: linear-gradient(to right, transparent 0%, rgba(0, 0, 0, 0.36) 22%, #000 50%, #000 100%);
  mask-image: linear-gradient(to right, transparent 0%, rgba(0, 0, 0, 0.36) 22%, #000 50%, #000 100%);
}

.visual-glow {
  position: absolute;
  width: 220px;
  height: 140px;
  border-radius: 50%;
  background: rgba(109, 93, 246, 0.09);
  filter: blur(34px);
}

.analysis-card {
  padding: 28px 30px 30px;
}

.section-heading {
  margin-bottom: 24px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.section-heading h2 {
  margin: 4px 0 0;
  color: #29263d;
  font-size: 21px;
  line-height: 1.3;
  font-weight: 750;
}

.section-heading-outside {
  margin: 0 2px 15px;
}

.section-note {
  color: #8a90a1;
  font-size: 12px;
}

.analysis-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(360px, 0.95fr);
  gap: 28px;
}

.radar-panel,
.dimension-overview {
  min-width: 0;
  border-radius: 14px;
  background: #fafaff;
}

.radar-panel {
  padding: 18px 18px 8px;
  border: 1px solid #f0eff8;
}

.dimension-overview {
  padding: 18px 20px;
  background: linear-gradient(180deg, #fbfaff 0%, #f7f8fc 100%);
}

.panel-title {
  color: #555d70;
  font-size: 13px;
  font-weight: 700;
}

.radar-chart {
  width: 100%;
  height: 330px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.radar-svg {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.radar-grid-polygon {
  fill: rgba(109, 93, 246, 0.025);
  stroke: rgba(109, 93, 246, 0.2);
  stroke-width: 1;
}

.radar-grid-polygon:nth-child(even) {
  fill: rgba(109, 93, 246, 0.055);
}

.radar-axis-line {
  stroke: rgba(109, 93, 246, 0.2);
  stroke-width: 1;
}

.radar-scale-label {
  fill: #a1a5b2;
  font-size: 9px;
  font-weight: 600;
  dominant-baseline: middle;
}

.radar-data-polygon {
  fill-opacity: 0.22;
  stroke-width: 2.5;
  stroke-linejoin: round;
  animation: radar-grow 0.75s ease both;
  transform-box: fill-box;
  transform-origin: center;
}

.radar-value-marker {
  filter: drop-shadow(0 2px 4px rgba(42, 35, 92, 0.16));
}

.radar-value-bg {
  fill: rgba(255, 255, 255, 0.94);
  stroke-width: 1.5;
}

.radar-value-text {
  fill: #3e4050;
  font-size: 10px;
  font-weight: 800;
  dominant-baseline: middle;
}

.radar-label {
  fill: #535b6e;
  font-size: 12px;
  font-weight: 700;
  dominant-baseline: middle;
}

.dimension-row {
  padding: 13px 0;
  border-bottom: 1px solid #ebeaf3;
}

.dimension-row:last-child {
  padding-bottom: 2px;
  border-bottom: 0;
}

.dimension-topline {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.dimension-name {
  color: #3d4152;
  font-size: 14px;
  font-weight: 650;
}

.dimension-result {
  display: flex;
  align-items: center;
  gap: 9px;
}

.dimension-result strong {
  min-width: 26px;
  text-align: right;
  color: #282b3a;
  font-size: 15px;
  font-variant-numeric: tabular-nums;
}

.progress-track {
  width: 100%;
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: #e9eaf1;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  transform-origin: left center;
  animation: progress-grow 0.9s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.dimension-detail-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.dimension-analysis-card {
  position: relative;
  padding: 20px 22px;
  overflow: hidden;
  border-left: 4px solid var(--dimension-color);
}

.dimension-analysis-card::after {
  content: '';
  position: absolute;
  top: -44px;
  right: -44px;
  width: 130px;
  height: 130px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--dimension-color) 8%, transparent);
}

.dimension-analysis-summary {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
}

.dimension-index {
  color: color-mix(in srgb, var(--dimension-color) 76%, #fff);
  font-size: 22px;
  line-height: 1;
  font-weight: 800;
  letter-spacing: -1px;
}

.dimension-analysis-summary h3 {
  margin: 0 0 4px;
  color: #2e3040;
  font-size: 17px;
}

.dimension-analysis-summary p {
  margin: 0;
  color: #858a99;
  font-size: 12px;
  line-height: 1.55;
}

.dimension-score-badge {
  min-width: 108px;
  display: grid;
  grid-template-columns: auto auto;
  align-items: baseline;
  justify-content: end;
  column-gap: 3px;
  text-align: right;
}

.dimension-score-badge strong {
  font-size: 28px;
  line-height: 1;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.dimension-score-badge > span {
  color: #9a9eab;
  font-size: 11px;
}

.dimension-score-badge :deep(.n-tag) {
  grid-column: 1 / -1;
  justify-self: end;
  margin-top: 6px;
}

.dimension-analysis-body {
  margin: 16px 0 0 56px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.analysis-block {
  min-height: 76px;
  padding: 12px 14px;
  border-radius: 11px;
  background: #f8f8fc;
  border: 1px solid #eeeeF5;
}

.analysis-block.training-block {
  background: color-mix(in srgb, var(--dimension-color) 5%, #fff);
  border-color: color-mix(in srgb, var(--dimension-color) 14%, #fff);
}

.analysis-block-label {
  display: block;
  margin-bottom: 5px;
  color: #646a7b;
  font-size: 11px;
  font-weight: 750;
}

.analysis-block p {
  margin: 0;
  color: #686f80;
  font-size: 12px;
  line-height: 1.65;
}

.recommended-actions {
  margin: 12px 0 0 56px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
}

.recommended-actions > span {
  margin-right: 2px;
  color: #777d8d;
  font-size: 11px;
  font-weight: 700;
}

.insight-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.insight-card {
  min-height: 206px;
  padding: 22px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.insight-warning {
  background: linear-gradient(145deg, #fff 0%, #fff8ec 100%);
  border-color: #fde8c5;
}

.insight-purple {
  background: linear-gradient(145deg, #fff 0%, #f6f2ff 100%);
  border-color: #e7defd;
}

.insight-success {
  background: linear-gradient(145deg, #fff 0%, #effcf6 100%);
  border-color: #d9f3e7;
}

.insight-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}

.insight-warning .insight-icon { color: #d97706; background: #ffedce; }
.insight-purple .insight-icon { color: #6D5DF6; background: #eae4ff; }
.insight-success .insight-icon { color: #059669; background: #dff8eb; }

.insight-content {
  min-width: 0;
  flex: 1;
}

.insight-content h3 {
  margin: 1px 0 4px;
  color: #2f3140;
  font-size: 16px;
}

.insight-intro,
.empty-copy,
.analysis-copy {
  margin: 0;
  color: #7b8191;
  font-size: 12px;
  line-height: 1.65;
}

.problem-tags {
  margin-top: 15px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.focus-dimension {
  margin: 14px 0 9px;
  padding: 11px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-radius: 10px;
  background: rgba(109, 93, 246, 0.08);
}

.focus-dimension span {
  color: #7c748f;
  font-size: 11px;
}

.focus-dimension strong {
  color: #5848cf;
  font-size: 14px;
}

.recommendation-list {
  margin: 12px 0 0;
  padding-left: 18px;
  color: #596173;
  font-size: 12px;
  line-height: 1.65;
}

.recommendation-list li + li {
  margin-top: 6px;
}

.empty-copy {
  margin-top: 14px;
  padding: 10px 12px;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.64);
}

.back-button:hover {
  transform: translateY(-2px);
}

.action-footer {
  display: flex;
  justify-content: center;
  padding: 2px 0 8px;
}

.back-button {
  min-width: 112px;
  border-radius: 10px;
  transition: transform 0.2s ease;
}

.fade-in {
  animation: report-enter 0.55s ease both;
}

.fade-in-delay-1 { animation-delay: 0.08s; }
.fade-in-delay-2 { animation-delay: 0.15s; }
.fade-in-delay-3 { animation-delay: 0.22s; }

@keyframes report-enter {
  from { opacity: 0; translate: 0 12px; }
  to { opacity: 1; translate: 0 0; }
}

@keyframes progress-grow {
  from { transform: scaleX(0); }
  to { transform: scaleX(1); }
}

@keyframes radar-grow {
  from { opacity: 0; transform: scale(0.35); }
  to { opacity: 1; transform: scale(1); }
}

@media (max-width: 1050px) {
  .hero-banner {
    grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
    padding: 19px 26px;
  }

  .hero-visual img {
    right: -155px;
    width: 650px;
    height: 325px;
  }

  .analysis-grid {
    grid-template-columns: minmax(0, 1fr) minmax(330px, 0.9fr);
  }

}

@media (max-width: 820px) {
  .hero-banner,
  .analysis-grid,
  .insight-grid {
    grid-template-columns: 1fr;
  }

  .hero-visual {
    display: none;
  }

  .dimension-analysis-body {
    grid-template-columns: 1fr;
  }

}

@media (max-width: 560px) {
  .hero-banner,
  .analysis-card {
    padding: 22px 18px;
  }

  .hero-score-area {
    align-items: flex-start;
  }

  .score-ring {
    width: 96px;
    height: 96px;
  }

  .score-value {
    font-size: 26px;
  }

  .dimension-analysis-summary {
    grid-template-columns: 34px minmax(0, 1fr);
  }

  .dimension-score-badge {
    grid-column: 2;
    justify-content: start;
    justify-self: start;
    text-align: left;
  }

  .dimension-score-badge :deep(.n-tag) {
    justify-self: start;
  }

  .dimension-analysis-body,
  .recommended-actions {
    margin-left: 0;
  }

  .section-note {
    display: none;
  }

}
</style>
