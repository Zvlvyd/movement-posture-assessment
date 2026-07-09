<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { messageApi } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { Conversation, MessageItem } from '../types'
import {
  NButton, NIcon, NAvatar, NTag, NSpace, NCard,
  NInput, NEmpty, NSpin, NBadge
} from 'naive-ui'
import {
  ChatbubblesOutline, SearchOutline, RefreshOutline,
  SendOutline, ChevronForwardOutline
} from '@vicons/ionicons5'

const router = useRouter()
const notice = useMessage()
const auth = useAuthStore()
const conversations = ref<Conversation[]>([])
const messages = ref<MessageItem[]>([])
const selectedPartner = ref<number | null>(null)
const loading = ref(true)
const detailLoading = ref(false)
const sending = ref(false)
const newMessage = ref('')
const unread = ref(0)
const messagePane = ref<HTMLElement | null>(null)
const searchQuery = ref('')
let pollTimer: number | undefined

const selected = computed(() => conversations.value.find(item => item.partner_id === selectedPartner.value))

const filteredConversations = computed(() => {
  if (!searchQuery.value.trim()) return conversations.value
  const q = searchQuery.value.trim().toLowerCase()
  return conversations.value.filter(c =>
    c.partner_name.toLowerCase().includes(q) ||
    c.last_message.toLowerCase().includes(q)
  )
})

async function loadConversations(showLoading = true) {
  if (showLoading) loading.value = true
  try {
    const [list, count] = await Promise.all([messageApi.conversations(), messageApi.unreadCount()])
    conversations.value = list.conversations || []
    unread.value = count.unread_count || 0
  } catch (error: any) {
    if (showLoading) notice.error(error?.response?.data?.detail || '消息加载失败')
  } finally { loading.value = false }
}

async function selectConversation(partnerId: number) {
  selectedPartner.value = partnerId
  detailLoading.value = true
  try {
    const data = await messageApi.getWith(partnerId)
    messages.value = data.messages || []
    await nextTick()
    messagePane.value?.scrollTo({ top: messagePane.value.scrollHeight })
    await loadConversations(false)
  } catch { notice.error('对话加载失败') }
  finally { detailLoading.value = false }
}

async function sendMessage() {
  const content = newMessage.value.trim()
  if (!content || !selectedPartner.value) return
  sending.value = true
  try {
    await messageApi.send(selectedPartner.value, content)
    newMessage.value = ''
    await selectConversation(selectedPartner.value)
  } catch (error: any) { notice.error(error?.response?.data?.detail || '发送失败') }
  finally { sending.value = false }
}

function onInputKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendMessage() }
}

onMounted(() => {
  loadConversations()
  pollTimer = window.setInterval(() => loadConversations(false), 30000)
})
onBeforeUnmount(() => window.clearInterval(pollTimer))
</script>

<template>
  <div class="messages-page">

    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <div class="header-icon-wrap">
          <n-icon size="22" :component="ChatbubblesOutline" />
        </div>
        <div>
          <h2 class="header-title">消息中心</h2>
          <p class="header-subtitle">查看教练消息、AI 提醒和系统通知</p>
        </div>
      </div>
      <n-button
        text
        class="refresh-btn"
        @click="loadConversations()"
      >
        <template #icon><n-icon :component="RefreshOutline" size="18" /></template>
      </n-button>
    </div>

    <!-- Two-column layout -->
    <div class="messenger-body">
      <!-- Left: conversation list -->
      <div class="left-panel">
        <div class="panel-card">
          <!-- Search -->
          <div class="search-wrap">
            <n-icon size="16" :component="SearchOutline" class="search-icon" />
            <input
              v-model="searchQuery"
              class="search-input"
              placeholder="搜索消息"
              type="text"
            />
          </div>

          <!-- Empty state -->
          <div v-if="!loading && conversations.length === 0" class="left-empty">
            <div class="left-empty-icon">
              <n-icon size="36" :component="ChatbubblesOutline" />
            </div>
            <p class="left-empty-title">暂无消息</p>
            <p class="left-empty-desc">加入班级后即可接收教练消息</p>
          </div>

          <!-- Conversation list -->
          <div v-else class="conv-list">
            <div
              v-for="item in filteredConversations"
              :key="item.partner_id"
              class="conv-item"
              :class="{ active: selectedPartner === item.partner_id }"
              @click="selectConversation(item.partner_id)"
            >
              <div class="conv-avatar-wrap">
                <n-avatar
                  round
                  :size="42"
                  :fallback-char="item.partner_name?.[0] || '?'"
                  :style="{ background: item.partner_role === 'coach'
                    ? 'linear-gradient(135deg, #7B6CFF, #5C8CFF)'
                    : 'linear-gradient(135deg, #10b981, #06b6d4)' }"
                />
                <div v-if="item.unread_count" class="unread-dot"></div>
              </div>
              <div class="conv-info">
                <div class="conv-top">
                  <span class="conv-name">{{ item.partner_name }}</span>
                  <span class="conv-role">{{ item.partner_role === 'coach' ? '教练' : '学员' }}</span>
                  <span class="conv-time">{{ item.last_time?.slice(5, 16) || '' }}</span>
                </div>
                <div class="conv-msg">{{ item.last_message }}</div>
              </div>
              <n-badge v-if="item.unread_count" :value="item.unread_count" />
            </div>

            <!-- No search results -->
            <div v-if="filteredConversations.length === 0 && conversations.length > 0" class="left-empty">
              <p class="left-empty-desc">未找到匹配的对话</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: chat area -->
      <div class="right-panel">
        <div class="panel-card chat-card">

          <!-- Chat header -->
          <div v-if="selected" class="chat-header">
            <n-avatar
              round
              :size="36"
              :fallback-char="selected.partner_name?.[0] || '?'"
              :style="{ background: selected.partner_role === 'coach'
                ? 'linear-gradient(135deg, #7B6CFF, #5C8CFF)'
                : 'linear-gradient(135deg, #10b981, #06b6d4)' }"
            />
            <div class="chat-header-info">
              <span class="chat-header-name">{{ selected.partner_name }}</span>
              <span class="chat-header-role">{{ selected.partner_role === 'coach' ? '教练' : '学员' }}</span>
            </div>
          </div>

          <!-- Empty state (no conversation selected) -->
          <div v-if="!selectedPartner" class="chat-empty">
            <img src="/chat.png" alt="" class="chat-illustration" />
            <h3 class="chat-empty-title">暂无聊天</h3>
            <p class="chat-empty-desc">加入班级后即可与教练交流、接收 AI 建议和系统通知</p>
            <n-button
              class="gradient-btn"
              size="large"
              @click="router.push('/my-classes')"
            >
              去加入班级
              <template #suffix>
                <n-icon :component="ChevronForwardOutline" />
              </template>
            </n-button>
          </div>

          <!-- Chat messages -->
          <template v-else>
            <n-spin :show="detailLoading" class="chat-spin">
              <div ref="messagePane" class="message-pane">
                <n-empty v-if="!messages.length" description="暂无消息，发送第一条消息吧" />
                <div
                  v-for="item in messages"
                  :key="item.id"
                  class="bubble-row"
                  :class="{ me: item.sender_id === auth.user?.id }"
                >
                  <div class="bubble">
                    <span>{{ item.content }}</span>
                    <time>{{ item.created_at?.slice(0, 16) }}</time>
                  </div>
                </div>
              </div>
            </n-spin>

            <!-- Composer -->
            <div class="composer">
              <n-input
                v-model:value="newMessage"
                type="textarea"
                autosize
                placeholder="输入消息（Enter 发送，Shift+Enter 换行）"
                @keydown="onInputKeydown"
                class="composer-input"
              />
              <n-button
                class="send-btn"
                :loading="sending"
                :disabled="!newMessage.trim()"
                @click="sendMessage"
              >
                <template #icon><n-icon :component="SendOutline" /></template>
              </n-button>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── Page ── */
.messages-page {
  position: relative;
  min-height: calc(100vh - 64px - 56px);
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #faf9ff 0%, #f5f4ff 55%, #ffffff 100%);
  margin: -24px;
  padding: 24px 40px;
  gap: 20px;
}

.messages-page::before {
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

/* ── Header ── */
.page-header {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.header-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(123,108,255,0.12), rgba(92,140,255,0.08));
  display: flex;
  align-items: center;
  justify-content: center;
  color: #7B6CFF;
}
.header-title {
  font-size: 24px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 2px;
  line-height: 1.3;
}
.header-subtitle {
  font-size: 14px;
  color: #8B8B99;
  margin: 0;
}
.refresh-btn {
  color: #94a3b8 !important;
  transition: color 0.2s;
}
.refresh-btn:hover {
  color: #7B6CFF !important;
}

/* ── Two-column layout ── */
.messenger-body {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  gap: 16px;
  min-height: 0;
}
.left-panel {
  width: 320px;
  flex-shrink: 0;
}
.right-panel {
  flex: 1;
  min-width: 0;
}

/* ── Card shell ── */
.panel-card {
  height: 100%;
  background: rgba(255,255,255,0.82);
  backdrop-filter: blur(18px);
  border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.8);
  box-shadow: 0 12px 40px rgba(108,99,255,0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── Search ── */
.search-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(0,0,0,0.04);
  flex-shrink: 0;
}
.search-icon {
  color: #94a3b8;
  flex-shrink: 0;
}
.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: #334155;
}
.search-input::placeholder {
  color: #cbd5e1;
}

/* ── Left empty state ── */
.left-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 24px;
  text-align: center;
}
.left-empty-icon {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  background: rgba(123,108,255,0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #7B6CFF;
  margin-bottom: 14px;
}
.left-empty-title {
  font-size: 15px;
  font-weight: 600;
  color: #475569;
  margin: 0 0 6px;
}
.left-empty-desc {
  font-size: 13px;
  color: #8B8B99;
  margin: 0;
}

/* ── Conversation list ── */
.conv-list {
  flex: 1;
  overflow-y: auto;
}
.conv-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid rgba(0,0,0,0.03);
}
.conv-item:hover {
  background: rgba(123,108,255,0.04);
}
.conv-item.active {
  background: rgba(123,108,255,0.07);
}
.conv-avatar-wrap {
  position: relative;
  flex-shrink: 0;
}
.unread-dot {
  position: absolute;
  top: 0;
  right: 0;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ef4444;
  border: 2px solid #fff;
}
.conv-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.conv-top {
  display: flex;
  align-items: center;
  gap: 6px;
}
.conv-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}
.conv-role {
  font-size: 11px;
  color: #7B6CFF;
  background: rgba(123,108,255,0.08);
  padding: 1px 6px;
  border-radius: 4px;
}
.conv-time {
  margin-left: auto;
  font-size: 11px;
  color: #94a3b8;
  flex-shrink: 0;
}
.conv-msg {
  font-size: 13px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Chat card ── */
.chat-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* ── Chat header ── */
.chat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(0,0,0,0.04);
  flex-shrink: 0;
}
.chat-header-info {
  display: flex;
  flex-direction: column;
}
.chat-header-name {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}
.chat-header-role {
  font-size: 12px;
  color: #7B6CFF;
}

/* ── Chat empty state ── */
.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 32px;
  text-align: center;
}
.chat-illustration {
  width: 360px;
  object-fit: contain;
  margin-top: -24px;
  margin-bottom: 16px;
  opacity: 0.75;
  mask-image: radial-gradient(ellipse 65% 60% at 50% 45%, black 35%, transparent 75%);
  -webkit-mask-image: radial-gradient(ellipse 65% 60% at 50% 45%, black 35%, transparent 75%);
}
.chat-empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 8px;
}
.chat-empty-desc {
  font-size: 14px;
  color: #8B8B99;
  max-width: 380px;
  line-height: 1.6;
  margin: 0 0 28px;
}

/* ── Gradient button ── */
.gradient-btn {
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
.gradient-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(123,108,255,0.35);
}
.gradient-btn :deep(.n-button__border),
.gradient-btn :deep(.n-button__state-border) {
  border: none !important;
}

/* ── Messages pane ── */
.chat-spin {
  flex: 1;
  min-height: 0;
}
.chat-spin :deep(.n-spin-content) {
  height: 100%;
}
.message-pane {
  height: 100%;
  overflow-y: auto;
  padding: 20px;
}
.bubble-row {
  display: flex;
  margin-bottom: 14px;
}
.bubble-row.me {
  justify-content: flex-end;
}
.bubble {
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 4px 14px 14px;
  background: #f1f5f9;
  display: flex;
  flex-direction: column;
  gap: 4px;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.5;
}
.me .bubble {
  background: linear-gradient(135deg, #7B6CFF, #5C8CFF);
  color: #fff;
  border-radius: 14px 4px 14px 14px;
}
.bubble time {
  font-size: 11px;
  color: #94a3b8;
}
.me .bubble time {
  color: rgba(255,255,255,0.7);
}

/* ── Composer ── */
.composer {
  display: flex;
  gap: 10px;
  padding: 14px 18px;
  border-top: 1px solid rgba(0,0,0,0.04);
  flex-shrink: 0;
  align-items: flex-end;
}
.composer-input {
  flex: 1;
}
.send-btn {
  background: linear-gradient(135deg, #7B6CFF, #5C8CFF) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 10px !important;
  width: 40px !important;
  height: 40px !important;
  flex-shrink: 0;
}
.send-btn :deep(.n-button__border),
.send-btn :deep(.n-button__state-border) {
  border: none !important;
}

/* ── Mobile ── */
@media (max-width: 768px) {
  .messages-page {
    padding: 16px;
    margin: -16px;
  }
  .messenger-body {
    flex-direction: column;
  }
  .left-panel {
    width: 100%;
    height: 280px;
  }
  .right-panel {
    flex: 1;
    min-height: 400px;
  }
  .header-title {
    font-size: 20px;
  }
  .chat-illustration {
    width: 260px;
    margin-top: -12px;
  }
}
</style>
