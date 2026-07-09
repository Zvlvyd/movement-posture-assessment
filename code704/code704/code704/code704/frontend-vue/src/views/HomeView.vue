<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { recordsApi, prescriptionApi } from '../services/api'
import type { TrainingRecord, Prescription } from '../types'
import {
  NCard, NButton, NSpace, NIcon, NAvatar,
  NList, NListItem, NText, NTag, NGrid, NGridItem
} from 'naive-ui'
import {
  PlayCircleOutline, BodyOutline, AnalyticsOutline,
  ListOutline, ChevronForwardOutline, FitnessOutline
} from '@vicons/ionicons5'

const router = useRouter()
const authStore = useAuthStore()

const prescription = ref<Prescription | null>(null)
const todayRecords = ref<TrainingRecord[]>([])
const loading = ref(true)

const quickActions = [
  { title: '体态评估', desc: 'AI智能体态分析', icon: BodyOutline, path: '/assessment', color: '#3b82f6' },
  { title: 'FMS筛查', desc: '功能性动作测试', icon: AnalyticsOutline, path: '/fms', color: '#8b5cf6' },
  { title: '标准学习', desc: '标准动作跟练', icon: PlayCircleOutline, path: '/training', color: '#10b981' },
  { title: 'AI训练方案', desc: 'AI智能生成训练方案', icon: ListOutline, path: '/prescription-training', color: '#f59e0b' }
]

onMounted(() => {
  Promise.all([
    prescriptionApi.list().then(rxs => { if (rxs.length > 0) prescription.value = rxs[0] }).catch(() => {}),
    recordsApi.history(1).then(records => { todayRecords.value = records }).catch(() => {})
  ]).finally(() => { loading.value = false })
})

function goTo(path: string) {
  router.push(path)
}
</script>

<script lang="ts">
export default { name: 'HomeView' }
</script>

<template>
  <div class="home-page">
    <n-card :bordered="false" class="welcome-card" size="large">
      <div class="welcome-content">
        <div class="welcome-avatar">
          <n-avatar round :size="56" :fallback-char="authStore.user?.username?.[0] || 'U'" color="#7c3aed" style="background: #7c3aed; color: #fff" />
        </div>
        <div class="welcome-text">
          <h2 class="welcome-title">欢迎回来，{{ authStore.user?.username }}</h2>
          <p class="welcome-subtitle">每天更标准一点点。首次使用建议先完成体态评估和FMS筛查，系统会根据评估结果为你生成专属训练方案。</p>
        </div>
      </div>
    </n-card>

    <div class="start-training-banner">
      <img class="banner-bg-img" src="/ai.png" alt="" />
      <div class="circle-btn" @click="goTo('/training')">
        <div class="circle-ring"></div>
        <img class="start-training-icon" src="/media/pictures/start.png" alt="开始训练" />
        <span class="circle-label">开始训练</span>
      </div>
    </div>

    <n-card :bordered="false" class="section-card" size="large">
      <template #header>
        <div class="card-header">
          <span class="card-title">今日训练内容</span>
        </div>
      </template>

      <div v-if="prescription && prescription.items.length > 0" class="today-training">
        <n-space class="prescription-tags">
          <n-tag :type="prescription.status === 'active' ? 'success' : 'default'" round>
            {{ prescription.status === 'active' ? '进行中' : prescription.status }}
          </n-tag>
        </n-space>
        <n-list size="medium" class="rx-list">
          <n-list-item v-for="item in prescription.items.slice(0, 6)" :key="item.id" class="rx-item">
            <div class="rx-item-left">
              <div class="rx-dot"></div>
              <span class="rx-name">{{ item.action_name }}</span>
            </div>
            <span class="rx-detail">{{ item.sets }}组 × {{ item.reps }}次</span>
          </n-list-item>
        </n-list>
      </div>

      <div v-else class="empty-training">
        <n-icon size="48" class="empty-icon" :component="FitnessOutline" />
        <n-text depth="3" class="empty-text">暂无训练内容</n-text>
        <n-text depth="3" class="empty-subtext">请先完成体态评估获取专属训练方案</n-text>
        <n-button type="primary" size="medium" @click="goTo('/assessment')" style="margin-top: 12px">
          去评估
        </n-button>
      </div>
    </n-card>

  </div>
</template>

<style scoped>
.home-page {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.welcome-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white;
  border-radius: 16px !important;
  overflow: hidden;
  position: relative;
}

.welcome-card::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -10%;
  width: 300px;
  height: 300px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
}

.welcome-card::after {
  content: '';
  position: absolute;
  bottom: -30%;
  right: 20%;
  width: 200px;
  height: 200px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 50%;
}

.welcome-content {
  display: flex;
  align-items: center;
  gap: 16px;
  position: relative;
  z-index: 1;
}

.welcome-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: 3px solid rgba(255, 255, 255, 0.3);
  overflow: hidden;
  flex-shrink: 0;
}

.welcome-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 4px 0;
  color: white;
}

.welcome-subtitle {
  font-size: 14px;
  margin: 0;
  color: rgba(255, 255, 255, 0.85);
}
.welcome-guide {
  font-size: 15px;
  margin: 12px auto 0 auto;
  color: rgba(255, 255, 255, 0.82);
  line-height: 1.6;
  max-width: 520px;
  text-align: center;
}

.start-training-banner {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  border-radius: 20px;
  min-height: 360px;
}

.banner-bg-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: 50% 85%;
  opacity: 0.35;
  pointer-events: none;
  z-index: 0;
}

.circle-btn {
  position: relative;
  z-index: 1;
  width: 170px;
  height: 170px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: white;
  cursor: pointer;
  position: relative;
  transition: all 0.3s ease;
  box-shadow: 0 0 0 12px rgba(102, 126, 234, 0.12), 0 8px 24px -6px rgba(102, 126, 234, 0.4);
}

.circle-btn:hover {
  transform: scale(1.06);
  box-shadow: 0 0 0 16px rgba(102, 126, 234, 0.18), 0 14px 36px -8px rgba(102, 126, 234, 0.5);
}

.circle-btn:active {
  transform: scale(0.97);
}

.start-training-icon {
  width: 94px;
  height: 94px;
  border-radius: 50%;
  object-fit: cover;
  opacity: 0.92;
  mix-blend-mode: screen;
  filter: contrast(1.12);
  pointer-events: none;
}

.circle-ring {
  position: absolute;
  inset: -6px;
  border-radius: 50%;
  border: 2px dashed rgba(255, 255, 255, 0.25);
  animation: ring-spin 12s linear infinite;
  pointer-events: none;
}

@keyframes ring-spin {
  to { transform: rotate(360deg); }
}

.circle-label {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 1px;
}

.section-card {
  border-radius: 12px !important;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.prescription-tags {
  margin-bottom: 12px;
}

.rx-list {
  max-height: 280px;
  overflow-y: auto;
}

.rx-item {
  padding: 10px 0 !important;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04) !important;
}

:deep(.dark) .rx-item {
  border-bottom-color: rgba(255, 255, 255, 0.06) !important;
}

.rx-item:last-child {
  border-bottom: none !important;
}

.rx-item-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rx-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3b82f6;
  flex-shrink: 0;
}

.rx-name {
  font-size: 14px;
  font-weight: 500;
}

.rx-detail {
  font-size: 13px;
  color: #64748b;
}

.empty-training {
  text-align: center;
  padding: 32px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.empty-icon {
  color: #cbd5e1;
  margin-bottom: 12px;
}

:deep(.dark) .empty-icon {
  color: #475569;
}

.empty-text {
  font-size: 15px;
  font-weight: 500;
  margin-bottom: 4px;
}

.empty-subtext {
  font-size: 13px;
}

.action-card {
  padding: 16px;
  border-radius: 10px;
  background: #f8fafc;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
}

:deep(.dark) .action-card {
  background: rgba(255, 255, 255, 0.04);
}

.action-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.1);
}

.action-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.action-info {
  flex: 1;
  min-width: 0;
}

.action-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 2px;
}

.action-desc {
  font-size: 12px;
  color: #64748b;
}

.action-arrow {
  color: #94a3b8;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .welcome-content {
    flex-direction: column;
    text-align: center;
  }

  .welcome-title {
    font-size: 18px;
  }

  .start-training-banner {
    min-height: 260px;
  }

  .circle-btn {
    width: 120px;
    height: 120px;
  }

  .start-training-icon {
    width: 66px;
    height: 66px;
  }

  .circle-label {
    font-size: 11px;
  }

  .action-card {
    padding: 12px;
  }

  .action-icon {
    width: 36px;
    height: 36px;
  }
}

</style>
