<script setup lang="ts">
import { h, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { coachApi } from '../services/api'
import {
  NCard, NButton, NTag, NIcon, NSpace, NDescriptions, NDescriptionsItem,
  NList, NListItem, NEmpty, NSpin, NGrid, NGridItem, NDataTable, NProgress,
  NTabs, NTabPane, NPopconfirm, useMessage, type DataTableColumns
} from 'naive-ui'
import {
  ArrowBackOutline, PersonOutline, CallOutline, CalendarOutline,
  FitnessOutline, TrophyOutline, CheckmarkCircleOutline, FlameOutline,
  BarbellOutline, AnalyticsOutline, TrashOutline, ExperimentOutline,
  HistoryOutlined, ClockCircleOutline, ThunderboltOutline, BarChartOutline
} from '@vicons/ionicons5'
import ScoreBar from '../components/ScoreBar.vue'
import MiniRadar from '../components/MiniRadar.vue'
import { getRiskColor, getRiskLabel } from '../utils/riskColor'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const profile = ref<any>(null)
const loading = ref(true)
const plans = ref<any[]>([])
const trainingRecords = ref<any[]>([])
const trainingStats = ref<any>(null)
const activeTab = ref('body')

function scoreColor(s: number): string {
  if (s >= 85) return '#10b981'
  if (s >= 60) return '#f59e0b'
  return '#ef4444'
}

async function loadProfile() {
  const id = Number(route.params.id)
  if (!id) { loading.value = false; return }
  const [p, ps, records, stats] = await Promise.allSettled([
    coachApi.studentProfile(id), coachApi.studentPlans(id),
    coachApi.trainingRecords(id, 90), coachApi.trainingStats(id)
  ])
  profile.value = p.status === 'fulfilled' ? p.value : null
  if (ps.status === 'fulfilled') plans.value = Array.isArray(ps.value) ? ps.value : (ps.value?.plans || [])
  if (records.status === 'fulfilled') trainingRecords.value = Array.isArray(records.value) ? records.value : (records.value?.records || [])
  if (stats.status === 'fulfilled') trainingStats.value = stats.value
  loading.value = false
}

async function deletePlan(plan: any) {
  const studentId = Number(route.params.id)
  if (!window.confirm(`确定删除训练计划"${plan.plan_name || plan.name || plan.id}"吗？`)) return
  try {
    await coachApi.deleteStudentPlan(studentId, plan.id || plan.plan_id)
    plans.value = plans.value.filter(p => (p.id || p.plan_id) !== (plan.id || plan.plan_id))
    message.success('训练计划已删除')
  } catch (err: any) { message.error(err?.response?.data?.detail || '删除失败') }
}

const recordColumns: DataTableColumns = [
  { title: '时间', key: 'created_at', width: 140, render: (r: any) => new Date(r.created_at || r.start_time).toLocaleString('zh-CN').slice(0, 16) },
  { title: '所属计划', key: 'plan_name', width: 120, ellipsis: { tooltip: true }, render: (r: any) => r.plan_name || '-' },
  { title: '训练动作', key: 'action_name', width: 130 },
  { title: '得分', key: 'best_score', width: 70, align: 'center',
    render: (r: any) => {
      const v = Math.round(r.best_score || r.total_score || 0)
      return v ? h('span', { style: { fontWeight: 700, color: scoreColor(v), fontSize: '14px' } }, String(v)) : '-'
    }
  },
  { title: '次数/时长', key: 'count', width: 120,
    render: (r: any) => {
      const parts: string[] = []
      if (r.rep_count) parts.push(`${r.rep_count} 次`)
      if (r.hold_time_seconds) parts.push(`${Number(r.hold_time_seconds).toFixed(0)}s`)
      return parts.join(' · ') || '-'
    }
  },
]

// FMS history columns
const fmsHistoryColumns: DataTableColumns = [
  { title: '日期', key: 'test_date', width: 100, render: (r: any) => r.test_date?.slice(0, 10) },
  { title: '平衡', key: 'balance_score', width: 55, align: 'center', render: (r: any) => Math.round(r.balance_score || 0) },
  { title: '灵活', key: 'flexibility_score', width: 55, align: 'center', render: (r: any) => Math.round(r.flexibility_score || 0) },
  { title: '上肢', key: 'upper_limb_score', width: 55, align: 'center', render: (r: any) => Math.round(r.upper_limb_score || 0) },
  { title: '核心', key: 'core_score', width: 55, align: 'center', render: (r: any) => Math.round(r.core_score || 0) },
  { title: '对称', key: 'symmetry_score', width: 55, align: 'center', render: (r: any) => Math.round(r.symmetry_score || 0) },
  { title: '综合', key: 'overall_score', width: 60, align: 'center', render: (r: any) => Math.round(r.overall_score || 0) },
  { title: '风险', key: 'risk_level', width: 75, render: (r: any) => {
    const color = getRiskColor(r.risk_level)
    return h('span', { style: { color, fontWeight: 600 } }, getRiskLabel(r.risk_level))
  }},
]

const asmtHistoryColumns: DataTableColumns = [
  { title: '日期', key: 'test_date', width: 100, render: (r: any) => r.test_date?.slice(0, 10) },
  { title: '类型', key: 'assessment_type', width: 70 },
  { title: '综合', key: 'overall_score', width: 60, align: 'center', render: (r: any) => Math.round(r.overall_score || 0) },
  { title: '风险', key: 'risk_level', width: 75, render: (r: any) => {
    const color = getRiskColor(r.risk_level)
    return h('span', { style: { color, fontWeight: 600 } }, getRiskLabel(r.risk_level))
  }},
]

// Plan items columns
const planItemColumns: DataTableColumns = [
  { title: '#', key: 'order_index', width: 40, render: (r: any) => r.order_index ?? '-' },
  { title: '动作', key: 'action_name', ellipsis: { tooltip: true }, width: 130 },
  { title: '阶段', key: 'phase', width: 65, render: (r: any) => {
    const m: Record<string, string> = { warmup: '热身', activation: '激活', main: '主体', cooldown: '冷身' }
    return m[r.phase] || r.phase || '-'
  }},
  { title: '组数', key: 'sets', width: 50, align: 'center' },
  { title: '次数', key: 'reps', width: 50, align: 'center' },
  { title: '时长(s)', key: 'duration_seconds', width: 70, align: 'center', render: (r: any) => r.duration_seconds || r.duration || '-' },
  { title: '难度', key: 'difficulty', width: 50, align: 'center' },
  { title: '强度', key: 'intensity', width: 60, render: (r: any) => {
    const colors: Record<string, string> = { LOW: 'success', MEDIUM: 'warning', HIGH: 'error' }
    return r.intensity || '-'
  }},
  { title: '完成', key: 'completions', width: 70, align: 'center',
    render: (r: any) => `${r.completions || 0}/${r.sets || 0}`
  },
  { title: '最新得分', key: 'latest_score', width: 80, align: 'center',
    render: (r: any) => {
      const v = r.latest_score
      if (v == null) return '-'
      return h('span', { style: { fontWeight: 700, color: scoreColor(v) } }, String(Math.round(v)))
    }
  },
]

onMounted(() => { loadProfile() })
</script>

<script lang="ts">
export default { name: 'CoachStudentDetailView' }
</script>

<template>
  <div class="student-detail-page">
    <n-spin v-if="loading" style="display: flex; justify-content: center; padding: 60px;" />

    <template v-else-if="profile">
      <div class="back-row">
        <n-button text @click="router.push('/coach')">
          <template #icon><n-icon :component="ArrowBackOutline" /></template>
          返回教练工作台
        </n-button>
      </div>

      <!-- Header card -->
      <n-card :bordered="false" class="header-card" size="large">
        <div class="student-header">
          <div>
            <h2 class="student-name">{{ profile.username }}</h2>
            <div class="student-meta">
              <span><n-icon size="14" :component="PersonOutline" /> {{ profile.gender === 'female' ? '女' : profile.gender === 'male' ? '男' : (profile.gender || '-') }}</span>
              <span><n-icon size="14" :component="CallOutline" /> {{ profile.phone || '-' }}</span>
              <span><n-icon size="14" :component="CalendarOutline" /> {{ profile.created_at ? new Date(profile.created_at).toLocaleDateString() : '-' }}</span>
            </div>
          </div>
          <div class="streak-badge" v-if="profile.checkin?.streak_days">
            <n-icon size="20" :component="FlameOutline" />
            <span class="streak-num">{{ profile.checkin.streak_days }}</span>
            <span class="streak-label">连续打卡</span>
          </div>
        </div>
      </n-card>

      <!-- Score cards -->
      <n-grid :cols="2" :x-gap="12" :y-gap="12">
        <n-grid-item>
          <n-card :bordered="false" class="score-card" size="medium">
            <div class="score-header">
              <n-icon size="20" :component="AnalyticsOutline" style="color: #3b82f6;" />
              <span class="score-title">FMS 评分</span>
            </div>
            <template v-if="profile.fms">
              <div class="score-value-big">{{ profile.fms.overall_score }}</div>
              <n-tag :color="getRiskColor(profile.fms.risk_level)" round size="small">
                {{ getRiskLabel(profile.fms.risk_level) }}
              </n-tag>
            </template>
            <n-empty v-else description="暂无数据" size="small" />
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card :bordered="false" class="score-card" size="medium">
            <div class="score-header">
              <n-icon size="20" :component="FitnessOutline" style="color: #10b981;" />
              <span class="score-title">体态评估</span>
            </div>
            <template v-if="profile.assessment">
              <div class="score-value-big">{{ profile.assessment.overall_score }}</div>
              <n-tag :color="getRiskColor(profile.assessment.risk_level)" round size="small">
                {{ getRiskLabel(profile.assessment.risk_level) }}
              </n-tag>
            </template>
            <n-empty v-else description="暂无数据" size="small" />
          </n-card>
        </n-grid-item>
      </n-grid>

      <!-- Training stats -->
      <n-grid v-if="trainingStats" :cols="4" :x-gap="12">
        <n-grid-item>
          <n-card :bordered="false" class="stat-mini-card" size="small">
            <div class="stat-mini-value" style="color: #3b82f6;">{{ trainingStats.week?.total || 0 }}</div>
            <div class="stat-mini-label">本周训练</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card :bordered="false" class="stat-mini-card" size="small">
            <div class="stat-mini-value" :style="{ color: scoreColor(trainingStats.week?.avg_score || 0) }">{{ Number(trainingStats.week?.avg_score || 0).toFixed(1) }}</div>
            <div class="stat-mini-label">本周均分</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card :bordered="false" class="stat-mini-card" size="small">
            <div class="stat-mini-value">{{ trainingStats.week?.total_duration_minutes || 0 }}</div>
            <div class="stat-mini-label">本周时长(分)</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card :bordered="false" class="stat-mini-card" size="small">
            <div class="stat-mini-value">{{ trainingStats.all_time?.total || 0 }}</div>
            <div class="stat-mini-label">累计训练</div>
          </n-card>
        </n-grid-item>
      </n-grid>

      <!-- Badges -->
      <n-card v-if="profile.badges?.length" :bordered="false" class="section-card" size="large">
        <template #header><span class="section-title"><n-icon :component="TrophyOutline" /> 徽章成就</span></template>
        <n-space>
          <n-tag v-for="badge in profile.badges" :key="badge.id" type="warning" round size="large">
            🏅 {{ badge.name }}
          </n-tag>
        </n-space>
      </n-card>

      <!-- Tabs -->
      <n-card :bordered="false" class="section-card" size="large">
        <n-tabs v-model:value="activeTab" type="line">
          <!-- 身体状况 -->
          <n-tab-pane name="body" tab="身体状况">
            <n-grid :cols="2" :x-gap="16">
              <!-- FMS -->
              <n-grid-item>
                <n-card size="small" title="FMS 功能性运动筛查" :bordered="false" class="inner-card">
                  <template #header-extra>
                    <n-tag v-if="profile.fms?.risk_level" :color="getRiskColor(profile.fms?.risk_level)" round size="small">
                      {{ getRiskLabel(profile.fms?.risk_level) }}
                    </n-tag>
                  </template>
                  <template v-if="profile.fms">
                    <ScoreBar label="平衡" :value="profile.fms.balance_score" />
                    <ScoreBar label="灵活" :value="profile.fms.flexibility_score" />
                    <ScoreBar label="上肢" :value="profile.fms.upper_limb_score" />
                    <ScoreBar label="核心" :value="profile.fms.core_score" />
                    <ScoreBar label="对称" :value="profile.fms.symmetry_score" />
                    <MiniRadar
                      :scores="{
                        balance_score: profile.fms.balance_score,
                        flexibility_score: profile.fms.flexibility_score,
                        upper_limb_score: profile.fms.upper_limb_score,
                        core_score: profile.fms.core_score,
                        symmetry_score: profile.fms.symmetry_score,
                      }"
                      :size="200"
                    />
                  </template>
                  <n-empty v-else description="暂无 FMS 数据" size="small" />
                </n-card>
              </n-grid-item>

              <!-- Assessment -->
              <n-grid-item>
                <n-card size="small" title="体态评估" :bordered="false" class="inner-card">
                  <template #header-extra>
                    <n-tag v-if="profile.assessment?.risk_level" :color="getRiskColor(profile.assessment?.risk_level)" round size="small">
                      {{ getRiskLabel(profile.assessment?.risk_level) }}
                    </n-tag>
                  </template>
                  <template v-if="profile.assessment">
                    <ScoreBar label="平衡" :value="profile.assessment.balance_score" />
                    <ScoreBar label="灵活" :value="profile.assessment.flexibility_score" />
                    <ScoreBar label="上肢" :value="profile.assessment.upper_limb_score" />
                    <ScoreBar label="核心" :value="profile.assessment.core_score" />
                    <ScoreBar label="对称" :value="profile.assessment.symmetry_score" />
                    <n-descriptions bordered size="small" :column="1" class="detail-desc">
                      <n-descriptions-item label="综合评分">{{ profile.assessment.overall_score }}</n-descriptions-item>
                      <n-descriptions-item label="评估类型">{{ profile.assessment.assessment_type || '-' }}</n-descriptions-item>
                      <n-descriptions-item label="评估日期">{{ profile.assessment.test_date?.slice(0, 10) || '-' }}</n-descriptions-item>
                    </n-descriptions>
                  </template>
                  <n-empty v-else description="暂无体态评估数据" size="small" />
                </n-card>
              </n-grid-item>
            </n-grid>

            <!-- FMS history -->
            <n-card v-if="profile.fms_history?.length > 1" size="small" title="FMS 历史记录" :bordered="false" class="inner-card" style="margin-top: 16px;">
              <n-data-table :columns="fmsHistoryColumns" :data="profile.fms_history" :row-key="(r: any) => r.id" size="small" :pagination="false" />
            </n-card>

            <!-- Assessment history -->
            <n-card v-if="profile.assessment_history?.length > 1" size="small" title="体态评估历史记录" :bordered="false" class="inner-card" style="margin-top: 16px;">
              <n-data-table :columns="asmtHistoryColumns" :data="profile.assessment_history" :row-key="(r: any) => r.id" size="small" :pagination="false" />
            </n-card>
          </n-tab-pane>

          <!-- 训练计划 -->
          <n-tab-pane name="plans" :tab="`训练计划 (${plans.length})`">
            <template v-if="plans.length">
              <n-card v-for="plan in plans" :key="plan.id || plan.plan_id" size="small" :bordered="false" class="plan-card">
                <template #header>
                  <n-space align="center">
                    <strong>{{ plan.plan_name }}</strong>
                    <n-tag :type="plan.status === 'active' ? 'info' : plan.status === 'completed' ? 'success' : 'default'" round size="small">
                      {{ plan.status === 'active' ? '进行中' : plan.status === 'completed' ? '已完成' : '草稿' }}
                    </n-tag>
                    <n-tag :type="plan.generation_method === 'deepseek' ? 'warning' : 'info'" round size="small">
                      {{ plan.generation_method === 'deepseek' ? 'AI生成' : '本地引擎' }}
                    </n-tag>
                    <n-tag v-if="plan.item_count" round size="small">{{ plan.item_count }} 个动作</n-tag>
                  </n-space>
                </template>
                <template #header-extra>
                  <n-space align="center">
                    <span style="font-size:12px;color:#94a3b8">{{ plan.created_at?.slice(0, 10) }}</span>
                    <n-popconfirm @positive-click="deletePlan(plan)">
                      <template #trigger>
                        <n-button text type="error" size="small">
                          <template #icon><n-icon :component="TrashOutline" /></template>
                          删除
                        </n-button>
                      </template>
                      确认删除此训练计划？
                    </n-popconfirm>
                  </n-space>
                </template>
                <!-- Overall progress -->
                <div v-if="plan.items?.length" style="margin-bottom: 12px;">
                  <n-progress
                    type="line"
                    :percentage="Math.round((plan.items.reduce((s: number, i: any) => s + (i.completions || 0), 0) / Math.max(1, plan.items.reduce((s: number, i: any) => s + (i.sets || 0), 0))) * 100)"
                    :indicator-placement="'inside'"
                    processing
                  />
                </div>
                <p v-if="plan.overall_strategy" style="color:#64748b;font-size:13px;margin-bottom:12px;">{{ plan.overall_strategy }}</p>
                <n-data-table
                  :columns="planItemColumns"
                  :data="plan.items || []"
                  :row-key="(r: any) => r.id"
                  size="small"
                  :pagination="false"
                />
              </n-card>
            </template>
            <n-empty v-else description="暂无训练计划" size="small" style="padding: 40px 0;" />
          </n-tab-pane>

          <!-- 训练记录 -->
          <n-tab-pane name="training" :tab="`训练记录 (${trainingRecords.length})`">
            <!-- Active plan progress -->
            <n-grid v-if="trainingStats?.active_plans?.length" :cols="2" :x-gap="12" style="margin-bottom: 16px;">
              <n-grid-item v-for="ap in trainingStats.active_plans" :key="ap.plan_id">
                <n-card size="small" :bordered="false" class="inner-card">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                      <strong>{{ ap.plan_name }}</strong>
                      <p style="font-size:12px;color:#94a3b8;margin:2px 0 0;">已完成 {{ ap.completed_sessions }} 组训练</p>
                      <n-tag v-if="ap.latest_score != null" :color="scoreColor(ap.latest_score)" round size="small">
                        最近得分 {{ ap.latest_score }}
                      </n-tag>
                    </div>
                    <n-progress type="circle" :percentage="ap.total_items ? Math.round(ap.completed_sessions / Math.max(ap.total_items, 1) * 100) : 0" :width="60">
                      {{ ap.completed_sessions }}
                    </n-progress>
                  </div>
                </n-card>
              </n-grid-item>
            </n-grid>

            <n-data-table
              v-if="trainingRecords.length"
              :columns="recordColumns"
              :data="trainingRecords"
              :row-key="(r: any) => r.id"
              :pagination="{ pageSize: 15, showSizePicker: true, pageSizes: [10, 15, 30] }"
              size="small"
            />
            <n-empty v-else description="暂无训练记录" size="small" style="padding: 40px 0;" />
          </n-tab-pane>
        </n-tabs>
      </n-card>
    </template>

    <n-empty v-else description="学员未找到" style="padding: 60px 0;" />
  </div>
</template>

<style scoped>
.student-detail-page {
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 24px;
}

.back-row { margin-bottom: -8px; }

.header-card {
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%) !important;
  color: white;
  border-radius: 16px !important;
}

.student-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.student-name { font-size: 22px; font-weight: 700; margin: 0 0 8px 0; color: white; }

.student-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  flex-wrap: wrap;
}

.student-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.streak-badge {
  text-align: center;
  color: white;
  background: rgba(255, 255, 255, 0.15);
  padding: 12px 16px;
  border-radius: 12px;
}

.streak-num { display: block; font-size: 24px; font-weight: 700; }
.streak-label { font-size: 11px; opacity: 0.85; }

.score-card {
  border-radius: 12px !important;
  text-align: center;
}

.score-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-bottom: 8px;
}

.score-title { font-size: 14px; font-weight: 600; }

.score-value-big { font-size: 32px; font-weight: 700; }

.stat-mini-card {
  border-radius: 12px !important;
  text-align: center;
}

.stat-mini-value { font-size: 22px; font-weight: 700; }
.stat-mini-label { font-size: 12px; color: #64748b; margin-top: 2px; }

.section-card { border-radius: 12px !important; }
.section-title { font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 6px; }

.inner-card {
  border-radius: 10px !important;
  background: #fafbfc;
}

.detail-desc {
  margin-top: 12px;
}

.muscle-box {
  margin-top: 12px;
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
}

.muscle-text {
  margin: 6px 0 0;
  font-size: 13px;
  color: #475569;
  white-space: pre-wrap;
}

.muscle-group {
  margin-top: 10px;
}

.muscle-label {
  font-size: 12px;
  color: #64748b;
  display: block;
  margin-bottom: 6px;
}

.muscle-raw {
  margin: 8px 0 0;
  font-size: 11px;
  max-height: 160px;
  overflow: auto;
  white-space: pre-wrap;
  color: #475569;
}

.plan-card {
  border-radius: 10px !important;
  margin-bottom: 12px;
}

.rx-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

@media (max-width: 768px) {
  .student-header { flex-direction: column; gap: 12px; }
  .student-meta { flex-direction: column; gap: 6px; }
}
</style>
