<script setup lang="ts">
defineProps<{ label: string; value: number; max?: number }>()
</script>

<template>
  <div class="score-bar">
    <span class="score-bar-label">{{ label }}</span>
    <div class="score-bar-track">
      <div
        class="score-bar-fill"
        :class="{
          'score-high': value >= 85,
          'score-mid': value >= 60 && value < 85,
          'score-low': value < 60,
        }"
        :style="{ width: Math.min(100, Math.max(0, (value / (max || 100)) * 100)) + '%' }"
      />
    </div>
    <span class="score-bar-value">{{ value != null ? Math.round(value) : '-' }}</span>
  </div>
</template>

<style scoped>
.score-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.score-bar-label {
  width: 32px;
  font-size: 12px;
  color: #64748b;
  flex-shrink: 0;
}
.score-bar-track {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: #f1f5f9;
  overflow: hidden;
}
.score-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}
.score-high { background: #10b981; }
.score-mid { background: #f59e0b; }
.score-low { background: #ef4444; }
.score-bar-value {
  width: 28px;
  font-size: 12px;
  font-weight: 600;
  text-align: right;
  color: #334155;
  flex-shrink: 0;
}
</style>
