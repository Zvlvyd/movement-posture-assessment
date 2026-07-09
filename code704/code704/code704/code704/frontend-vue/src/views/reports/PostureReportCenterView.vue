<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { assessmentApi } from '../../services/api'
import type { AssessmentRecord } from '../../types'
import { NCard, NButton, NSpace, NTag, NSpin, NEmpty, NStatistic, NIcon } from 'naive-ui'
import { ArrowBackOutline, BodyOutline, DocumentTextOutline, ChevronForwardOutline, TimeOutline } from '@vicons/ionicons5'

const router = useRouter()
const loading = ref(true)
const records = ref<AssessmentRecord[]>([])

const latest = computed(() => records.value[0] || null)

function riskTagType(level: string) {
  if (level === 'low') return 'success' as const
  if (level === 'medium') return 'warning' as const
  return 'error' as const
}
function riskLabel(level: string) {
  if (level === 'low') return '低风险'
  if (level === 'medium') return '中风险'
  return '高风险'
}

function postureStatus(score: number) {
  if (score >= 85) return '整体姿态优秀'
  if (score >= 70) return '姿态状态良好'
  if (score >= 60) return '轻度姿态问题'
  return '建议进一步评估'
}

function viewDetail(id: number) {
  router.push(`/assessment/report/${id}`)
}

onMounted(async () => {
  try {
    records.value = await assessmentApi.getRecords()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="report-center">
    <n-button text size="small" @click="router.push('/profile')">
      <template #icon><n-icon :component="ArrowBackOutline" /></template>
      返回个人中心
    </n-button>

    <n-card class="report-hero" :bordered="false">
      <div class="report-hero-content">
        <div class="report-icon" style="background: rgba(16,185,129,0.12); color: #10b981;">
          <n-icon size="32" :component="BodyOutline" />
        </div>
        <div>
          <h1 class="report-title">体态评估报告</h1>
          <p class="report-desc">AI 智能体态分析，识别圆肩、驼背、骨盆前倾等问题</p>
        </div>
      </div>
    </n-card>

    <n-spin v-if="loading" size="large" class="loading" />

    <template v-else-if="records.length">
      <!-- Latest Report Summary -->
      <n-card class="report-card latest-card" :bordered="false">
        <div class="latest-header">
          <div>
            <span class="section-kicker">LATEST REPORT</span>
            <h2>最新体态评估</h2>
          </div>
          <n-button type="primary" class="view-detail-btn" @click="viewDetail(latest!.id)">
            查看详情
            <template #icon><n-icon :component="DocumentTextOutline" /></template>
          </n-button>
        </div>
        <n-space align="center" size="large" class="latest-stats">
          <n-statistic label="体态评分" :value="Math.round(latest!.overall_score)">
            <template #suffix>分</template>
          </n-statistic>
          <n-statistic label="测试日期" :value="new Date(latest!.test_date).toLocaleDateString('zh-CN')" />
          <n-tag :type="riskTagType(latest!.risk_level)" round size="large" :bordered="false">
            {{ riskLabel(latest!.risk_level) }}
          </n-tag>
        </n-space>
        <div class="status-line">{{ postureStatus(latest!.overall_score) }}</div>
      </n-card>

      <!-- History List -->
      <n-card title="历史评估记录" class="report-card">
        <div class="history-list">
          <div
            v-for="r in records"
            :key="r.id"
            class="history-item"
            @click="viewDetail(r.id)"
          >
            <div class="history-main">
              <div class="history-date">
                <n-icon size="14" :component="TimeOutline" />
                <span>{{ new Date(r.test_date).toLocaleDateString('zh-CN') }}</span>
              </div>
              <span class="history-score">{{ Math.round(r.overall_score) }} 分</span>
            </div>
            <div class="history-side">
              <n-tag :type="riskTagType(r.risk_level)" round size="small" :bordered="false">
                {{ riskLabel(r.risk_level) }}
              </n-tag>
              <n-icon size="18" :component="ChevronForwardOutline" class="history-arrow" />
            </div>
          </div>
        </div>
      </n-card>
    </template>

    <n-empty v-else description="暂无体态评估记录" class="empty">
      <template #extra>
        <n-button type="primary" @click="router.push('/assessment')">前往体态评估</n-button>
      </template>
    </n-empty>
  </div>
</template>

<style scoped>
.report-center {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.report-hero {
  background: linear-gradient(135deg, #10b981, #059669);
  border-radius: 20px;
  color: #fff;
}
.report-hero-content {
  display: flex;
  align-items: center;
  gap: 18px;
}
.report-icon {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.report-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #fff;
}
.report-desc {
  margin: 6px 0 0;
  font-size: 14px;
  color: rgba(255,255,255,0.8);
}
.report-card {
  border-radius: 16px;
  background: rgba(255,255,255,0.95);
  box-shadow: 0 8px 30px rgba(16,185,129,0.08);
}
.latest-card {
  background: linear-gradient(135deg, #ecfdf5, #ffffff);
}
.latest-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 18px;
}
.latest-header h2 {
  margin: 4px 0 0;
  font-size: 20px;
  color: #1e293b;
}
.section-kicker {
  color: #10b981;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.2px;
}
.view-detail-btn {
  background: linear-gradient(135deg, #10b981, #059669) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 12px !important;
  font-weight: 600 !important;
}
.latest-stats {
  padding: 8px 0;
}
.status-line {
  margin-top: 16px;
  padding: 12px 16px;
  border-radius: 12px;
  background: rgba(16,185,129,0.08);
  color: #047857;
  font-size: 14px;
  font-weight: 600;
}
.loading { display: flex; justify-content: center; padding: 60px 0; }
.empty { padding: 60px 0; }
.history-list { display: flex; flex-direction: column; gap: 10px; }
.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-radius: 14px;
  background: rgba(16,185,129,0.04);
  cursor: pointer;
  transition: all 0.2s ease;
}
.history-item:hover {
  background: rgba(16,185,129,0.08);
  transform: translateX(4px);
}
.history-main {
  display: flex;
  align-items: center;
  gap: 20px;
}
.history-date {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #64748b;
  font-size: 13px;
  width: 120px;
}
.history-score {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
}
.history-side {
  display: flex;
  align-items: center;
  gap: 12px;
}
.history-arrow {
  color: #94a3b8;
  transition: transform 0.2s ease;
}
.history-item:hover .history-arrow {
  transform: translateX(4px);
  color: #10b981;
}

@media (max-width: 768px) {
  .report-center { padding: 16px; }
  .latest-header { flex-direction: column; gap: 12px; }
  .history-main { flex-direction: column; align-items: flex-start; gap: 8px; }
  .history-item { align-items: flex-start; flex-direction: column; gap: 12px; }
}
</style>
