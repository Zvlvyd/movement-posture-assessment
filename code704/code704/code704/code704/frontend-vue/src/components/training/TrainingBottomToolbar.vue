<script setup lang="ts">
import { NButton, NIcon, NProgress } from 'naive-ui'
import { PlayCircleOutline, TimeOutline, CheckmarkCircleOutline } from '@vicons/ionicons5'

defineProps<{
  doneCount: number
  totalExercises: number
  progressPercent: number
  remainingMinutes: number
  hasRecommendedItem: boolean
  allCompleted: boolean
}>()

const emit = defineEmits<{
  (e: 'continueTraining'): void
}>()
</script>

<template>
  <div class="bottom-toolbar">
    <div class="toolbar-inner">
      <!-- Progress info -->
      <div class="toolbar-progress">
        <div class="toolbar-progress-bar">
          <n-progress
            type="line"
            :percentage="progressPercent"
            :height="6"
            :border-radius="3"
            color="#7B6CFF"
            rail-color="rgba(108,99,255,0.08)"
            :show-indicator="false"
          />
        </div>
        <span class="toolbar-progress-text">
          {{ doneCount }}/{{ totalExercises }} 个动作已完成
        </span>
      </div>

      <!-- Remaining time -->
      <div class="toolbar-time">
        <n-icon size="16" :component="TimeOutline" color="#64748b" />
        <span>预计剩余 <strong>{{ remainingMinutes }}</strong> 分钟</span>
      </div>

      <!-- CTA button -->
      <div class="toolbar-cta">
        <n-button
          v-if="allCompleted"
          size="medium"
          type="success"
          round
          disabled
        >
          <template #icon><n-icon :component="CheckmarkCircleOutline" /></template>
          训练完成
        </n-button>
        <n-button
          v-else
          size="medium"
          type="primary"
          round
          class="cta-btn"
          @click="emit('continueTraining')"
        >
          <template #icon><n-icon :component="PlayCircleOutline" /></template>
          {{ hasRecommendedItem ? '继续训练' : '开始训练' }}
        </n-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bottom-toolbar {
  position: sticky;
  bottom: 0;
  z-index: 50;
  margin: 0 -32px;
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(16px);
  border-top: 1px solid rgba(108,99,255,0.08);
  box-shadow: 0 -4px 20px rgba(108,99,255,0.06);
}
.toolbar-inner {
  max-width: 860px;
  margin: 0 auto;
  padding: 14px 32px;
  display: flex;
  align-items: center;
  gap: 20px;
}

/* ── Progress ── */
.toolbar-progress {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}
.toolbar-progress-bar {
  width: 160px;
  flex-shrink: 0;
}
.toolbar-progress-text {
  font-size: 13px;
  color: #64748b;
  white-space: nowrap;
}

/* ── Time ── */
.toolbar-time {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #64748b;
  white-space: nowrap;
  flex-shrink: 0;
}
.toolbar-time strong {
  color: #1e293b;
}

/* ── CTA ── */
.toolbar-cta {
  flex-shrink: 0;
}
.cta-btn {
  background: linear-gradient(135deg, #7B6CFF, #5C8CFF) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(123,108,255,0.35);
  padding: 0 28px !important;
}
.cta-btn:hover {
  box-shadow: 0 6px 24px rgba(123,108,255,0.5);
  transform: translateY(-1px);
}

@media (max-width: 768px) {
  .toolbar-inner {
    flex-wrap: wrap;
    gap: 12px;
    padding: 12px 16px;
  }
  .toolbar-progress-bar {
    width: 100px;
  }
  .toolbar-time {
    font-size: 12px;
  }
}
</style>
