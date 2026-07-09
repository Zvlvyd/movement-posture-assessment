<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { TrophyOutline, ShieldCheckmarkOutline, TimeOutline, VideocamOutline, StarOutline } from '@vicons/ionicons5'
import type { ReportMetric } from '../../mock/standardTrainingReportMock'

defineProps<{ metrics: ReportMetric[] }>()

const ICON_MAP: Record<string, any> = {
  TrophyOutline, ShieldCheckmarkOutline, TimeOutline, VideocamOutline, StarOutline,
  RepeatOutline: TrophyOutline, ChatbubbleOutline: ShieldCheckmarkOutline,
}
function getIcon(name: string) { return ICON_MAP[name] || TrophyOutline }
</script>

<template>
  <div class="metrics">
    <!-- 核心指标：2 张卡片 -->
    <div class="core">
      <div v-for="(m, i) in metrics.slice(0, 2)" :key="m.name" class="core-card">
        <div class="core-head">
          <span class="core-icon"><n-icon size="18" :component="getIcon(m.icon)" /></span>
          <span class="core-label">{{ m.name }}</span>
        </div>
        <div class="core-body">
          <span class="core-val">{{ m.value }}</span>
          <span v-if="m.unit" class="core-unit">{{ m.unit }}</span>
        </div>
        <div class="core-bar">
          <div class="core-bar-in" :style="{ width: typeof m.value === 'number' ? Math.min(m.value as number, 100) + '%' : '100%' }"></div>
        </div>
      </div>
    </div>

    <!-- 辅助指标：单行轻量 -->
    <div class="aux">
      <div v-for="m in metrics.slice(2)" :key="m.name" class="aux-item">
        <n-icon size="13" :component="getIcon(m.icon)" />
        <span class="aux-label">{{ m.name }}</span>
        <span class="aux-val">{{ m.value }}</span>
        <span v-if="m.unit" class="aux-unit">{{ m.unit }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.metrics {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ── 核心指标 ── */
.core {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.core-card {
  background: #fff;
  border-radius: 14px;
  padding: 16px 20px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.025);
}

.core-head {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 8px;
}

.core-icon { color: #94a3b8; }

.core-label {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
}

.core-body {
  display: flex;
  align-items: baseline;
  gap: 5px;
  margin-bottom: 8px;
}

.core-val {
  font-size: 34px;
  font-weight: 800;
  color: #1e293b;
  line-height: 1;
  letter-spacing: -1px;
}

.core-unit {
  font-size: 13px;
  color: #94a3b8;
}

.core-bar {
  height: 3px;
  border-radius: 2px;
  background: #f1f5f9;
  overflow: hidden;
}

.core-bar-in {
  height: 100%;
  border-radius: 2px;
  background: #6366f1;
  transition: width 1s ease;
}

/* ── 辅助指标行 ── */
.aux {
  display: flex;
  gap: 24px;
  padding: 2px 4px;
}

.aux-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #b0b0c0;
}

.aux-label {
  color: #b0b0c0;
}

.aux-val {
  color: #64748b;
  font-weight: 600;
}

.aux-unit {
  color: #b0b0c0;
}

@media (max-width: 768px) {
  .core {
    grid-template-columns: 1fr;
  }
  .aux {
    flex-wrap: wrap;
    gap: 14px;
  }
}
</style>
