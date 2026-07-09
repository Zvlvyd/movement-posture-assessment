<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { coachApi } from '../services/api'
import {
  NCard, NButton, NTag, NIcon, NSpace, NDescriptions, NDescriptionsItem,
  NList, NListItem, NEmpty, NSpin, NGrid, NGridItem, NProgress,
  NModal, NForm, NFormItem, NInput, NPopconfirm, useMessage
} from 'naive-ui'
import {
  ArrowBackOutline, PersonOutline, FitnessOutline,
  BarChartOutline, AnalyticsOutline, PersonRemoveOutline,
  TrophyOutline, CopyOutline, RefreshOutline, CreateOutline, TrashOutline,
  SchoolOutline
} from '@vicons/ionicons5'
import ScoreBar from '../components/ScoreBar.vue'
import { getRiskColor, getRiskLabel } from '../utils/riskColor'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const classData = ref<any>(null)
const trend = ref<any>(null)
const loading = ref(true)
const showEditModal = ref(false)
const editingClassName = ref('')
const editingClassDesc = ref('')

function loadData() {
  const id = Number(route.params.id)
  if (!id) { loading.value = false; return }
  loading.value = true
  Promise.all([
    coachApi.classStats(id).catch(() => null),
    coachApi.classTrend(id, 14).catch(() => null)
  ]).then(([stats, t]) => {
    classData.value = stats
    trend.value = t
  }).finally(() => { loading.value = false })
}

function getRiskColorFn(level: string) {
  const c = getRiskColor(level)
  if (c === '#10b981') return 'success'
  if (c === '#f59e0b') return 'warning'
  if (c === '#ef4444' || c === '#dc2626') return 'error'
  return 'default'
}

async function removeStudent(student: any) {
  const classId = Number(route.params.id)
  try {
    await coachApi.removeStudent(classId, student.id)
    classData.value.students = (classData.value.students || []).filter((s: any) => s.id !== student.id)
    classData.value.student_count = Math.max(0, (classData.value.student_count || 1) - 1)
    message.success('学员已移出班级')
  } catch (err: any) { message.error(err?.response?.data?.detail || '移除失败') }
}

async function copyInviteCode(code: string) {
  try {
    await navigator.clipboard.writeText(code)
    message.success(`邀请码 ${code} 已复制`)
  } catch { message.error('复制失败') }
}

async function regenerateCode() {
  const classId = Number(route.params.id)
  try {
    const res = await coachApi.regenerateCode(classId)
    classData.value.invite_code = res.invite_code
    message.success(`邀请码已更新为 ${res.invite_code}`)
  } catch (err: any) { message.error(err?.response?.data?.detail || '刷新邀请码失败') }
}

function openEditModal() {
  editingClassName.value = classData.value?.class_name || ''
  editingClassDesc.value = classData.value?.description || ''
  showEditModal.value = true
}

async function saveClass() {
  const id = Number(route.params.id)
  if (!editingClassName.value.trim() || !id) return
  try {
    await coachApi.updateClass(id, { name: editingClassName.value, description: editingClassDesc.value })
    showEditModal.value = false
    message.success('班级已更新')
    // Refresh data
    classData.value.class_name = editingClassName.value
    classData.value.description = editingClassDesc.value
    loadData()
  } catch (err: any) { message.error(err?.response?.data?.detail || '更新失败') }
}

async function deleteThisClass() {
  const id = Number(route.params.id)
  try {
    await coachApi.deleteClass(id)
    message.success('班级已删除')
    router.push('/coach')
  } catch (err: any) { message.error(err?.response?.data?.detail || '删除失败') }
}

const trendItems = () => Array.isArray(trend.value) ? trend.value : (trend.value?.items || trend.value?.trend || [])

const maxTrendScore = computed(() => {
  const items = trendItems()
  return Math.max(...items.map((d: any) => d.avg_score || d.score || 0), 1)
})
const maxTrendCount = computed(() => {
  const items = trendItems()
  return Math.max(...items.map((d: any) => d.sessions ?? d.count ?? 0), 1)
})

// Find current class from coachApi for invite code
const classInfo = ref<any>(null)
async function loadClassInfo() {
  try {
    const classes = await coachApi.classes()
    const id = Number(route.params.id)
    classInfo.value = (classes || []).find((c: any) => c.id === id)
  } catch { /* ignore */ }
}

onMounted(() => { loadData(); loadClassInfo() })
</script>

<script lang="ts">
export default { name: 'CoachClassDetailView' }
</script>

<template>
  <div class="class-detail-page">
    <n-spin v-if="loading" style="display: flex; justify-content: center; padding: 60px;" />

    <template v-else-if="classData">
      <div class="back-row">
        <n-space align="center" justify="space-between">
          <n-button text @click="router.push('/coach')">
            <template #icon><n-icon :component="ArrowBackOutline" /></template>
            返回教练工作台
          </n-button>
          <n-space>
            <n-button size="small" @click="openEditModal">
              <template #icon><n-icon :component="CreateOutline" /></template>
              编辑班级
            </n-button>
            <n-popconfirm @positive-click="deleteThisClass">
              <template #trigger>
                <n-button size="small" type="error">
                  <template #icon><n-icon :component="TrashOutline" /></template>
                  删除班级
                </n-button>
              </template>
              确认删除此班级？班级中如有学员需先移除
            </n-popconfirm>
          </n-space>
        </n-space>
      </div>

      <n-card :bordered="false" class="header-card" size="large">
        <div class="class-header">
          <div>
            <h2 class="class-name">{{ classData.class_name }}</h2>
            <p class="class-subtitle">{{ classData.student_count }} 名学员</p>
          </div>
        </div>
      </n-card>

      <!-- Invite Code Banner -->
      <n-card v-if="classInfo?.invite_code" size="small" class="invite-banner">
        <div class="invite-banner-row">
          <n-space align="center">
            <span class="invite-label-text">班级邀请码</span>
            <n-tag type="info" size="large" class="invite-code-tag" @click="copyInviteCode(classInfo.invite_code)">
              {{ classInfo.invite_code }}
            </n-tag>
            <n-button size="small" text @click="copyInviteCode(classInfo.invite_code)" title="复制">
              <template #icon><n-icon :component="CopyOutline" /></template>
            </n-button>
            <n-popconfirm @positive-click="regenerateCode">
              <template #trigger>
                <n-button size="small" text title="刷新邀请码">
                  <template #icon><n-icon :component="RefreshOutline" /></template>
                </n-button>
              </template>
              确认刷新邀请码？旧邀请码将失效
            </n-popconfirm>
          </n-space>
          <span style="font-size:12px;color:#94a3b8;">将邀请码分享给学员即可加入班级</span>
        </div>
      </n-card>

      <!-- Stats -->
      <n-grid :cols="4" :x-gap="12" :y-gap="12">
        <n-grid-item>
          <n-card :bordered="false" class="stat-card" size="medium">
            <div class="stat-icon-wrapper" style="background:#3b82f615;color:#3b82f6;">
              <n-icon size="20" :component="SchoolOutline" />
            </div>
            <div class="stat-value">{{ classData.class_name }}</div>
            <div class="stat-label">班级</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card :bordered="false" class="stat-card" size="medium">
            <div class="stat-icon-wrapper" style="background:#10b98115;color:#10b981;">
              <n-icon size="20" :component="PersonOutline" />
            </div>
            <div class="stat-value">{{ classData.student_count }}</div>
            <div class="stat-label">学员数</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card :bordered="false" class="stat-card" size="medium">
            <div class="stat-icon-wrapper" style="background:#f59e0b15;color:#f59e0b;">
              <n-icon size="20" :component="TrophyOutline" />
            </div>
            <div class="stat-value">{{ classData.summary?.avg_overall_score || '-' }}</div>
            <div class="stat-label">平均综合分</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card :bordered="false" class="stat-card" size="medium">
            <div class="stat-icon-wrapper" style="background:#8b5cf615;color:#8b5cf6;">
              <n-icon size="20" :component="BarChartOutline" />
            </div>
            <div class="stat-value">{{ classData.summary?.active_7d_rate ?? '-' }}{{ classData.summary?.active_7d_rate != null ? '%' : '' }}</div>
            <div class="stat-label">7日活跃率</div>
          </n-card>
        </n-grid-item>
      </n-grid>

      <!-- Weekly overview -->
      <n-grid :cols="2" :x-gap="12" :y-gap="12">
        <n-grid-item>
          <n-card :bordered="false" class="section-card" size="medium">
            <template #header><span class="section-title">近 14 天训练趋势</span></template>
            <div v-if="trendItems().length" class="mini-trend-chart">
              <div class="trend-bars">
                <div
                  v-for="(item, index) in trendItems()"
                  :key="item.date || index"
                  class="trend-bar-col"
                  :style="{ width: Math.max(4, Math.min(12, 700 / trendItems().length)) + 'px' }"
                >
                  <div
                    class="trend-bar-score"
                    :title="`${item.date} 分数:${item.avg_score || item.score || 0}`"
                    :style="{
                      height: `${((item.avg_score || item.score || 0) / maxTrendScore) * 55}px`,
                      background: (item.avg_score || item.score || 0) >= 60 ? '#52c41a' : '#faad14',
                    }"
                  />
                  <div
                    class="trend-bar-count"
                    :title="`${item.date} 次数:${item.sessions ?? item.count ?? 0}`"
                    :style="{
                      height: `${((item.sessions ?? item.count ?? 0) / maxTrendCount) * 40}px`,
                    }"
                  />
                </div>
              </div>
              <div class="trend-legend">
                <span class="legend-dot" style="background:#52c41a;" /> 平均分
                <span class="legend-dot" style="background:#1890ff;opacity:0.6;" /> 训练次数
              </div>
            </div>
            <n-empty v-else description="暂无趋势数据" size="small" />
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card :bordered="false" class="section-card" size="medium">
            <template #header><span class="section-title">本周概况</span></template>
            <n-descriptions v-if="classData.summary" bordered size="small" :column="2">
              <n-descriptions-item label="7日总训练">{{ classData.summary.total_sessions_7d }} 次</n-descriptions-item>
              <n-descriptions-item label="30日总训练">{{ classData.summary.total_sessions_30d }} 次</n-descriptions-item>
              <n-descriptions-item label="人均周训练">{{ classData.summary.sessions_per_student_7d }} 次</n-descriptions-item>
              <n-descriptions-item label="本周训练学员">{{ classData.summary.active_7d_count }}/{{ classData.student_count }} 人</n-descriptions-item>
              <n-descriptions-item label="平均综合分">{{ classData.summary.avg_overall_score }}</n-descriptions-item>
              <n-descriptions-item label="完成率">{{ classData.summary.active_7d_rate }}%</n-descriptions-item>
            </n-descriptions>
            <n-empty v-else description="暂无数据" size="small" />
          </n-card>
        </n-grid-item>
      </n-grid>

      <!-- Student list -->
      <n-card :bordered="false" class="section-card" size="large">
        <template #header><span class="section-title">班级学员 ({{ classData.students?.length || 0 }})</span></template>
        <n-list v-if="classData.students?.length">
          <n-list-item v-for="student in classData.students" :key="student.id">
            <div class="student-row">
              <div class="student-left">
                <div class="student-info" @click="router.push(`/coach/student/${student.id}`)" style="cursor:pointer;">
                  <span class="student-name">{{ student.username }}</span>
                  <span class="student-meta">
                    {{ student.sessions_7d || 0 }}次训练 · 连续{{ student.streak_days || 0 }}天
                  </span>
                </div>
              </div>
              <!-- FMS Scores -->
              <div class="student-scores" v-if="student.fms_scores">
                <n-space size="small" wrap>
                  <ScoreBar label="平衡" :value="student.fms_scores.balance || 0" />
                  <ScoreBar label="灵活" :value="student.fms_scores.flexibility || 0" />
                  <ScoreBar label="上肢" :value="student.fms_scores.upper_limb || 0" />
                  <ScoreBar label="核心" :value="student.fms_scores.core || 0" />
                  <ScoreBar label="对称" :value="student.fms_scores.symmetry || 0" />
                </n-space>
              </div>
              <div class="student-scores" v-else-if="!student.fms_scores">
                <n-tag type="default" round size="small">未筛查</n-tag>
              </div>
              <n-space align="center">
                <n-tag v-if="student.risk_level" :type="getRiskColorFn(student.risk_level)" round size="small">
                  {{ getRiskLabel(student.risk_level) }}
                </n-tag>
                <n-tag :type="(student.sessions_7d || 0) >= 3 ? 'success' : (student.sessions_7d || 0) >= 1 ? 'info' : 'default'" round size="small">
                  {{ student.sessions_7d || 0 }}次
                </n-tag>
                <span v-if="student.streak_days > 0" style="font-size:12px;">🔥 {{ student.streak_days }}天</span>
                <n-popconfirm @positive-click="removeStudent(student)">
                  <template #trigger>
                    <n-button text type="error" size="small">
                      <template #icon><n-icon :component="PersonRemoveOutline" /></template>
                    </n-button>
                  </template>
                  确认将"{{ student.username }}"移出班级？
                </n-popconfirm>
              </n-space>
            </div>
          </n-list-item>
        </n-list>
        <n-empty v-else description="暂无学员" size="small" style="padding: 30px 0;" />
      </n-card>
    </template>

    <n-empty v-else description="班级未找到" style="padding: 60px 0;" />

    <!-- Edit class modal -->
    <n-modal v-model:show="showEditModal" preset="card" title="编辑班级" style="width: 440px;">
      <n-form label-placement="top">
        <n-form-item label="班级名称">
          <n-input v-model:value="editingClassName" placeholder="请输入班级名称" />
        </n-form-item>
        <n-form-item label="班级描述">
          <n-input v-model:value="editingClassDesc" placeholder="请输入班级描述（选填）" type="textarea" :rows="3" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showEditModal = false">取消</n-button>
          <n-button type="primary" @click="saveClass">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.class-detail-page {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 24px;
}

.back-row { margin-bottom: -8px; }

.header-card {
  background: linear-gradient(135deg, #5E74F8, #7B6CFF, #9A68D8) !important;
  color: white;
  border-radius: 16px !important;
}

.class-name { font-size: 22px; font-weight: 700; margin: 0 0 4px 0; color: white; }
.class-subtitle { font-size: 13px; margin: 0; color: rgba(255, 255, 255, 0.85); }

.invite-banner {
  border-radius: 12px !important;
  background: #f0f5ff !important;
}

.invite-banner-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.invite-label-text {
  font-weight: 600;
  font-size: 14px;
  color: #334155;
}

.invite-code-tag {
  font-family: monospace;
  font-size: 16px;
  letter-spacing: 3px;
  cursor: pointer;
}

.stat-card {
  border-radius: 12px !important;
  text-align: center;
}

.stat-icon-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 6px;
}

.stat-value { font-size: 20px; font-weight: 700; }
.stat-label { font-size: 12px; color: #64748b; margin-top: 2px; }

.section-card { border-radius: 12px !important; }
.section-title { font-size: 16px; font-weight: 600; }

.mini-trend-chart {
  padding: 8px 0;
}
.trend-bars {
  display: flex;
  align-items: flex-end;
  gap: 1px;
  height: 110px;
}
.trend-bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 4px;
}
.trend-bar-score {
  width: 100%;
  border-radius: 2px 2px 0 0;
  min-height: 2px;
}
.trend-bar-count {
  width: 100%;
  background: #1890ff;
  opacity: 0.6;
  border-radius: 0 0 2px 2px;
  min-height: 2px;
}
.trend-legend {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  margin-top: 8px;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
  margin-right: 2px;
}

.student-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: 12px;
  flex-wrap: wrap;
}

.student-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.student-name { font-size: 14px; font-weight: 600; display: block; }
.student-meta { font-size: 11px; color: #64748b; display: block; }

.student-scores {
  flex: 1;
  min-width: 200px;
}

@media (max-width: 768px) {
  .student-row { flex-direction: column; align-items: flex-start; }
  .invite-banner-row { flex-direction: column; align-items: flex-start; }
}
</style>
