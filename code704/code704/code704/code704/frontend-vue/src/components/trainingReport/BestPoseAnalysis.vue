<script setup lang="ts">
import { NCard, NProgress, NTag, NIcon, NCollapse, NCollapseItem } from 'naive-ui'
import {
  CheckmarkCircleOutline, WarningOutline, FitnessOutline, ChevronDownOutline
} from '@vicons/ionicons5'
import type { BestPoseMetrics } from '../../mock/standardTrainingReportMock'
import { getStatusColor } from '../../mock/standardTrainingReportMock'

defineProps<{
  data: BestPoseMetrics
}>()

function statusIcon(status: string): any {
  return status === 'good' ? CheckmarkCircleOutline : WarningOutline
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    good: '优秀',
    close: '接近',
    warning: '注意',
    bad: '偏差'
  }
  return map[status] || '未知'
}
</script>

<script lang="ts">
export default { name: 'BestPoseAnalysis' }
</script>

<template>
  <n-card :bordered="false" class="best-pose-card" size="large">
    <template #header>
      <div class="section-header">
        <n-icon size="20" :component="FitnessOutline" class="section-icon" />
        <span class="section-title">最佳动作分析</span>
      </div>
    </template>

    <!-- 帧来源提示 -->
    <div v-if="data.frameTip" class="frame-source-tip">
      <n-icon size="12" :component="CheckmarkCircleOutline" />
      {{ data.frameTip }}
    </div>

    <div class="pose-metrics">
        <div class="metric-progress-list">
          <div class="metric-progress-item">
            <div class="metric-progress-label">
              <span>动作质量</span>
              <span class="metric-progress-value" :style="{ color: '#8b5cf6' }">{{ data.quality }}%</span>
            </div>
            <n-progress
              type="line"
              :percentage="data.quality"
              :color="'#8b5cf6'"
              :height="8"
              :show-indicator="false"
              :border-radius="4"
            />
          </div>

          <div class="metric-progress-item">
            <div class="metric-progress-label">
              <span>稳定性</span>
              <span class="metric-progress-value" :style="{ color: '#3b82f6' }">{{ data.stability }}%</span>
            </div>
            <n-progress
              type="line"
              :percentage="data.stability"
              :color="'#3b82f6'"
              :height="8"
              :show-indicator="false"
              :border-radius="4"
            />
          </div>

          <div class="metric-progress-item">
            <div class="metric-progress-label">
              <span>标准度</span>
              <span class="metric-progress-value" :style="{ color: '#10b981' }">{{ data.standard }}%</span>
            </div>
            <n-progress
              type="line"
              :percentage="data.standard"
              :color="'#10b981'"
              :height="8"
              :show-indicator="false"
              :border-radius="4"
            />
          </div>
        </div>

        <div class="key-angles">
          <div class="key-angles-label">关键关节角度</div>
          <div class="key-angles-list">
            <n-tag
              v-for="angle in data.keyAngles"
              :key="angle.joint"
              round
              size="small"
              :bordered="false"
              :style="{
                background: `${getStatusColor(angle.status)}15`,
                color: getStatusColor(angle.status)
              }"
            >
              <template #icon>
                <n-icon size="12" :component="statusIcon(angle.status)" />
              </template>
              {{ angle.joint }} {{ angle.value }}°
            </n-tag>
          </div>
        </div>

        <n-collapse class="detail-collapse" display-directive="show">
          <n-collapse-item name="detailed-angles">
            <template #header>
              <span class="collapse-title">查看详细关节角度</span>
            </template>
            <template #header-extra>
              <n-icon size="16" :component="ChevronDownOutline" class="collapse-arrow" />
            </template>
            <div class="detailed-angles-list">
              <div
                v-for="angle in data.detailedAngles"
                :key="angle.joint"
                class="detailed-angle-item"
              >
                <div class="detailed-angle-main">
                  <n-icon
                    size="14"
                    :component="statusIcon(angle.status)"
                    :style="{ color: getStatusColor(angle.status) }"
                  />
                  <span class="detailed-angle-name">{{ angle.joint }}</span>
                  <span class="detailed-angle-status" :style="{ color: getStatusColor(angle.status) }">
                    {{ statusLabel(angle.status) }}
                  </span>
                </div>
                <div class="detailed-angle-values">
                  <span>你的 {{ angle.user }}°</span>
                  <span class="angle-separator">/</span>
                  <span class="angle-standard">标准 {{ angle.standard }}°</span>
                  <span class="angle-diff" :style="{ color: getStatusColor(angle.status) }">
                    {{ angle.diff > 0 ? '+' : '' }}{{ angle.diff }}°
                  </span>
                </div>
              </div>
            </div>
          </n-collapse-item>
        </n-collapse>
    </div>
  </n-card>
</template>

<style scoped lang="scss">
.best-pose-card {
  border-radius: 20px !important;
  background: white !important;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04) !important;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-icon {
  color: #8b5cf6;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}

.frame-source-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  margin-bottom: 16px;
  border-radius: 10px;
  background: #f5f3ff;
  font-size: 12px;
  color: #7c3aed;
}

.pose-metrics {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.metric-progress-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.metric-progress-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-progress-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: #475569;
  font-weight: 500;
}

.metric-progress-value {
  font-weight: 700;
  font-size: 16px;
}

.key-angles-label {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 10px;
}

.key-angles-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-collapse {
  border-radius: 12px;
  background: #f8fafc;
  overflow: hidden;
}

.collapse-title {
  font-size: 14px;
  color: #475569;
  font-weight: 500;
}

.collapse-arrow {
  color: #94a3b8;
  transition: transform 0.25s ease;
}

:deep(.n-collapse-item__header) {
  padding: 14px 16px !important;
}

:deep(.n-collapse-item__content-inner) {
  padding: 0 16px 16px !important;
}

.detailed-angles-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detailed-angle-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 10px;
  background: white;
}

.detailed-angle-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detailed-angle-name {
  font-size: 14px;
  color: #334155;
  font-weight: 500;
}

.detailed-angle-status {
  font-size: 12px;
  font-weight: 600;
}

.detailed-angle-values {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #475569;
}

.angle-separator {
  color: #cbd5e1;
}

.angle-standard {
  color: #94a3b8;
}

.angle-diff {
  font-weight: 600;
  min-width: 42px;
  text-align: right;
}

@media (max-width: 640px) {
  .detailed-angle-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .detailed-angle-values {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
