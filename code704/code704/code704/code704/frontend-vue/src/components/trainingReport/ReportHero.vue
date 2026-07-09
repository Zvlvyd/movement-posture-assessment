<script setup lang="ts">
import { computed } from 'vue'
import { NIcon } from 'naive-ui'
import { CheckmarkCircleOutline } from '@vicons/ionicons5'

const props = defineProps<{
  actionName: string
  bestScore: number
  encouragement: string
  completedAt: string
}>()

const gradeInfo = computed(() => {
  const s = props.bestScore
  if (s >= 95) return { grade: 'A+', label: '动作标准' }
  if (s >= 90) return { grade: 'A',  label: '动作标准' }
  if (s >= 80) return { grade: 'B+', label: '基本达标' }
  if (s >= 70) return { grade: 'B',  label: '接近标准' }
  if (s >= 60) return { grade: 'C',  label: '有待提升' }
  return { grade: 'D', label: '需重点纠正' }
})
</script>

<template>
  <section class="hero">
    <!-- 极浅科技纹理 -->
    <div class="hero-texture"></div>

    <!-- 顶部辅助信息行（弱化） -->
    <div class="hero-top">
      <span class="hero-badge">
        <n-icon size="13" :component="CheckmarkCircleOutline" />
        训练完成
      </span>
      <span class="hero-time">{{ completedAt }}</span>
    </div>

    <!-- 唯一主视觉：评分环 -->
    <div class="hero-score">
      <svg viewBox="0 0 160 160">
        <circle cx="80" cy="80" r="68" fill="none" stroke="#f1f0f5" stroke-width="5" />
        <circle
          cx="80" cy="80" r="68"
          fill="none"
          stroke="#7c3aed"
          stroke-width="5"
          stroke-linecap="round"
          :stroke-dasharray="`${(bestScore / 100) * 427.3} 427.3`"
          transform="rotate(-90 80 80)"
        />
      </svg>
      <div class="score-inner">
        <span class="score-num">{{ bestScore }}</span>
        <span class="score-unit">分</span>
      </div>
    </div>

    <!-- 评分说明 -->
    <p class="score-label">单次动作最高得分</p>

    <!-- 动作名 + 等级（辅助标签） -->
    <div class="hero-mid">
      <h1 class="hero-action">{{ actionName }}</h1>
      <span class="hero-grade">{{ gradeInfo.grade }} · {{ gradeInfo.label }}</span>
    </div>

    <!-- 结论：仅一行 -->
    <p class="hero-conclusion">{{ encouragement }}</p>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.035);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 36px 32px 30px;
}

/* 科技网格 ≤5% */
.hero-texture {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.04;
  background-image:
    linear-gradient(#c0c0d0 1px, transparent 1px),
    linear-gradient(90deg, #c0c0d0 1px, transparent 1px);
  background-size: 38px 38px;
  mask-image: radial-gradient(ellipse 65% 55% at 50% 40%, black 25%, transparent 100%);
}

.hero-top {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 12px;
  border-radius: 20px;
  background: #f5f3ff;
  color: #7c3aed;
  font-size: 12px;
  font-weight: 600;
}

.hero-time {
  font-size: 12px;
  color: #b0b0c0;
}

/* 评分环 */
.hero-score {
  position: relative;
  z-index: 1;
  width: 164px;
  height: 164px;
  margin-bottom: 6px;
}

.hero-score svg {
  width: 100%;
  height: 100%;
}

.score-inner {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.score-num {
  font-size: 54px;
  font-weight: 800;
  color: #1e293b;
  line-height: 1;
  letter-spacing: -2px;
}

.score-unit {
  font-size: 15px;
  color: #94a3b8;
  font-weight: 500;
  margin-top: 2px;
}

.score-label {
  position: relative;
  z-index: 1;
  font-size: 12px;
  color: #a78bfa;
  margin: 0 0 16px;
}

/* 动作 + 等级 */
.hero-mid {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.hero-action {
  font-size: 19px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.hero-grade {
  font-size: 12px;
  font-weight: 600;
  color: #7c3aed;
  background: #f5f3ff;
  padding: 3px 10px;
  border-radius: 6px;
}

/* 结论一行 */
.hero-conclusion {
  position: relative;
  z-index: 1;
  font-size: 13px;
  color: #94a3b8;
  text-align: center;
  max-width: 480px;
  margin: 0;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .hero {
    padding: 26px 18px 22px;
  }
  .hero-score {
    width: 136px;
    height: 136px;
  }
  .score-num {
    font-size: 44px;
  }
  .hero-action {
    font-size: 17px;
  }
}
</style>
