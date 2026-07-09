<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NCard, NButton, NSpace, NSpin, NDescriptions, NDescriptionsItem,
  NTag, NIcon, NList, NListItem
} from 'naive-ui'
import {
  CheckmarkCircleOutline, ArrowBackOutline, TrophyOutline,
  TimeOutline, BarbellOutline
} from '@vicons/ionicons5'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const report = ref<any>(null)

onMounted(() => {
  setTimeout(() => {
    report.value = {
      id: route.params.id || 1,
      prescription_id: 1,
      phase: 1,
      start_time: new Date(Date.now() - 1800000).toISOString(),
      end_time: new Date().toISOString(),
      total_score: 84.5,
      completed: true,
      items: [
        { name: '猫牛式', score: 90, sets: 3, reps: 10, completed: true },
        { name: '鸟狗式', score: 82, sets: 3, reps: 8, completed: true },
        { name: '臀桥', score: 88, sets: 3, reps: 12, completed: true },
        { name: '死虫式', score: 78, sets: 3, reps: 10, completed: true },
        { name: '婴儿式', score: 95, sets: 2, reps: 1, completed: true }
      ],
      feedback: [
        { type: 'good', text: '整体动作标准度良好，继续保持！' },
        { type: 'warning', text: '死虫式动作中腰部略有抬起，注意核心收紧' },
        { type: 'info', text: '建议下次训练增加2组鸟狗式强化核心' }
      ]
    }
    loading.value = false
  }, 500)
})

function getScoreColor(score: number) {
  if (score >= 90) return '#10b981'
  if (score >= 75) return '#3b82f6'
  if (score >= 60) return '#f59e0b'
  return '#ef4444'
}

function getFeedbackType(type: string) {
  switch (type) {
    case 'good': return 'success'
    case 'warning': return 'warning'
    case 'error': return 'error'
    default: return 'info'
  }
}
</script>

<script lang="ts">
export default { name: 'PrescriptionTrainingReportView' }
</script>

<template>
  <div class="report-page">
    <n-spin v-if="loading" style="display: flex; justify-content: center; padding: 60px;">
      <template #description>加载中...</template>
    </n-spin>

    <template v-else-if="report">
      <n-card :bordered="false" class="header-card" size="large">
        <div class="report-header">
          <div class="header-icon">
            <n-icon size="32" :component="TrophyOutline" />
          </div>
          <div class="header-info">
            <h2 class="report-title">AI训练方案报告</h2>
            <p class="report-subtitle">第 {{ report.phase }} 阶段训练方案</p>
          </div>
          <div class="score-section">
            <div class="score-circle" :style="{ borderColor: getScoreColor(report.total_score) }">
              <span class="score-value" :style="{ color: getScoreColor(report.total_score) }">
                {{ report.total_score?.toFixed(1) }}
              </span>
              <span class="score-max">/100</span>
            </div>
            <n-tag type="success" round size="large">
              <n-icon size="14" :component="CheckmarkCircleOutline" style="margin-right: 4px;" />
              已完成
            </n-tag>
          </div>
        </div>
      </n-card>

      <n-card :bordered="false" class="section-card" size="large">
        <template #header>
          <span class="section-title">训练概况</span>
        </template>
        <n-descriptions :column="2" bordered size="medium">
          <n-descriptions-item label="训练时长">
            {{ Math.round((new Date(report.end_time).getTime() - new Date(report.start_time).getTime()) / 60000) }} 分钟
          </n-descriptions-item>
          <n-descriptions-item label="完成动作">
            {{ report.items.length }} 个
          </n-descriptions-item>
          <n-descriptions-item label="综合评分">
            <span class="highlight-score" :style="{ color: getScoreColor(report.total_score) }">
              {{ report.total_score?.toFixed(1) }} 分
            </span>
          </n-descriptions-item>
          <n-descriptions-item label="训练状态">
            <n-tag type="success" size="small" round>已完成</n-tag>
          </n-descriptions-item>
        </n-descriptions>
      </n-card>

      <n-card :bordered="false" class="section-card" size="large">
        <template #header>
          <div class="header-with-icon">
            <n-icon size="18" :component="BarbellOutline" style="color: #8b5cf6;" />
            <span class="section-title">动作详情</span>
          </div>
        </template>
        <n-list>
          <n-list-item v-for="(item, idx) in report.items" :key="idx">
            <div class="action-item">
              <div class="action-left">
                <div class="action-index">{{ idx + 1 }}</div>
                <div class="action-info">
                  <div class="action-name">{{ item.name }}</div>
                  <div class="action-meta">{{ item.sets }}组 × {{ item.reps }}次</div>
                </div>
              </div>
              <div class="action-score" :style="{ color: getScoreColor(item.score) }">
                {{ item.score }} 分
              </div>
            </div>
          </n-list-item>
        </n-list>
      </n-card>

      <n-card :bordered="false" class="section-card" size="large">
        <template #header>
          <span class="section-title">训练反馈</span>
        </template>
        <div class="feedback-list">
          <div
            v-for="(fb, i) in report.feedback"
            :key="i"
            class="feedback-item"
            :class="`feedback-${fb.type}`"
          >
            <n-tag :type="getFeedbackType(fb.type)" round size="small" class="feedback-tag">
              {{ fb.type === 'good' ? '👍 做得好' : fb.type === 'warning' ? '⚠️ 需改进' : '💡 建议' }}
            </n-tag>
            <span class="feedback-text">{{ fb.text }}</span>
          </div>
        </div>
      </n-card>

      <div class="action-footer">
        <n-space justify="center">
          <n-button type="primary" size="large" @click="router.push('/prescription-training')">
            继续训练
          </n-button>
          <n-button size="large" @click="router.push('/prescription-training')">
            <template #icon><n-icon :component="ArrowBackOutline" /></template>
            返回
          </n-button>
        </n-space>
      </div>
    </template>
  </div>
</template>

<style scoped>
.report-page {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.header-card {
  background: linear-gradient(135deg, #faf5ff 0%, #eff6ff 100%) !important;
  border-radius: 16px !important;
}

.report-header {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.header-info {
  flex: 1;
}

.report-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 4px 0;
}

.report-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.score-section {
  text-align: center;
  flex-shrink: 0;
}

.score-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 4px solid;
  display: flex;
  align-items: baseline;
  justify-content: center;
  margin-bottom: 8px;
  background: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.score-value {
  font-size: 36px;
  font-weight: 700;
}

.score-max {
  font-size: 14px;
  color: #94a3b8;
  margin-left: 2px;
}

.section-card {
  border-radius: 12px !important;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
}

.header-with-icon {
  display: flex;
  align-items: center;
  gap: 8px;
}

.highlight-score {
  font-weight: 700;
  font-size: 16px;
}

.action-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.action-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.action-index {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #f1f5f9;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.action-name {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 2px;
}

.action-meta {
  font-size: 12px;
  color: #64748b;
}

.action-score {
  font-size: 18px;
  font-weight: 700;
}

.feedback-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.feedback-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #f8fafc;
}

:deep(.dark) .feedback-item {
  background: rgba(255, 255, 255, 0.04);
}

.feedback-tag {
  flex-shrink: 0;
}

.feedback-text {
  font-size: 14px;
}

.action-footer {
  padding: 16px 0 8px;
}

@media (max-width: 768px) {
  .report-header {
    flex-direction: column;
    text-align: center;
  }

  .score-circle {
    width: 80px;
    height: 80px;
  }

  .score-value {
    font-size: 28px;
  }
}
</style>
