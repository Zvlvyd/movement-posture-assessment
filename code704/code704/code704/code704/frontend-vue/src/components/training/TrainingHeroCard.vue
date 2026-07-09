<script setup lang="ts">
import { NCard, NTag, NIcon, NProgress } from 'naive-ui'
import { FlameOutline, TimeOutline, FitnessOutline, TrophyOutline } from '@vicons/ionicons5'

defineProps<{
  planName: string
  totalExercises: number
  doneCount: number
  progressPercent: number
  totalDurationMinutes: number
  remainingMinutes: number
  motivationalText: string
  phaseBreakdown: Array<{ phase: string; label: string; color: string; total: number; done: number }>
}>()
</script>

<template>
  <div class="hero-card">
    <!-- Background decorations -->
    <div class="hero-bg-decor hero-decor-1"></div>
    <div class="hero-bg-decor hero-decor-2"></div>
    <div class="hero-bg-decor hero-decor-3"></div>

    <!-- Content -->
    <div class="hero-content">
      <!-- Left side -->
      <div class="hero-left">
        <div class="hero-badge">
          <n-icon size="14" :component="FlameOutline" />
          <span>今日训练概览</span>
        </div>
        <h2 class="hero-plan-name">{{ planName }}</h2>
        <div class="hero-tags">
          <n-tag size="small" round :bordered="false">
            {{ totalExercises }} 个动作
          </n-tag>
          <n-tag size="small" round :bordered="false">
            约 {{ totalDurationMinutes }} 分钟
          </n-tag>
        </div>

        <!-- Progress bar -->
        <div class="hero-progress-area">
          <div class="hero-progress-header">
            <span class="progress-label">训练进度</span>
            <span class="progress-value">{{ progressPercent }}%</span>
          </div>
          <n-progress
            type="line"
            :percentage="progressPercent"
            :height="8"
            :border-radius="4"
            :color="'#fff'"
            :rail-color="'rgba(255,255,255,0.2)'"
            :show-indicator="false"
          />
        </div>

        <!-- Stats row -->
        <div class="hero-stats">
          <div class="hero-stat">
            <n-icon size="16" :component="FitnessOutline" />
            <span class="stat-num">{{ doneCount }}/{{ totalExercises }}</span>
            <span class="stat-label">已完成</span>
          </div>
          <div class="hero-stat">
            <n-icon size="16" :component="TimeOutline" />
            <span class="stat-num">{{ remainingMinutes }}</span>
            <span class="stat-label">剩余分钟</span>
          </div>
          <div class="hero-stat">
            <n-icon size="16" :component="TrophyOutline" />
            <span class="stat-num">{{ doneCount }}</span>
            <span class="stat-label">已练动作</span>
          </div>
        </div>

        <!-- Motivational text -->
        <p class="hero-motivation">{{ motivationalText }}</p>
      </div>

      <!-- Right side: progress ring -->
      <div class="hero-right">
        <div class="progress-ring-container">
          <svg viewBox="0 0 120 120" class="progress-ring-svg">
            <circle
              cx="60" cy="60" r="52"
              fill="none"
              stroke="rgba(255,255,255,0.18)"
              stroke-width="8"
            />
            <circle
              cx="60" cy="60" r="52"
              fill="none"
              stroke="#fff"
              stroke-width="8"
              stroke-linecap="round"
              :stroke-dasharray="2 * Math.PI * 52"
              :stroke-dashoffset="2 * Math.PI * 52 * (1 - progressPercent / 100)"
              transform="rotate(-90 60 60)"
              class="progress-ring-fill"
            />
          </svg>
          <div class="progress-ring-center">
            <span class="ring-percent">{{ progressPercent }}</span>
            <span class="ring-unit">%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Phase breakdown mini bar -->
    <div class="hero-phase-bar">
      <div
        v-for="pb in phaseBreakdown"
        :key="pb.phase"
        class="phase-bar-segment"
        :style="{ flex: pb.total, background: pb.color }"
        :title="`${pb.label}: ${pb.done}/${pb.total}`"
      ></div>
    </div>
  </div>
</template>

<style scoped>
.hero-card {
  position: relative;
  background: linear-gradient(135deg, #5B4DFF 0%, #7B6CFF 50%, #4F8CFF 100%);
  border-radius: 24px;
  padding: 28px 32px 0;
  color: #fff;
  overflow: hidden;
  box-shadow: 0 16px 48px rgba(91, 77, 255, 0.22);
}

/* ── Background decorations ── */
.hero-bg-decor {
  position: absolute;
  border-radius: 50%;
  background: rgba(255,255,255,0.06);
  pointer-events: none;
}
.hero-decor-1 {
  width: 200px; height: 200px;
  top: -40px; right: -50px;
}
.hero-decor-2 {
  width: 120px; height: 120px;
  bottom: -20px; left: 30%;
  background: rgba(255,255,255,0.04);
}
.hero-decor-3 {
  width: 80px; height: 80px;
  top: 60px; left: -20px;
  background: rgba(255,255,255,0.05);
}

/* ── Content ── */
.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
}
.hero-left {
  flex: 1;
  min-width: 0;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 16px;
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 12px;
}
.hero-plan-name {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 10px;
  line-height: 1.3;
}
.hero-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* ── Progress area ── */
.hero-progress-area {
  margin-top: 18px;
  max-width: 360px;
}
.hero-progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}
.progress-label {
  font-size: 12px;
  opacity: 0.8;
}
.progress-value {
  font-size: 13px;
  font-weight: 700;
}

/* ── Stats row ── */
.hero-stats {
  display: flex;
  gap: 20px;
  margin-top: 16px;
}
.hero-stat {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.stat-num {
  font-weight: 700;
  font-size: 15px;
}
.stat-label {
  opacity: 0.7;
  font-size: 12px;
}

/* ── Motivation ── */
.hero-motivation {
  margin: 14px 0 0;
  font-size: 13px;
  opacity: 0.75;
  font-style: italic;
  line-height: 1.5;
}

/* ── Progress ring ── */
.hero-right {
  flex-shrink: 0;
}
.progress-ring-container {
  position: relative;
  width: 110px;
  height: 110px;
}
.progress-ring-svg {
  width: 100%;
  height: 100%;
}
.progress-ring-fill {
  transition: stroke-dashoffset 0.8s ease;
}
.progress-ring-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.ring-percent {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}
.ring-unit {
  font-size: 12px;
  opacity: 0.7;
}

/* ── Phase breakdown bar ── */
.hero-phase-bar {
  display: flex;
  height: 4px;
  margin: 20px -32px 0;
  border-radius: 0 0 4px 4px;
  overflow: hidden;
}
.phase-bar-segment {
  min-width: 4px;
  opacity: 0.7;
  transition: flex 0.4s ease;
}

@media (max-width: 640px) {
  .hero-card {
    padding: 20px 20px 0;
  }
  .hero-content {
    flex-direction: column;
  }
  .hero-right {
    align-self: center;
  }
  .hero-stats {
    flex-wrap: wrap;
    gap: 12px;
  }
  .hero-phase-bar {
    margin: 16px -20px 0;
  }
}
</style>
