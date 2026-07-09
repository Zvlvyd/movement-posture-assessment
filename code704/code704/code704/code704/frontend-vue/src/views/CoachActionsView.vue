<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { coachApi } from '../services/api'
import { useMessage } from 'naive-ui'
import {
  NButton, NCard, NCheckbox, NDescriptions, NDescriptionsItem, NDynamicTags,
  NEmpty, NForm, NFormItem, NGrid, NGridItem, NIcon, NImage, NInput,
  NInputNumber, NModal, NPagination, NSelect, NSpace, NSpin, NTag
} from 'naive-ui'
import {
  AddOutline, CloudUploadOutline, CreateOutline, EyeOffOutline, EyeOutline,
  FitnessOutline, RefreshOutline, SearchOutline, TrashOutline
} from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const actions = ref<any[]>([])
const categories = ref<string[]>([])
const families = ref<string[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)
const search = ref('')
const category = ref<string | null>(null)
const family = ref<string | null>(null)
const difficulty = ref<number | null>(null)
const bodyPart = ref('')
const includeHidden = ref(false)

const detailVisible = ref(false)
const createVisible = ref(false)
const editMode = ref(false)
const selectedAction = ref<any>(null)
const saving = ref(false)
const uploadProgress = ref<Record<string, number>>({})

const emptyForm = () => ({
  name: '', category: '', family: '', family_name: '', difficulty: 2,
  description: '', steps: [] as string[], cues: [] as string[], target_body_parts: [] as string[]
})
const form = reactive(emptyForm())
const difficultyLabels = ['极简', '简单', '中等', '困难', '极难']

const categoryOptions = computed(() => categories.value.map(value => ({ label: value, value })))
const familyOptions = computed(() => families.value.map(value => ({ label: value, value })))
const difficultyOptions = difficultyLabels.map((label, index) => ({ label: `${index + 1} - ${label}`, value: index + 1 }))

function normalizeList(data: any) {
  actions.value = data?.items || data?.actions || (Array.isArray(data) ? data : [])
  total.value = data?.total ?? actions.value.length
  categories.value = data?.categories || []
  families.value = data?.families || []
}

async function loadActions() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (search.value.trim()) params.search = search.value.trim()
    if (category.value) params.category = category.value
    if (family.value) params.family = family.value
    if (difficulty.value) params.difficulty = difficulty.value
    if (bodyPart.value.trim()) params.body_part = bodyPart.value.trim()
    if (includeHidden.value) params.include_hidden = true
    normalizeList(await coachApi.listActions(params))
  } catch (err: any) {
    message.error(err?.response?.data?.detail || '获取动作库失败')
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  search.value = ''
  category.value = null
  family.value = null
  difficulty.value = null
  bodyPart.value = ''
  includeHidden.value = false
  page.value = 1
  loadActions()
}

function thumbnail(action: any) {
  return action.thumbnail_url || action.media?.find((item: any) => item.media_type === 'thumbnail')?.url
}

function fillForm(action?: any) {
  Object.assign(form, emptyForm(), action ? {
    name: action.name || '', category: action.category || '', family: action.family || '',
    family_name: action.family_name || '', difficulty: action.difficulty || 2,
    description: action.description || '', steps: [...(action.steps || [])],
    cues: [...(action.cues || [])], target_body_parts: [...(action.target_body_parts || [])]
  } : {})
}

async function openDetail(action: any, editing = false) {
  try {
    const lookup = action.id ?? action.json_id ?? action.name
    selectedAction.value = await coachApi.getAction(lookup)
    fillForm(selectedAction.value)
    editMode.value = editing
    detailVisible.value = true
  } catch (err: any) {
    message.error(err?.response?.data?.detail || '获取动作详情失败')
  }
}

function openCreate() {
  fillForm()
  createVisible.value = true
}

async function createAction() {
  if (!form.name.trim()) return message.warning('请输入动作名称')
  saving.value = true
  try {
    await coachApi.createAction({ ...form })
    message.success('动作创建成功')
    createVisible.value = false
    await loadActions()
  } catch (err: any) {
    message.error(err?.response?.data?.detail || '创建失败')
  } finally { saving.value = false }
}

async function saveAction() {
  if (!selectedAction.value?.id) return message.warning('系统内置动作不支持直接编辑')
  saving.value = true
  try {
    await coachApi.updateAction(selectedAction.value.id, { ...form })
    message.success('保存成功')
    detailVisible.value = false
    await loadActions()
  } catch (err: any) {
    message.error(err?.response?.data?.detail || '保存失败')
  } finally { saving.value = false }
}

async function toggleVisibility(action: any) {
  try {
    await coachApi.setActionVisibility(String(action.id ?? action.name), action.is_visible === false)
    message.success(action.is_visible === false ? '已取消隐藏' : '已隐藏')
    await loadActions()
  } catch (err: any) { message.error(err?.response?.data?.detail || '操作失败') }
}

async function deleteAction(action: any) {
  if (!action.id || !window.confirm(`确定删除动作“${action.name}”吗？`)) return
  try {
    await coachApi.deleteAction(action.id)
    message.success('动作已删除')
    if (selectedAction.value?.id === action.id) detailVisible.value = false
    await loadActions()
  } catch (err: any) { message.error(err?.response?.data?.detail || '删除失败') }
}

async function uploadMedia(event: Event, mediaType: string) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !selectedAction.value?.id) return
  uploadProgress.value[mediaType] = 1
  try {
    await coachApi.uploadActionMedia(selectedAction.value.id, file, mediaType, pct => { uploadProgress.value[mediaType] = pct })
    selectedAction.value = await coachApi.getAction(selectedAction.value.id)
    message.success('媒体上传成功')
    await loadActions()
  } catch (err: any) { message.error(err?.response?.data?.detail || '上传失败') }
  finally { uploadProgress.value[mediaType] = 0 }
}

async function deleteMedia(media: any) {
  if (!window.confirm('确定删除这个媒体文件吗？')) return
  try {
    await coachApi.deleteActionMedia(media.id)
    selectedAction.value = await coachApi.getAction(selectedAction.value.id)
    message.success('媒体已删除')
  } catch (err: any) { message.error(err?.response?.data?.detail || '删除失败') }
}

onMounted(loadActions)
</script>

<template>
  <div class="actions-page">
    <n-card :bordered="false" class="header-card">
      <div class="page-header">
        <div><h2><n-icon :component="FitnessOutline" /> 动作库管理</h2><p>维护学员学习和训练计划使用的标准动作</p></div>
        <n-space><n-button @click="loadActions"><template #icon><n-icon :component="RefreshOutline" /></template>刷新</n-button><n-button type="primary" @click="openCreate"><template #icon><n-icon :component="AddOutline" /></template>创建动作</n-button></n-space>
      </div>
    </n-card>

    <n-card :bordered="false" class="filter-card">
      <div class="filters">
        <n-input v-model:value="search" clearable placeholder="搜索动作名称" @keyup.enter="page = 1; loadActions()"><template #prefix><n-icon :component="SearchOutline" /></template></n-input>
        <n-select v-model:value="category" clearable :options="categoryOptions" placeholder="分类" />
        <n-select v-model:value="family" clearable :options="familyOptions" placeholder="动作家族" />
        <n-select v-model:value="difficulty" clearable :options="difficultyOptions" placeholder="难度" />
        <n-input v-model:value="bodyPart" clearable placeholder="目标部位" @keyup.enter="page = 1; loadActions()" />
        <n-checkbox v-model:checked="includeHidden">显示隐藏动作</n-checkbox>
        <n-button type="primary" @click="page = 1; loadActions()">筛选</n-button>
        <n-button @click="resetFilters">重置</n-button>
      </div>
    </n-card>

    <n-spin :show="loading">
      <n-grid v-if="actions.length" cols="1 s:2 m:3 l:4" responsive="screen" :x-gap="14" :y-gap="14">
        <n-grid-item v-for="action in actions" :key="action.id || action.json_id || action.name">
          <n-card hoverable class="action-card" :class="{ hidden: action.is_visible === false }">
            <div class="thumb" @click="openDetail(action)">
              <n-image v-if="thumbnail(action)" :src="thumbnail(action)" object-fit="cover" preview-disabled />
              <n-icon v-else size="48" :component="FitnessOutline" />
            </div>
            <h3 @click="openDetail(action)">{{ action.name }}</h3>
            <n-space wrap size="small">
              <n-tag v-if="action.family_name" type="info">{{ action.family_name }}</n-tag>
              <n-tag type="warning">{{ difficultyLabels[(action.difficulty || 1) - 1] }}</n-tag>
              <n-tag v-if="action.category">{{ action.category }}</n-tag>
            </n-space>
            <p>{{ action.description || '暂无描述' }}</p>
            <n-space justify="space-between">
              <n-button size="small" @click="openDetail(action)"><template #icon><n-icon :component="EyeOutline" /></template>详情</n-button>
              <n-button size="small" @click="openDetail(action, true)"><template #icon><n-icon :component="CreateOutline" /></template>编辑</n-button>
              <n-button size="small" @click="toggleVisibility(action)"><template #icon><n-icon :component="action.is_visible === false ? EyeOutline : EyeOffOutline" /></template>{{ action.is_visible === false ? '显示' : '隐藏' }}</n-button>
              <n-button v-if="action.id" size="small" type="error" @click="deleteAction(action)"><template #icon><n-icon :component="TrashOutline" /></template></n-button>
            </n-space>
          </n-card>
        </n-grid-item>
      </n-grid>
      <n-empty v-else-if="!loading" description="没有符合条件的动作" />
    </n-spin>
    <n-pagination v-if="total > pageSize" v-model:page="page" v-model:page-size="pageSize" :item-count="total" show-size-picker :page-sizes="[12, 24, 48]" @update:page="loadActions" @update:page-size="page = 1; loadActions()" />

    <n-modal v-model:show="detailVisible" preset="card" :title="selectedAction?.name || '动作详情'" class="action-modal">
      <n-form v-if="editMode" label-placement="top">
        <n-grid cols="2" :x-gap="12"><n-grid-item><n-form-item label="动作名称"><n-input v-model:value="form.name" /></n-form-item></n-grid-item><n-grid-item><n-form-item label="分类"><n-input v-model:value="form.category" /></n-form-item></n-grid-item><n-grid-item><n-form-item label="家族标识"><n-input v-model:value="form.family" /></n-form-item></n-grid-item><n-grid-item><n-form-item label="家族名称"><n-input v-model:value="form.family_name" /></n-form-item></n-grid-item></n-grid>
        <n-form-item label="难度"><n-input-number v-model:value="form.difficulty" :min="1" :max="5" /></n-form-item>
        <n-form-item label="描述"><n-input v-model:value="form.description" type="textarea" /></n-form-item>
        <n-form-item label="步骤"><n-dynamic-tags v-model:value="form.steps" /></n-form-item>
        <n-form-item label="动作要点"><n-dynamic-tags v-model:value="form.cues" /></n-form-item>
        <n-form-item label="目标部位"><n-dynamic-tags v-model:value="form.target_body_parts" /></n-form-item>
        <n-space justify="end"><n-button @click="editMode = false">取消编辑</n-button><n-button type="primary" :loading="saving" @click="saveAction">保存</n-button></n-space>
      </n-form>
      <template v-else-if="selectedAction">
        <n-descriptions bordered :column="2"><n-descriptions-item label="名称">{{ selectedAction.name }}</n-descriptions-item><n-descriptions-item label="来源">{{ selectedAction.source || '-' }}</n-descriptions-item><n-descriptions-item label="分类">{{ selectedAction.category || '-' }}</n-descriptions-item><n-descriptions-item label="家族">{{ selectedAction.family_name || selectedAction.family || '-' }}</n-descriptions-item><n-descriptions-item label="难度">{{ difficultyLabels[(selectedAction.difficulty || 1) - 1] }}</n-descriptions-item><n-descriptions-item label="目标部位"><n-tag v-for="part in selectedAction.target_body_parts || []" :key="part">{{ part }}</n-tag></n-descriptions-item></n-descriptions>
        <p class="detail-description">{{ selectedAction.description || '暂无描述' }}</p>
        <ol><li v-for="step in selectedAction.steps || []" :key="step">{{ step }}</li></ol>
        <n-space wrap><n-tag v-for="cue in selectedAction.cues || []" :key="cue" type="info">{{ cue }}</n-tag></n-space>
        <div v-if="selectedAction.id" class="media-section"><h3>媒体管理</h3><div v-for="type in ['thumbnail', 'image', 'video']" :key="type" class="media-row"><strong>{{ type === 'thumbnail' ? '缩略图' : type === 'image' ? '示例图片' : '示例视频' }}</strong><label class="upload-btn"><input type="file" :accept="type === 'video' ? 'video/*' : 'image/*'" @change="uploadMedia($event, type)"><n-icon :component="CloudUploadOutline" />上传 {{ uploadProgress[type] ? uploadProgress[type] + '%' : '' }}</label><div class="media-list"><div v-for="media in (selectedAction.media || []).filter((m: any) => m.media_type === type)" :key="media.id"><video v-if="type === 'video'" :src="media.url" controls /><n-image v-else :src="media.url" width="120" /><n-button size="tiny" type="error" @click="deleteMedia(media)">删除</n-button></div></div></div></div>
        <n-space justify="end"><n-button @click="editMode = true"><template #icon><n-icon :component="CreateOutline" /></template>编辑</n-button></n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="createVisible" preset="card" title="创建动作" class="action-modal">
      <n-form label-placement="top"><n-form-item label="动作名称"><n-input v-model:value="form.name" /></n-form-item><n-grid cols="2" :x-gap="12"><n-grid-item><n-form-item label="分类"><n-input v-model:value="form.category" /></n-form-item></n-grid-item><n-grid-item><n-form-item label="难度"><n-input-number v-model:value="form.difficulty" :min="1" :max="5" /></n-form-item></n-grid-item><n-grid-item><n-form-item label="家族标识"><n-input v-model:value="form.family" /></n-form-item></n-grid-item><n-grid-item><n-form-item label="家族名称"><n-input v-model:value="form.family_name" /></n-form-item></n-grid-item></n-grid><n-form-item label="描述"><n-input v-model:value="form.description" type="textarea" /></n-form-item><n-form-item label="步骤"><n-dynamic-tags v-model:value="form.steps" /></n-form-item><n-form-item label="动作要点"><n-dynamic-tags v-model:value="form.cues" /></n-form-item><n-form-item label="目标部位"><n-dynamic-tags v-model:value="form.target_body_parts" /></n-form-item></n-form>
      <template #footer><n-space justify="end"><n-button @click="createVisible = false">取消</n-button><n-button type="primary" :loading="saving" @click="createAction">创建</n-button></n-space></template>
    </n-modal>
  </div>
</template>

<style scoped>
.actions-page{display:flex;flex-direction:column;gap:16px}.header-card,.filter-card,.action-card{border-radius:14px}.page-header{display:flex;align-items:center;justify-content:space-between;gap:16px}.page-header h2{display:flex;align-items:center;gap:8px;margin:0}.page-header p{margin:5px 0 0;color:#64748b}.filters{display:grid;grid-template-columns:2fr repeat(4,1fr) auto auto auto;gap:10px;align-items:center}.action-card{height:100%}.action-card.hidden{opacity:.55}.thumb{height:150px;margin:-16px -16px 12px;display:flex;align-items:center;justify-content:center;overflow:hidden;color:#94a3b8;background:#f1f5f9;cursor:pointer}.thumb :deep(img){width:100%;height:150px;object-fit:cover}.action-card h3{margin:0 0 9px;cursor:pointer}.action-card p{min-height:42px;color:#64748b}.action-modal{width:min(900px,92vw)}.detail-description{padding:12px;border-radius:8px;background:#f8fafc}.media-section{margin-top:20px}.media-row{padding:12px 0;border-top:1px solid #e5e7eb}.upload-btn{display:inline-flex;align-items:center;gap:6px;margin-left:12px;padding:6px 12px;border:1px solid #d8dee9;border-radius:7px;cursor:pointer}.upload-btn input{display:none}.media-list{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}.media-list>div{display:flex;flex-direction:column;gap:5px}.media-list video{width:240px;max-height:160px}.n-pagination{align-self:flex-end}@media(max-width:1000px){.filters{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:640px){.page-header{align-items:flex-start;flex-direction:column}.filters{grid-template-columns:1fr}.action-modal{width:96vw}}
</style>
