<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useDialog, useMessage } from 'naive-ui'
import { studentClassApi } from '../services/api'
import type { MyClassInfo } from '../types'
import {
  NButton, NIcon, NTag, NSpace, NCard, NModal,
  NInput, NSpin
} from 'naive-ui'
import {
  AddOutline, PeopleOutline,
  CopyOutline, LogOutOutline
} from '@vicons/ionicons5'

const message = useMessage()
const dialog = useDialog()
const classes = ref<MyClassInfo[]>([])
const loading = ref(true)
const joining = ref(false)
const showJoin = ref(false)
const inviteCode = ref('')

async function loadClasses() {
  loading.value = true
  try {
    const data = await studentClassApi.myClasses()
    classes.value = data.classes || []
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '班级列表加载失败')
  } finally {
    loading.value = false
  }
}

async function joinClass() {
  const code = inviteCode.value.trim().toUpperCase()
  if (code.length !== 8) return message.warning('请输入8位邀请码')
  joining.value = true
  try {
    const data = await studentClassApi.join(code)
    message.success(data.message || '加入成功')
    showJoin.value = false
    inviteCode.value = ''
    await loadClasses()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '加入失败，请检查邀请码')
  } finally {
    joining.value = false
  }
}

function leaveClass(item: MyClassInfo) {
  dialog.warning({
    title: '确认退出班级？',
    content: `退出后将无法查看「${item.class_name}」的训练数据。`,
    positiveText: '确认退出',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const data = await studentClassApi.leaveClass(item.class_id)
        message.success(data.message || '已退出班级')
        await loadClasses()
      } catch (error: any) {
        message.error(error?.response?.data?.detail || '退出失败')
      }
    }
  })
}

async function copyCode(code = '') {
  try { await navigator.clipboard.writeText(code); message.success('邀请码已复制') }
  catch { message.error('复制失败') }
}

onMounted(loadClasses)
</script>

<template>
  <div class="classes-page">

    <!-- Watermark illustration -->
    <img src="/class.png" alt="" class="bg-illustration" />

    <!-- Content area -->
    <div class="page-body">
      <n-spin :show="loading">

        <!-- Empty state card -->
        <div v-if="!loading && classes.length === 0" class="empty-card">
          <div class="card-icon-wrap">
            <n-icon size="36" :component="PeopleOutline" class="card-icon" />
          </div>
          <h2 class="card-title">加入班级，获取专业指导</h2>
          <p class="card-subtitle">输入教练分享的邀请码，即可加入班级并接受教练的专业指导</p>
          <n-button class="join-btn" size="large" @click="showJoin = true">
            <template #icon>
              <n-icon :component="AddOutline" />
            </template>
            加入班级
          </n-button>
        </div>

        <!-- Class list -->
        <div v-else-if="!loading && classes.length > 0" class="class-list">
          <div class="list-header">
            <span class="list-title">已加入 {{ classes.length }} 个班级</span>
            <n-button class="join-btn" size="small" @click="showJoin = true">
              <template #icon>
                <n-icon :component="AddOutline" />
              </template>
              加入班级
            </n-button>
          </div>
          <n-card
            v-for="item in classes"
            :key="item.class_id"
            :bordered="false"
            class="class-card"
          >
            <div class="class-row">
              <div class="class-main">
                <h3 class="class-name">{{ item.class_name }}</h3>
                <p v-if="item.description" class="class-desc">{{ item.description }}</p>
                <n-space>
                  <n-tag type="info" size="small" round :bordered="false">教练：{{ item.coach.username }}</n-tag>
                  <span v-if="item.coach.phone" class="coach-phone">{{ item.coach.phone }}</span>
                </n-space>
              </div>
              <div class="class-meta">
                <span class="meta-label">邀请码</span>
                <n-tag
                  type="info" size="large" :bordered="false"
                  class="invite-tag"
                  @click="copyCode(item.invite_code)"
                >
                  {{ item.invite_code || '---' }}
                  <template #icon><n-icon :component="CopyOutline" size="14" /></template>
                </n-tag>
                <span class="meta-count">{{ item.student_count }} 名学员</span>
                <span class="meta-date">创建于 {{ new Date(item.created_at).toLocaleDateString() }}</span>
              </div>
            </div>
            <template #action>
              <n-space justify="end">
                <n-button text type="primary" size="small" @click="copyCode(item.invite_code)">
                  <template #icon><n-icon :component="CopyOutline" /></template>
                  复制邀请码
                </n-button>
                <n-button text type="error" size="small" @click="leaveClass(item)">
                  <template #icon><n-icon :component="LogOutOutline" /></template>
                  退出班级
                </n-button>
              </n-space>
            </template>
          </n-card>
        </div>
      </n-spin>
    </div>

    <!-- Join modal -->
    <n-modal v-model:show="showJoin" preset="card" title="加入班级" style="width: min(460px, 92vw); border-radius: 16px;">
      <p style="color: #64748b; font-size: 14px; margin-bottom: 16px;">请输入教练分享的8位班级邀请码</p>
      <n-input
        v-model:value="inviteCode"
        maxlength="8"
        size="large"
        placeholder="例如 A3B7K9M2"
        class="code-input"
        @keyup.enter="joinClass"
      />
      <template #footer>
        <n-space justify="end">
          <n-button @click="showJoin = false">取消</n-button>
          <n-button type="primary" :loading="joining" @click="joinClass">加入</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
/* ── Page shell ── */
.classes-page {
  position: relative;
  min-height: calc(100vh - 64px - 56px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(180deg, #faf9ff 0%, #f5f4ff 55%, #ffffff 100%);
  margin: -24px;
  padding: 24px;
}

/* ── Background ── */
.classes-page::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(rgba(108,99,255,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(108,99,255,0.04) 1px, transparent 1px);
  background-size: 30px 30px, 30px 30px;
  z-index: 0;
  pointer-events: none;
}

/* ── Watermark illustration ── */
.bg-illustration {
  position: absolute;
  right: -4%;
  top: 8%;
  width: 38%;
  opacity: 0.08;
  z-index: 0;
  pointer-events: none;
  user-select: none;
}

/* ── Body ── */
.page-body {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 6vh;
}

/* ── Empty state card ── */
.empty-card {
  width: 600px;
  min-height: 280px;
  background: rgba(255,255,255,0.78);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,0.75);
  border-radius: 20px;
  box-shadow: 0 12px 40px rgba(108,99,255,0.10);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 40px;
  text-align: center;
}
.card-icon-wrap {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(123,108,255,0.12), rgba(92,140,255,0.08));
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}
.card-icon {
  color: #7B6CFF;
}
.card-title {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 10px;
}
.card-subtitle {
  font-size: 14px;
  color: #64748b;
  line-height: 1.6;
  margin: 0 0 28px;
  max-width: 420px;
}

/* ── Join button ── */
.join-btn {
  background: linear-gradient(135deg, #7B6CFF, #5C8CFF) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 12px !important;
  padding: 12px 28px !important;
  font-weight: 600 !important;
  font-size: 15px !important;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
  box-shadow: 0 4px 16px rgba(123,108,255,0.25);
}
.join-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(123,108,255,0.35);
}
.join-btn:active {
  transform: translateY(0);
}
.join-btn :deep(.n-button__border),
.join-btn :deep(.n-button__state-border) {
  border: none !important;
}

/* ── Class list ── */
.class-list {
  width: 100%;
  max-width: 860px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.list-title {
  font-size: 15px;
  font-weight: 600;
  color: #475569;
}
.class-card {
  border-radius: 14px !important;
  background: rgba(255,255,255,0.78) !important;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.75) !important;
  box-shadow: 0 4px 20px rgba(108,99,255,0.06);
  transition: all 0.25s ease;
}
.class-card:hover {
  box-shadow: 0 8px 30px rgba(108,99,255,0.10);
  transform: translateY(-1px);
}
.class-row {
  display: flex;
  justify-content: space-between;
  gap: 32px;
}
.class-main {
  flex: 1;
  min-width: 0;
}
.class-name {
  font-size: 17px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 8px;
}
.class-desc {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 12px;
}
.coach-phone {
  font-size: 12px;
  color: #94a3b8;
}
.class-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  flex-shrink: 0;
  min-width: 140px;
}
.meta-label {
  font-size: 11px;
  color: #94a3b8;
}
.invite-tag {
  font-family: monospace;
  font-size: 15px;
  letter-spacing: 3px;
  cursor: pointer;
  transition: all 0.2s;
}
.invite-tag:hover {
  transform: scale(1.04);
}
.meta-count {
  font-size: 12px;
  color: #64748b;
}
.meta-date {
  font-size: 12px;
  color: #94a3b8;
}

/* ── Code input ── */
.code-input :deep(input) {
  font-family: monospace;
  letter-spacing: 4px;
  text-align: center;
  text-transform: uppercase;
}

/* ── Mobile ── */
@media (max-width: 768px) {
  .empty-card {
    width: 100%;
    padding: 36px 24px;
    min-height: auto;
  }
  .card-title {
    font-size: 18px;
  }
  .card-subtitle {
    font-size: 13px;
  }
  .bg-illustration {
    width: 60%;
    right: -10%;
    opacity: 0.05;
  }
  .class-row {
    flex-direction: column;
    gap: 16px;
  }
  .class-meta {
    align-items: flex-start;
  }
}
</style>
