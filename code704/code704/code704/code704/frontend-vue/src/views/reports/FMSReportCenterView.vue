<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fmsApi } from '../../services/api'
import type { FMSRecord } from '../../types'
import { NCard, NButton, NSpace, NTag, NSpin, NEmpty, NStatistic, NIcon } from 'naive-ui'
import { ArrowBackOutline, AnalyticsOutline, DocumentTextOutline, ChevronForwardOutline, TimeOutline } from '@vicons/ionicons5'

const router = useRouter()
const loading = ref(true)
const records = ref<FMSRecord[]>([])

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

function viewDetail(id: number) {
  router.push(`/fms/report/${id}`)
}

onMounted(async () => {
  try {
    records.value = await fmsApi.getRecords()
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
        <div class="report-icon" style="background: rgba(139,92,246,0.12); color: #8b5cf6;">
          <n-icon size="32" :component="AnalyticsOutline" />
        </div>
        <div>
          <h1 class="report-title">FMS 功能性动作筛查报告</h1>
          <p class="report-desc">基于功能性动作模式评估运动损伤风险</p>
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
            <h2>最新筛查结果</h2>
          </div>
          <n-button type="primary" class="view-detail-btn" @click="viewDetail(latest!.id)">
            查看详情
            <template #icon><n-icon :component="DocumentTextOutline" /></template>
          </n-button>
        </div>
        <n-space align="center" size="large" class="latest-stats">
          <n-statistic label="综合评分" :value="Math.round(latest!.overall_score)">
            <template #suffix>分</template>
          </n-statistic>
          <n-statistic label="测试日期" :value="new Date(latest!.test_date).toLocaleDateString('zh-CN')" />
          <n-tag :type="riskTagType(latest!.risk_level)" round size="large" :bordered="false">
            {{ riskLabel(latest!.risk_level) }}
          </n-tag>
        </n-space>
      </n-card>

      <!-- History List -->
      <n-card title="历史筛查记录" class="report-card">
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

    <n-empty v-else description="暂无 FMS 筛查记录" class="empty">
      <template #extra>
        <n-button type="primary" @click="router.push('/fms')">前往 FMS 筛查</n-button>
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
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
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
  box-shadow: 0 8px 30px rgba(139,92,246,0.08);
}
.latest-card {
  background: linear-gradient(135deg, #f5f3ff, #ffffff);
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
  color: #8b5cf6;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.2px;
}
.view-detail-btn {
  background: linear-gradient(135deg, #8b5cf6, #7c3aed) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 12px !important;
  font-weight: 600 !important;
}
.latest-stats {
  padding: 8px 0;
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
  background: rgba(139,92,246,0.04);
  cursor: pointer;
  transition: all 0.2s ease;
}
.history-item:hover {
  background: rgba(139,92,246,0.08);
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
  color: #8b5cf6;
}

@media (max-width: 768px) {
  .report-center { padding: 16px; }
  .latest-header { flex-direction: column; gap: 12px; }
  .history-main { flex-direction: column; align-items: flex-start; gap: 8px; }
  .history-item { align-items: flex-start; flex-direction: column; gap: 12px; }
}
</style>
