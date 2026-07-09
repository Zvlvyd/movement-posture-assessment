<script setup lang="ts">
import { h, ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { coachApi } from '../services/api'
import {
  NCard, NButton, NTabs, NTabPane, NTag, NIcon,
  NList, NListItem, NAvatar, NSpace, NInput,
  NGrid, NGridItem, NEmpty, NSpin, NModal, NForm, NFormItem, NSelect,
  NDataTable, NPopconfirm, useMessage, type DataTableColumns
} from 'naive-ui'
import {
  PeopleOutline, SearchOutline, ChevronForwardOutline,
  PersonAddOutline, BarChartOutline, FitnessOutline,
  AddOutline, SchoolOutline, CreateOutline, TrashOutline,
  CopyOutline, RefreshOutline, IdcardOutline, EyeOutline
} from '@vicons/ionicons5'
import ScoreBar from '../components/ScoreBar.vue'
import { getRiskColor, getRiskLabel } from '../utils/riskColor'

const router = useRouter()
const message = useMessage()

const activeTab = ref('trainees')
const searchQuery = ref('')
const loading = ref(true)
const showCreateClassModal = ref(false)
const newClassName = ref('')
const newClassDesc = ref('')
const showAddStudentModal = ref(false)
const traineeKeyword = ref('')
const availableTrainees = ref<any[]>([])
const selectedTraineeId = ref<number | null>(null)
const selectedClassIdForAdd = ref<number | null>(null)
const showEditClassModal = ref(false)
const editingClass = ref<any>(null)

const summary = ref({ total_students: 0, class_count: 0, sessions_7d: 0, sessions_30d: 0 })
const students = ref<Array<{ id: number; username: string; phone?: string; class?: string; class_id?: number }>>([])
const classes = ref<Array<{ id: number; name: string; description?: string; student_count: number; created_at: string; invite_code?: string }>>([])

function loadData() {
  loading.value = true
  Promise.all([
    coachApi.summary().catch(() => ({ total_students: 0, class_count: 0, sessions_7d: 0, sessions_30d: 0 })),
    coachApi.students().catch(() => []),
    coachApi.classes().catch(() => [])
  ]).then(([s, st, cl]) => {
    summary.value = s
    students.value = st
    classes.value = cl
  }).finally(() => { loading.value = false })
}

const filteredStudents = computed(() => {
  if (!searchQuery.value) return students.value
  const q = searchQuery.value.toLowerCase()
  return students.value.filter(s => s.username.toLowerCase().includes(q) || (s.phone && s.phone.includes(q)))
})

function goToStudent(studentId: number) {
  router.push(`/coach/student/${studentId}`)
}

function goToClassDetail(classId: number) {
  router.push(`/coach/class/${classId}`)
}

async function createClass() {
  if (!newClassName.value.trim()) { message.warning('请输入班级名称'); return }
  try {
    await coachApi.createClass(newClassName.value.trim(), newClassDesc.value.trim())
    showCreateClassModal.value = false
    newClassName.value = ''
    newClassDesc.value = ''
    message.success('班级创建成功')
    loadData()
  } catch (err: any) { message.error(err?.response?.data?.detail || '创建失败') }
}

async function searchAvailableTrainees() {
  if (!traineeKeyword.value) { availableTrainees.value = []; return }
  try { availableTrainees.value = await coachApi.availableTrainees(traineeKeyword.value) }
  catch { message.error('搜索可添加学员失败') }
}

async function addStudent() {
  if (!selectedClassIdForAdd.value || !selectedTraineeId.value) return message.warning('请选择班级和学员')
  try {
    await coachApi.addStudent(selectedClassIdForAdd.value, selectedTraineeId.value)
    showAddStudentModal.value = false
    message.success('学员已加入班级')
    loadData()
  } catch (err: any) { message.error(err?.response?.data?.detail || '添加失败') }
}

async function removeStudentFromClass(studentId: number, classId: number) {
  try {
    await coachApi.removeStudent(classId, studentId)
    message.success('学员已移除')
    loadData()
  } catch (err: any) { message.error(err?.response?.data?.detail || '移除失败') }
}

function openEditClass(cls: any) {
  editingClass.value = { ...cls }
  showEditClassModal.value = true
}

async function saveClass() {
  if (!editingClass.value?.name?.trim()) return
  try {
    await coachApi.updateClass(editingClass.value.id, { name: editingClass.value.name, description: editingClass.value.description || '' })
    showEditClassModal.value = false
    message.success('班级已更新')
    loadData()
  } catch (err: any) { message.error(err?.response?.data?.detail || '更新失败') }
}

async function deleteClass(cls: any) {
  try {
    await coachApi.deleteClass(cls.id)
    message.success('班级已删除')
    loadData()
  } catch (err: any) { message.error(err?.response?.data?.detail || '删除失败') }
}

async function copyInviteCode(code: string) {
  try {
    await navigator.clipboard.writeText(code)
    message.success(`邀请码 ${code} 已复制`)
  } catch { message.error('复制失败') }
}

async function regenerateCode(classId: number) {
  try {
    const res = await coachApi.regenerateCode(classId)
    message.success(`邀请码已更新为 ${res.invite_code}`)
    loadData()
  } catch (err: any) { message.error(err?.response?.data?.detail || '刷新邀请码失败') }
}

// Student table columns
const studentColumns: DataTableColumns = [
  { title: 'ID', key: 'id', width: 50 },
  {
    title: '用户名', key: 'username', width: 110,
    render(row: any) {
      return h('a', { style: { color: '#3b82f6', cursor: 'pointer', fontWeight: 500 }, onClick: () => goToStudent(row.id) }, row.username)
    }
  },
  { title: '手机号', key: 'phone', width: 120, render: (r: any) => r.phone || '-' },
  {
    title: '所属班级', key: 'class', width: 130,
    render: (r: any) => r.class || '未分班'
  },
  {
    title: '操作', key: 'actions', width: 200,
    render(row: any) {
      const els: any[] = [
        h(NButton, { size: 'tiny', type: 'primary', onClick: () => goToStudent(row.id) }, { default: () => '查看详情' }),
      ]
      if (row.class_id) {
        els.push(h(NButton, { size: 'tiny', type: 'error', onClick: () => removeStudentFromClass(row.id, row.class_id!) }, { default: () => '移除' }))
      }
      return h('span', { style: { display: 'flex', gap: '6px', whiteSpace: 'nowrap' } }, els)
    }
  },
]

onMounted(() => { loadData() })
</script>

<script lang="ts">
export default { name: 'CoachView' }
</script>

<template>
  <div class="coach-page">
    <n-spin v-if="loading" style="display: flex; justify-content: center; padding: 60px;" />

    <template v-if="!loading">
      <n-card :bordered="false" class="header-card" size="large">
        <div class="header-content">
          <div class="header-left">
            <div class="header-icon">
              <n-icon size="28" :component="PeopleOutline" />
            </div>
            <div>
              <h2 class="page-title">教练工作台</h2>
              <p class="page-subtitle">管理您的学员和训练进度</p>
            </div>
          </div>
        </div>
      </n-card>

      <n-grid :cols="4" :x-gap="12" :y-gap="12" class="stats-grid">
        <n-grid-item>
          <n-card :bordered="false" class="stat-card" size="medium">
            <div class="stat-icon" style="background: #3b82f615; color: #3b82f6;">
              <n-icon size="22" :component="PeopleOutline" />
            </div>
            <div class="stat-value">{{ summary.total_students }}</div>
            <div class="stat-label">学员总数</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card :bordered="false" class="stat-card" size="medium">
            <div class="stat-icon" style="background: #10b98115; color: #10b981;">
              <n-icon size="22" :component="FitnessOutline" />
            </div>
            <div class="stat-value">{{ summary.sessions_7d }}</div>
            <div class="stat-label">本周训练</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card :bordered="false" class="stat-card" size="medium">
            <div class="stat-icon" style="background: #8b5cf615; color: #8b5cf6;">
              <n-icon size="22" :component="SchoolOutline" />
            </div>
            <div class="stat-value">{{ summary.class_count }}</div>
            <div class="stat-label">班级数量</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card :bordered="false" class="stat-card" size="medium">
            <div class="stat-icon" style="background: #f59e0b15; color: #f59e0b;">
              <n-icon size="22" :component="BarChartOutline" />
            </div>
            <div class="stat-value">{{ summary.sessions_30d }}</div>
            <div class="stat-label">本月训练</div>
          </n-card>
        </n-grid-item>
      </n-grid>

      <n-card :bordered="false" class="section-card" size="large">
        <n-tabs v-model:value="activeTab" type="line">
          <!-- 学员列表 tab -->
          <n-tab-pane name="trainees" tab="学员列表">
            <div class="search-bar">
              <n-input v-model:value="searchQuery" placeholder="搜索学员用户名或手机号" clearable>
                <template #prefix><n-icon :component="SearchOutline" /></template>
              </n-input>
              <n-button type="primary" @click="showAddStudentModal = true; selectedClassIdForAdd = null; traineeKeyword = ''; availableTrainees = []">
                <template #icon><n-icon :component="PersonAddOutline" /></template>
                添加学员
              </n-button>
            </div>

            <n-data-table
              v-if="filteredStudents.length"
              :columns="studentColumns"
              :data="filteredStudents"
              :row-key="(r: any) => `${r.id}-${r.class_id || ''}`"
              :pagination="filteredStudents.length > 20 ? { pageSize: 20, showSizePicker: true } : false"
              size="small"
            />

            <n-empty v-if="filteredStudents.length === 0 && !loading" description="暂无学员" style="padding: 40px 0;">
              <template #extra>
                <n-space>
                  <n-button type="primary" size="small" @click="showCreateClassModal = true">新建班级</n-button>
                  <n-button size="small" @click="showAddStudentModal = true">添加学员</n-button>
                </n-space>
              </template>
            </n-empty>
          </n-tab-pane>

          <!-- 班级管理 tab -->
          <n-tab-pane name="classes" tab="班级管理">
            <div class="search-bar">
              <n-button type="primary" @click="showCreateClassModal = true">
                <template #icon><n-icon :component="AddOutline" /></template>
                创建班级
              </n-button>
            </div>

            <n-grid v-if="classes.length > 0" :cols="3" :x-gap="14" :y-gap="14" responsive="screen">
              <n-grid-item v-for="cls in classes" :key="cls.id">
                <n-card class="class-card">
                  <template #header>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                      <div class="class-title-click" @click="goToClassDetail(cls.id)" style="display:flex;align-items:center;gap:10px;">
                        <div class="class-icon-badge"><n-icon size="18" :component="SchoolOutline" /></div>
                        <strong>{{ cls.name }}</strong>
                      </div>
                      <n-space size="small">
                        <n-button text size="tiny" @click="openEditClass(cls)" title="编辑">
                          <template #icon><n-icon :component="CreateOutline" /></template>
                        </n-button>
                        <n-popconfirm @positive-click="deleteClass(cls)">
                          <template #trigger>
                            <n-button text size="tiny" type="error" title="删除">
                              <template #icon><n-icon :component="TrashOutline" /></template>
                            </n-button>
                          </template>
                          确认删除班级"{{ cls.name }}"？
                        </n-popconfirm>
                      </n-space>
                    </div>
                  </template>
                  <template #header-extra>
                    <n-tag type="info" round size="small">{{ cls.student_count }}人</n-tag>
                  </template>

                  <p class="class-desc">{{ cls.description || '暂无描述' }}</p>

                  <!-- Invite code -->
                  <div class="invite-row">
                    <span class="invite-label">邀请码</span>
                    <n-tag type="info" class="invite-code" @click="copyInviteCode(cls.invite_code || '')">
                      {{ cls.invite_code || '---' }}
                    </n-tag>
                    <n-button text size="tiny" @click="copyInviteCode(cls.invite_code || '')" title="复制邀请码">
                      <template #icon><n-icon :component="CopyOutline" /></template>
                    </n-button>
                    <n-popconfirm @positive-click="regenerateCode(cls.id)">
                      <template #trigger>
                        <n-button text size="tiny" title="刷新邀请码">
                          <template #icon><n-icon :component="RefreshOutline" /></template>
                        </n-button>
                      </template>
                      确认刷新邀请码？旧邀请码将失效
                    </n-popconfirm>
                  </div>

                  <n-button type="primary" size="small" ghost block @click="goToClassDetail(cls.id)">
                    查看统计
                  </n-button>
                </n-card>
              </n-grid-item>
            </n-grid>

            <n-empty v-else description="暂无班级" style="padding: 40px 0;">
              <template #extra>
                <n-button type="primary" size="small" @click="showCreateClassModal = true">创建班级</n-button>
              </template>
            </n-empty>
          </n-tab-pane>

          <!-- 训练报告 tab -->
          <n-tab-pane name="reports" tab="训练报告">
            <n-list v-if="students.length" clickable>
              <n-list-item v-for="student in students" :key="student.id" @click="goToStudent(student.id)">
                <div class="trainee-item">
                  <div class="trainee-left">
                    <n-avatar round :fallback-char="student.username[0]" />
                    <div class="trainee-info">
                      <div class="trainee-name">{{ student.username }}</div>
                      <div class="trainee-meta">查看评估、训练计划与训练记录</div>
                    </div>
                  </div>
                  <n-icon size="20" :component="ChevronForwardOutline" class="arrow-icon" />
                </div>
              </n-list-item>
            </n-list>
            <n-empty v-else description="暂无可查看的学员报告" style="padding: 40px 0;" />
          </n-tab-pane>
        </n-tabs>
      </n-card>
    </template>

    <!-- Create class modal -->
    <n-modal v-model:show="showCreateClassModal" preset="card" title="创建班级" style="width: 440px;">
      <n-form label-placement="top">
        <n-form-item label="班级名称">
          <n-input v-model:value="newClassName" placeholder="请输入班级名称" />
        </n-form-item>
        <n-form-item label="班级描述">
          <n-input v-model:value="newClassDesc" placeholder="请输入班级描述（选填）" type="textarea" :rows="2" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showCreateClassModal = false">取消</n-button>
          <n-button type="primary" @click="createClass">创建</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- Add student modal -->
    <n-modal v-model:show="showAddStudentModal" preset="card" title="添加学员到班级" style="width: 480px;">
      <n-form label-placement="top">
        <n-form-item label="目标班级">
          <n-select v-model:value="selectedClassIdForAdd" :options="classes.map(c => ({ label: `${c.name}（${c.student_count}人）`, value: c.id }))" placeholder="请选择班级" />
        </n-form-item>
        <n-form-item label="搜索学员">
          <n-input v-model:value="traineeKeyword" placeholder="输入用户名搜索" @keyup.enter="searchAvailableTrainees">
            <template #suffix><n-button text @click="searchAvailableTrainees">搜索</n-button></template>
          </n-input>
        </n-form-item>
        <n-form-item label="选择学员">
          <n-select v-model:value="selectedTraineeId" filterable :options="availableTrainees.map(u => ({ label: `${u.username}${u.phone ? `（${u.phone}）` : ''}`, value: u.id }))" placeholder="请选择学员" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showAddStudentModal = false">取消</n-button>
          <n-button type="primary" @click="addStudent">确认添加</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- Edit class modal -->
    <n-modal v-model:show="showEditClassModal" preset="card" title="编辑班级" style="width: 440px;">
      <n-form v-if="editingClass" label-placement="top">
        <n-form-item label="班级名称"><n-input v-model:value="editingClass.name" /></n-form-item>
        <n-form-item label="班级描述"><n-input v-model:value="editingClass.description" type="textarea" :rows="2" /></n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showEditClassModal = false">取消</n-button>
          <n-button type="primary" @click="saveClass">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.coach-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.header-card {
  background: linear-gradient(135deg, #5E74F8, #7B6CFF, #9A68D8) !important;
  color: white;
  border-radius: 16px !important;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 4px 0;
  color: white;
}

.page-subtitle {
  font-size: 13px;
  margin: 0;
  color: rgba(255, 255, 255, 0.85);
}

.stats-grid {
  margin-top: 0 !important;
}

.stat-card {
  border-radius: 12px !important;
  text-align: center;
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

.section-card {
  border-radius: 12px !important;
}

.search-bar {
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
}

.trainee-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.trainee-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.trainee-name {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
}

.trainee-meta {
  font-size: 12px;
  color: #64748b;
  display: flex;
  gap: 6px;
  align-items: center;
}

.arrow-icon {
  color: #94a3b8;
}

.class-card {
  border-radius: 12px !important;
  cursor: pointer;
  height: 100%;
}

.class-desc {
  color: #64748b;
  font-size: 13px;
  min-height: 20px;
  margin: 0 0 12px;
}

.invite-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f6f8fa;
  border-radius: 8px;
  margin-bottom: 12px;
}

.invite-label {
  font-size: 12px;
  color: #94a3b8;
  flex-shrink: 0;
}

.invite-code {
  font-family: monospace;
  font-size: 13px;
  letter-spacing: 2px;
  cursor: pointer;
  flex: 1;
  text-align: center;
}

.class-title-click {
  cursor: pointer;
  padding: 2px 6px;
  margin: -2px -6px;
  border-radius: 6px;
  transition: background 0.15s;
}
.class-title-click:hover {
  background: rgba(0, 0, 0, 0.04);
}

.class-icon-badge {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #f0fdf4;
  color: #10b981;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 768px) {
  .stats-grid {
    gap: 8px !important;
  }

  .stat-value {
    font-size: 20px;
  }

  .search-bar {
    flex-direction: column;
  }
}
</style>
