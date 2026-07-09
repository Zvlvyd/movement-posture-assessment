<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { prescriptionV2Api, planEditApi } from '../services/api'
import type { PlanV2, PlanItemV2 } from '../types'
import {
  NCard, NButton, NSpace, NTag, NIcon,
  NEmpty, NSpin, NDescriptions, NDescriptionsItem,
  NPopconfirm, NDivider, NModal, NInput, NSelect, NInputNumber
} from 'naive-ui'
import { useMessage } from 'naive-ui'
import {
  ArrowBackOutline, PlayCircleOutline, BarbellOutline,
  FitnessOutline, TimeOutline, RepeatOutline, TrashOutline,
  CheckmarkCircleOutline, FlameOutline
} from '@vicons/ionicons5'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const plan = ref<PlanV2 | null>(null)
const loading = ref(true)
const activating = ref(false)
const deleting = ref(false)
const showEdit = ref(false)
const editing = ref(false)
const editName = ref('')
const editNotes = ref('')
const editItems = ref<any[]>([])
const actions = ref<any[]>([])
const addActionId = ref<string | null>(null)

async function openEdit() {
  if (!plan.value) return
  editName.value = plan.value.plan_name
  editNotes.value = ''
  editItems.value = plan.value.items.map(item => ({
    ...item,
    duration_seconds: (item as any).duration_seconds ?? item.duration ?? 0
  }))
  showEdit.value = true
  if (!actions.value.length) {
    try { actions.value = (await prescriptionV2Api.getActions()).actions || [] } catch { /* adding is optional */ }
  }
}

function addAction() {
  const action = actions.value.find(item => String(item.id ?? item.action_id) === String(addActionId.value))
  if (!action || editItems.value.some(item => String(item.action_id) === String(action.id ?? action.action_id))) return
  editItems.value.push({
    action_id: action.id ?? action.action_id,
    action_name: action.name,
    phase: action.phases?.[0] || 'main',
    sets: 3, reps: 10, duration_seconds: 0,
    difficulty: action.difficulty || 1,
    intensity: action.intensity || 'MEDIUM'
  })
  addActionId.value = null
}

async function saveEdit() {
  if (!plan.value || !editName.value.trim() || !editItems.value.length) return message.warning('计划名称和动作不能为空')
  editing.value = true
  try {
    const data = await planEditApi.edit(plan.value.id, {
      plan_name: editName.value.trim(),
      items: editItems.value,
      student_notes: editNotes.value || undefined
    })
    message.success(data.message || (data.status === 'pending' ? '已提交教练审批' : '计划已更新'))
    showEdit.value = false
    loadPlan()
  } catch (error: any) { message.error(error?.response?.data?.detail || '保存失败') }
  finally { editing.value = false }
}

function loadPlan() {
  const id = Number(route.params.id)
  if (!id) { loading.value = false; return }
  loading.value = true
  prescriptionV2Api.get(id)
    .then(p => { plan.value = p })
    .catch(() => { plan.value = null })
    .finally(() => { loading.value = false })
}

function activate() {
  if (!plan.value) return
  activating.value = true
  prescriptionV2Api.activate(plan.value.id)
    .then(() => { router.push('/prescription-training') })
    .catch(() => {
      const firstAction = plan.value?.items?.[0]?.action_name
      if (firstAction) router.push('/training')
    })
    .finally(() => { activating.value = false })
}

function deletePlan() {
  if (!plan.value) return
  deleting.value = true
  prescriptionV2Api.delete(plan.value.id)
    .then(() => { router.push('/prescription-training') })
    .catch(() => {})
    .finally(() => { deleting.value = false })
}

const trainingConfig = computed(() => {
  return plan.value?.plan_meta?.training_config || null
})

const phases = computed(() => {
  if (!plan.value?.items) return []
  const order = ['warmup', 'activation', 'main', 'cooldown']
  const groups: { phase: string; items: PlanItemV2[] }[] = []
  const seen = new Set<string>()
  for (const item of plan.value.items) {
    const p = item.phase || 'main'
    if (!seen.has(p)) {
      seen.add(p)
      groups.push({ phase: p, items: [] })
    }
    groups.find(g => g.phase === p)?.items.push(item)
  }
  groups.sort((a, b) => order.indexOf(a.phase) - order.indexOf(b.phase))
  return groups
})

function getPhaseColor(phase: string) {
  const map: Record<string, string> = {
    warmup: '#f59e0b', activation: '#3b82f6', main: '#8b5cf6', cooldown: '#10b981'
  }
  return map[phase] || '#64748b'
}

function getPhaseLabel(phase: string) {
  const map: Record<string, string> = {
    warmup: '热身', activation: '激活', main: '主训', cooldown: '放松'
  }
  return map[phase] || phase
}

function getStatusLabel(status: string) {
  const map: Record<string, string> = { active: '进行中', completed: '已完成', draft: '草稿' }
  return map[status] || status
}

function getStatusType(status: string) {
  const map: Record<string, any> = { active: 'success', completed: 'info', draft: 'default' }
  return map[status] || 'default'
}

onMounted(() => { loadPlan() })
</script>

<script lang="ts">
export default { name: 'PrescriptionPlanDetailView' }
</script>

<template>
  <div class="plan-detail-page">
    <n-spin v-if="loading" style="display: flex; justify-content: center; padding: 60px;" />

    <template v-else-if="plan">
      <div class="back-row">
        <n-button text @click="router.push('/prescription-training')">
          <template #icon><n-icon :component="ArrowBackOutline" /></template>
          返回训练方案列表
        </n-button>
      </div>

      <n-card :bordered="false" class="header-card" size="large">
        <div class="plan-header">
          <div class="plan-info">
            <h2 class="plan-name">{{ plan.plan_name }}</h2>
            <div class="plan-tags">
              <n-tag :type="getStatusType(plan.status)" round size="small">
                {{ getStatusLabel(plan.status) }}
              </n-tag>
              <n-tag size="small" round>
                {{ plan.generation_method === 'deepseek' ? 'AI 生成' : '本地规则' }}
              </n-tag>
              <n-tag size="small" round>
                {{ plan.items?.length || 0 }} 个动作
              </n-tag>
              <n-tag v-if="trainingConfig?.user_level_label" size="small" round type="warning">
                {{ trainingConfig.user_level_label }}
              </n-tag>
            </div>
            <div v-if="trainingConfig" class="plan-training-config">
              <n-icon size="14" :component="RepeatOutline" />
              <span>建议每周 {{ trainingConfig.training_frequency }} 次 · 每次约 {{ trainingConfig.training_duration }} 分钟 · {{ trainingConfig.training_goal }}</span>
            </div>
          </div>
          <n-space>
            <n-button style="background: #fff; color: #333; border: 1px solid #d9d9d9" @click="openEdit">编辑计划</n-button>
            <n-popconfirm @positive-click="deletePlan">
              <template #trigger>
                <n-button style="background: #fff; color: #e74c3c; border: 1px solid #d9d9d9" :loading="deleting">
                  <template #icon><n-icon :component="TrashOutline" /></template>
                </n-button>
              </template>
              确定要删除这个训练计划吗？
            </n-popconfirm>
          </n-space>
        </div>

        <n-descriptions :column="2" size="small" bordered style="margin-top: 16px;">
          <n-descriptions-item label="训练水平">
            {{ trainingConfig?.user_level_label || '-' }}
          </n-descriptions-item>
          <n-descriptions-item label="创建时间">
            {{ plan.created_at ? new Date(plan.created_at).toLocaleDateString() : '-' }}
          </n-descriptions-item>
        </n-descriptions>
      </n-card>

      <n-card :bordered="false" class="section-card" size="large">
        <template #header>
          <span class="section-title">训练流程</span>
        </template>

        <div v-for="group in phases" :key="group.phase" class="phase-block">
          <div class="phase-header" :style="{ background: getPhaseColor(group.phase) + '12' }">
            <div class="phase-dot" :style="{ background: getPhaseColor(group.phase) }"></div>
            <span class="phase-label" :style="{ color: getPhaseColor(group.phase) }">
              {{ getPhaseLabel(group.phase) }}
            </span>
            <span class="phase-count">{{ group.items.length }} 个动作</span>
          </div>

          <div class="action-list">
            <div v-for="(item, idx) in group.items" :key="item.id" class="action-row">
              <div class="action-order">{{ idx + 1 }}</div>
              <div class="action-body">
                <div class="action-name">
                  {{ item.action_name }}
                  <n-tag v-if="item.alternative" size="tiny" round type="warning">替代</n-tag>
                </div>
                <div class="action-detail">
                  <span><n-icon size="14" :component="RepeatOutline" /> {{ item.sets }}组 × {{ item.reps }}次</span>
                  <span v-if="item.duration_seconds"><n-icon size="14" :component="TimeOutline" /> {{ item.duration_seconds }}s</span>
                </div>
                <div v-if="item.notes" class="action-notes">{{ item.notes }}</div>
              </div>
            </div>
          </div>
        </div>
      </n-card>

      <div class="action-footer">
        <n-button
          type="primary"
          size="large"
          :loading="activating"
          @click="activate"
          block
        >
          <template #icon><n-icon size="20" :component="PlayCircleOutline" /></template>
          开始训练
        </n-button>
      </div>

      <n-modal v-model:show="showEdit" preset="card" title="编辑训练计划" style="width:min(860px,94vw)">
        <n-space vertical size="large">
          <div><strong>计划名称</strong><n-input v-model:value="editName" placeholder="计划名称" style="margin-top:6px" /></div>
          <div><strong>修改原因（加入班级后将提交教练审批）</strong><n-input v-model:value="editNotes" type="textarea" :rows="2" placeholder="说明为什么要修改计划" style="margin-top:6px" /></div>
          <div class="edit-head"><strong>计划动作</strong><n-select v-model:value="addActionId" filterable placeholder="添加动作" :options="actions.filter(a => !editItems.some(i => String(i.action_id) === String(a.id ?? a.action_id))).map(a => ({ label: a.name, value: String(a.id ?? a.action_id) }))" style="width:220px" @update:value="addAction" /></div>
          <div class="edit-table">
            <div v-for="(item,index) in editItems" :key="`${item.action_name}-${index}`" class="edit-row">
              <strong>{{ item.action_name }}</strong>
              <n-select v-model:value="item.phase" :options="['warmup','activation','main','cooldown'].map(v => ({label:getPhaseLabel(v),value:v}))" size="small" />
              <label>组<n-input-number v-model:value="item.sets" :min="1" :max="10" size="small" /></label>
              <label>次<n-input-number v-model:value="item.reps" :min="1" :max="50" size="small" /></label>
              <label>秒<n-input-number v-model:value="item.duration_seconds" :min="0" :max="600" size="small" /></label>
              <n-button text type="error" @click="editItems.splice(index,1)">移除</n-button>
            </div>
          </div>
        </n-space>
        <template #footer><n-space justify="end"><n-button @click="showEdit=false">取消</n-button><n-button type="primary" :loading="editing" @click="saveEdit">保存修改</n-button></n-space></template>
      </n-modal>
    </template>

    <n-empty v-else description="训练计划未找到">
      <template #extra>
        <n-button type="primary" @click="router.push('/prescription-training')">返回训练方案列表</n-button>
      </template>
    </n-empty>
  </div>
</template>

<style scoped>
.plan-detail-page {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.back-row {
  margin-bottom: -8px;
}

.header-card {
  border-radius: 16px !important;
  background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%) !important;
  color: white;
}

.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.plan-name {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 10px 0;
  color: white;
}

.plan-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.plan-training-config {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
}

.header-card :deep(.n-descriptions) {
  background: transparent;
}

.section-card {
  border-radius: 12px !important;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
}

.phase-block {
  margin-bottom: 20px;
}

.phase-block:last-child {
  margin-bottom: 0;
}

.phase-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  margin-bottom: 8px;
}

.phase-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.phase-label {
  font-size: 15px;
  font-weight: 600;
}

.phase-count {
  font-size: 12px;
  color: #94a3b8;
  margin-left: auto;
}

.action-row {
  display: flex;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid #f1f5f9;
}

.action-row:last-child {
  border-bottom: none;
}

.action-order {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  flex-shrink: 0;
}

.action-body {
  flex: 1;
  min-width: 0;
}

.action-name {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.action-detail {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #64748b;
}

.action-notes {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
  font-style: italic;
}

.action-footer {
  padding: 8px 0 16px;
}
.edit-head{display:flex;align-items:center;justify-content:space-between;gap:12px}.edit-table{max-height:420px;overflow:auto}.edit-row{display:grid;grid-template-columns:minmax(110px,1fr) 100px 115px 115px 120px 42px;gap:8px;align-items:center;padding:9px 0;border-bottom:1px solid #eef2f7}.edit-row label{display:flex;align-items:center;gap:4px;color:#64748b;white-space:nowrap}.edit-row :deep(.n-input-number){width:88px}

@media (max-width: 640px) {
  .plan-header {
    flex-direction: column;
    gap: 12px;
  }
  .edit-row{grid-template-columns:1fr 100px}.edit-row label{grid-column:auto}
}
</style>
