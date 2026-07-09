<script setup lang="ts">
import { computed } from 'vue'
import { NIcon } from 'naive-ui'
import type { PlanItemV2 } from '../../types'
import TrainingExerciseCard from './TrainingExerciseCard.vue'

const props = defineProps<{
  phase: string
  phaseLabel: string
  phaseDescription: string
  phaseColor: string
  phaseIcon: any
  items: PlanItemV2[]
  completedExercises: Set<number>
  itemProgress: Map<number, { sets_done: number; total_sets: number; latest_reps: number; latest_score: number }>
  recommendedItemId: number | null
}>()

const emit = defineEmits<{
  (e: 'startExercise', item: PlanItemV2): void
}>()

const doneCount = computed(() => props.items.filter(i => props.completedExercises.has(i.id)).length)
</script>

<template>
  <div class="phase-section" v-if="items.length > 0">
    <!-- Phase header -->
    <div class="phase-header" :style="{ '--phase-color': phaseColor }">
      <div class="phase-icon">
        <n-icon :component="phaseIcon" size="20" :color="phaseColor" />
      </div>
      <div class="phase-info">
        <div class="phase-label">{{ phaseLabel }}</div>
        <div class="phase-desc">{{ phaseDescription }} · {{ items.length }} 个动作 · 已完成 {{ doneCount }}</div>
      </div>
    </div>

    <!-- Exercise cards -->
    <div class="phase-items">
      <TrainingExerciseCard
        v-for="(item, idx) in items"
        :key="item.id"
        :item="item"
        :index="idx"
        :is-completed="completedExercises.has(item.id)"
        :is-recommended="item.id === recommendedItemId"
        :sets-done="itemProgress.get(item.id)?.sets_done ?? 0"
        :total-sets="itemProgress.get(item.id)?.total_sets ?? item.sets"
        :latest-reps="itemProgress.get(item.id)?.latest_reps ?? 0"
        :latest-score="itemProgress.get(item.id)?.latest_score ?? null"
        :is-first="idx === 0"
        :is-last="idx === items.length - 1"
        @start="(item) => emit('startExercise', item)"
      />
    </div>
  </div>
</template>

<style scoped>
.phase-section {
  margin-bottom: 20px;
}

/* ── Phase header ── */
.phase-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0 12px 14px;
  border-left: 4px solid var(--phase-color);
  margin-bottom: 12px;
}
.phase-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--phase-color) 12%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.phase-label {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}
.phase-desc {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 2px;
}
</style>
