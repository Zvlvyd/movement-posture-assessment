<script setup lang="ts">
import { computed } from 'vue'
import { NButton, NTag, NIcon } from 'naive-ui'
import { CheckmarkCircleOutline, PlayCircleOutline, TimeOutline, FitnessOutline } from '@vicons/ionicons5'
import type { PlanItemV2 } from '../../types'

const props = defineProps<{
  item: PlanItemV2
  index: number
  isCompleted: boolean
  isRecommended: boolean
  setsDone: number
  totalSets: number
  latestReps: number
  latestScore: number | null
  isFirst: boolean
  isLast: boolean
}>()

const emit = defineEmits<{
  (e: 'start', item: PlanItemV2): void
}>()

const DIFFICULTY_LABELS: Record<number, string> = { 1: '入门', 2: '初级', 3: '中级', 4: '进阶', 5: '高级' }
const DIFFICULTY_COLORS: Record<number, string> = { 1: '#10b981', 2: '#10b981', 3: '#f59e0b', 4: '#f97316', 5: '#ef4444' }

const durSec = props.item.sets * (props.item.duration_seconds || props.item.duration || 0)
const durMin = Math.floor(durSec / 60)
const durRemSec = durSec % 60
const durText = durMin > 0
  ? `${durMin}分${durRemSec > 0 ? durRemSec + '秒' : ''}`
  : `${durRemSec}秒`

function btnLabel() {
  if (props.isCompleted) return '再次训练'
  if (props.setsDone > 0) return '继续训练'
  return '开始训练'
}

const doneSets = computed(() => Number(props.setsDone) || 0)
const curReps = computed(() => Number(props.latestReps) || 0)
const ttlSets = computed(() => Number(props.totalSets) || Number(props.item.sets) || 1)
const repsPer = computed(() => Number(props.item.reps) || 10)
</script>

<template>
  <div
    class="exercise-card"
    :class="{
      'is-completed': isCompleted,
      'is-recommended': isRecommended,
      'is-in-progress': setsDone > 0 && !isCompleted,
    }"
  >
    <!-- Stepper connector lines -->
    <div class="stepper-connector" :class="{ 'top-hidden': isFirst, 'bottom-hidden': isLast }">
      <div class="stepper-line"></div>
    </div>

    <!-- Step node -->
    <div class="step-node" :class="{ done: isCompleted, current: isRecommended }">
      <n-icon v-if="isCompleted" size="16" :component="CheckmarkCircleOutline" />
      <span v-else class="step-num">{{ index + 1 }}</span>
    </div>

    <!-- Card body -->
    <div class="card-body">
      <div class="card-main">
        <!-- Thumbnail placeholder -->
        <div class="exercise-thumb">
          <n-icon size="24" :component="FitnessOutline" />
        </div>

        <!-- Info -->
        <div class="exercise-info">
          <div class="exercise-name">{{ item.action_name }}</div>
          <div class="exercise-meta">
            <span class="meta-tag">
              <n-icon size="12" :component="FitnessOutline" />
              {{ item.sets }}组 × {{ item.reps }}次
            </span>
            <span class="meta-tag">
              <n-icon size="12" :component="TimeOutline" />
              {{ durText }}
            </span>
            <span
              class="meta-tag difficulty-tag"
              :style="{ color: DIFFICULTY_COLORS[item.difficulty] || '#64748b' }"
            >
              {{ DIFFICULTY_LABELS[item.difficulty] || '未知' }}
            </span>
            <n-tag v-if="item.alternative" size="tiny" type="warning" :bordered="false">
              替代动作
            </n-tag>
          </div>
          <div v-if="item.notes" class="exercise-notes">{{ item.notes }}</div>
        </div>
      </div>

      <!-- Progress & status -->
      <div v-if="(doneSets > 0 || curReps > 0) && !isCompleted" class="exercise-progress">
        <span class="progress-text">已完成 {{ doneSets }}/{{ ttlSets }} 组 · 当前组 {{ curReps }}/{{ repsPer }} 次</span>
        <span v-if="latestScore !== null && latestScore > 0" class="progress-score">{{ latestScore }} 分</span>
      </div>
    </div>

    <!-- Action button -->
    <div class="card-action">
      <n-button
        v-if="isCompleted"
        size="small"
        type="success"
        ghost
        round
        @click="emit('start', item)"
      >
        <template #icon><n-icon :component="PlayCircleOutline" /></template>
        再次训练
      </n-button>
      <n-button
        v-else-if="isRecommended"
        size="small"
        type="primary"
        round
        class="btn-glow"
        @click="emit('start', item)"
      >
        <template #icon><n-icon :component="PlayCircleOutline" /></template>
        继续训练
      </n-button>
      <n-button
        v-else
        size="small"
        round
        @click="emit('start', item)"
      >
        <template #icon><n-icon :component="PlayCircleOutline" /></template>
        开始训练
      </n-button>
    </div>
  </div>
</template>

<style scoped>
.exercise-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  margin-bottom: 6px;
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(108, 99, 255, 0.06);
  box-shadow: 0 2px 12px rgba(108, 99, 255, 0.05);
  transition: all 0.3s ease;
}

.exercise-card:hover {
  box-shadow: 0 4px 20px rgba(108, 99, 255, 0.1);
}

.exercise-card.is-recommended {
  border-color: rgba(108, 99, 255, 0.25);
  box-shadow: 0 0 24px rgba(123, 108, 255, 0.18), 0 4px 16px rgba(108, 99, 255, 0.1);
  background: linear-gradient(135deg, #fff 60%, rgba(123, 108, 255, 0.03));
}

.exercise-card.is-completed {
  border-color: rgba(16, 185, 129, 0.15);
  background: rgba(16, 185, 129, 0.02);
}

/* ── Stepper connector ── */
.stepper-connector {
  position: absolute;
  left: 13px;
  top: 0;
  bottom: 0;
  width: 2px;
  pointer-events: none;
}
.stepper-line {
  width: 100%;
  height: 100%;
  background: linear-gradient(180deg, rgba(108, 99, 255, 0.15), rgba(108, 99, 255, 0.15));
}
.stepper-connector.top-hidden .stepper-line {
  mask-image: linear-gradient(180deg, transparent 0%, #000 40%);
}
.stepper-connector.bottom-hidden .stepper-line {
  mask-image: linear-gradient(180deg, #000 60%, transparent 100%);
}

/* ── Step node ── */
.step-node {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid rgba(108, 99, 255, 0.25);
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  z-index: 2;
  transition: all 0.3s ease;
}
.step-node .step-num {
  font-size: 12px;
  font-weight: 700;
  color: #94a3b8;
}
.step-node.current {
  border-color: #7B6CFF;
  box-shadow: 0 0 0 3px rgba(123, 108, 255, 0.12);
}
.step-node.current .step-num {
  color: #7B6CFF;
}
.step-node.done {
  background: linear-gradient(135deg, #10b981, #34d399);
  border-color: #10b981;
  color: #fff;
}

/* ── Card body ── */
.card-body {
  flex: 1;
  min-width: 0;
}
.card-main {
  display: flex;
  align-items: center;
  gap: 14px;
}

/* ── Thumbnail ── */
.exercise-thumb {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(123, 108, 255, 0.08), rgba(79, 140, 255, 0.08));
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(123, 108, 255, 0.4);
  flex-shrink: 0;
}

/* ── Info ── */
.exercise-info {
  min-width: 0;
}
.exercise-name {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.exercise-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.meta-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #64748b;
  background: #f8fafc;
  padding: 2px 8px;
  border-radius: 6px;
}
.difficulty-tag {
  font-weight: 600;
}
.exercise-notes {
  margin-top: 6px;
  font-size: 12px;
  color: #94a3b8;
  font-style: italic;
}

/* ── Progress ── */
.exercise-progress {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.set-badges {
  display: flex;
  gap: 6px;
}
.set-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 22px;
  border-radius: 11px;
  font-size: 11px;
  font-weight: 600;
  background: #f1f5f9;
  color: #94a3b8;
  border: 2px solid transparent;
  transition: all 0.2s;
}
.set-badge.done {
  background: #dcfce7;
  color: #16a34a;
}
.set-badge.current {
  background: #fef3c7;
  color: #d97706;
  border-color: #3b82f6;
}
.progress-text {
  font-size: 12px;
  color: #64748b;
}
.progress-score {
  font-size: 12px;
  font-weight: 600;
  color: #7B6CFF;
}

/* ── Action ── */
.card-action {
  flex-shrink: 0;
}
.btn-glow {
  background: linear-gradient(135deg, #7B6CFF, #5C8CFF) !important;
  border: none !important;
  color: #fff !important;
  box-shadow: 0 4px 16px rgba(123, 108, 255, 0.35);
}
.btn-glow:hover {
  box-shadow: 0 6px 24px rgba(123, 108, 255, 0.5);
  transform: translateY(-1px);
}

@media (max-width: 640px) {
  .exercise-card {
    flex-wrap: wrap;
    padding: 14px;
  }
  .card-main {
    flex: 1;
  }
  .card-action {
    width: 100%;
    display: flex;
    justify-content: flex-end;
  }
  .card-action :deep(.n-button) {
    width: 100%;
  }
}
</style>
