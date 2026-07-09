<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { NButton, NTag, NCard, NEmpty, NDataTable, NSpin, NSpace, NAlert, NInputNumber, NInput, NModal, useDialog, useMessage, type DataTableColumns } from 'naive-ui'
import { coachApi } from '../services/api'
import type { ChangeRequestItem } from '../types'

const message = useMessage()
const dialog = useDialog()
const requests = ref<ChangeRequestItem[]>([])
const loading = ref(true)
const selected = ref<ChangeRequestItem | null>(null)
const detailLoading = ref(false)
const submitting = ref(false)
const adjustItems = ref<any[]>([])
const coachNotes = ref('')
const rejectReason = ref('')
const showReject = ref(false)

const labels: Record<string, [string, 'warning' | 'success' | 'error' | 'info' | 'default']> = {
  pending: ['待审批', 'warning'], approved: ['已通过', 'success'], rejected: ['已拒绝', 'error'], adjusted: ['已调整', 'info']
}
const isPending = computed(() => selected.value?.status === 'pending')
const originalItems = computed(() => parseItems(selected.value?.original_snapshot))

function parseItems(raw?: string) { try { return raw ? JSON.parse(raw) : [] } catch { return [] } }
function statusTag(status: string) { const item = labels[status] || [status, 'default']; return h(NTag, { type: item[1] }, { default: () => item[0] }) }

const columns: DataTableColumns<ChangeRequestItem> = [
  { title: '学员', key: 'student_name', width: 130 },
  { title: '计划', key: 'plan_name', ellipsis: { tooltip: true } },
  { title: '状态', key: 'status', width: 100, render: row => statusTag(row.status) },
  { title: '申请时间', key: 'created_at', width: 150, render: row => row.created_at?.slice(0, 16) },
  { title: '操作', key: 'action', width: 100, render: row => h(NButton, { text: true, type: 'primary', onClick: () => openDetail(row.id) }, { default: () => '查看详情' }) }
]

async function loadRequests() {
  loading.value = true
  try { const data = await coachApi.listChangeRequests(); requests.value = data.requests || [] }
  catch (error: any) { message.error(error?.response?.data?.detail || '审批列表加载失败') }
  finally { loading.value = false }
}

async function openDetail(id: number) {
  detailLoading.value = true
  try {
    const data = await coachApi.getChangeRequest(id)
    selected.value = data
    adjustItems.value = parseItems(data.proposed_items).map((item: any) => ({ ...item }))
    coachNotes.value = ''
  } catch { message.error('详情加载失败') }
  finally { detailLoading.value = false }
}

async function approve() {
  if (!selected.value) return
  submitting.value = true
  try { await coachApi.approveChangeRequest(selected.value.id); message.success('已通过审批'); selected.value = null; await loadRequests() }
  catch (error: any) { message.error(error?.response?.data?.detail || '操作失败') }
  finally { submitting.value = false }
}

async function adjust() {
  if (!selected.value) return
  submitting.value = true
  try { await coachApi.adjustChangeRequest(selected.value.id, adjustItems.value, coachNotes.value); message.success('已调整并通过'); selected.value = null; await loadRequests() }
  catch (error: any) { message.error(error?.response?.data?.detail || '操作失败') }
  finally { submitting.value = false }
}

async function reject() {
  if (!selected.value || !rejectReason.value.trim()) return message.warning('请填写拒绝原因')
  submitting.value = true
  try { await coachApi.rejectChangeRequest(selected.value.id, rejectReason.value.trim()); message.success('已拒绝'); showReject.value = false; selected.value = null; rejectReason.value = ''; await loadRequests() }
  catch (error: any) { message.error(error?.response?.data?.detail || '操作失败') }
  finally { submitting.value = false }
}

function confirmApprove() { dialog.success({ title: '确认通过？', content: '通过后，学员提交的计划修改将生效。', positiveText: '通过', negativeText: '取消', onPositiveClick: approve }) }
onMounted(loadRequests)
</script>

<template>
  <div class="page-shell">
    <template v-if="!selected">
      <div class="page-head"><h2>计划审批</h2><n-button @click="loadRequests">刷新</n-button></div>
      <n-card><n-empty v-if="!loading && !requests.length" description="暂无计划变更请求"/><n-data-table v-else :columns="columns" :data="requests" :loading="loading" :row-key="row => row.id"/></n-card>
    </template>
    <template v-else>
      <n-button text type="primary" class="back" @click="selected = null">← 返回列表</n-button>
      <n-spin :show="detailLoading">
        <n-card>
          <template #header><n-space align="center"><span>{{ selected.student_name }} — {{ selected.plan_name }}</span><n-tag :type="labels[selected.status]?.[1] || 'default'">{{ labels[selected.status]?.[0] || selected.status }}</n-tag></n-space></template>
          <n-alert v-if="selected.student_notes" type="warning" title="学员留言" class="notes">{{ selected.student_notes }}</n-alert>
          <div class="compare">
            <n-card size="small" title="修改前">
              <n-empty v-if="!originalItems.length" description="无原始数据" />
              <div v-for="(item, index) in originalItems" :key="`${item.action_name}-${index}`" class="plan-item">
                <strong>{{ item.action_name }}</strong><n-tag size="small">{{ item.phase }}</n-tag><span>{{ item.sets }}组</span><span>{{ item.reps }}次</span><span>{{ item.duration_seconds || 0 }}秒</span>
              </div>
            </n-card>
            <n-card size="small" :title="isPending ? '修改后（可调整）' : '修改后'">
              <n-empty v-if="!adjustItems.length" description="无计划项数据" />
              <div v-for="(item, index) in adjustItems" :key="`${item.action_name}-${index}`" class="plan-item">
                <strong>{{ item.action_name }}</strong><n-tag size="small">{{ item.phase }}</n-tag>
                <label>组 <n-input-number v-model:value="item.sets" :min="1" :max="10" size="small" :disabled="!isPending" /></label>
                <label>次 <n-input-number v-model:value="item.reps" :min="1" :max="50" size="small" :disabled="!isPending" /></label>
                <label>秒 <n-input-number v-model:value="item.duration_seconds" :min="0" :max="600" size="small" :disabled="!isPending" /></label>
              </div>
            </n-card>
          </div>
          <n-input v-if="isPending" v-model:value="coachNotes" type="textarea" placeholder="给学员的反馈（可选）" class="notes" />
          <n-alert v-if="!isPending && selected.coach_notes" :type="selected.status === 'rejected' ? 'error' : 'info'" title="教练留言" class="notes">{{ selected.coach_notes }}</n-alert>
          <n-space v-if="isPending" justify="end" class="actions"><n-button type="primary" :loading="submitting" @click="confirmApprove">通过</n-button><n-button :loading="submitting" @click="adjust">调整后通过</n-button><n-button type="error" :loading="submitting" @click="showReject = true">拒绝</n-button></n-space>
        </n-card>
      </n-spin>
    </template>
    <n-modal v-model:show="showReject" preset="card" title="拒绝修改请求" style="width:min(480px,92vw)"><n-input v-model:value="rejectReason" type="textarea" :rows="3" placeholder="填写拒绝原因，学员将收到通知"/><template #footer><n-space justify="end"><n-button @click="showReject=false">取消</n-button><n-button type="error" :loading="submitting" @click="reject">确认拒绝</n-button></n-space></template></n-modal>
  </div>
</template>

<style scoped>
.page-shell{max-width:1100px;margin:auto}.page-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}.page-head h2{margin:0}.back{margin-bottom:12px}.notes{margin:14px 0}.compare{display:grid;grid-template-columns:1fr 1fr;gap:16px}.plan-item{display:grid;grid-template-columns:minmax(100px,1fr) auto 82px 82px 82px;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid #eef2f7}.plan-item label{display:flex;align-items:center;gap:4px;color:#64748b}.plan-item :deep(.n-input-number){width:58px}.actions{margin-top:16px}@media(max-width:800px){.compare{grid-template-columns:1fr}.plan-item{grid-template-columns:1fr auto}.plan-item label{grid-column:auto}}
</style>
