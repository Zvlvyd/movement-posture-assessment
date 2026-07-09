<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { checkinApi } from '../services/api'
import {
  NCard, NButton, NSpace, NTag, NIcon, NText,
  NGrid, NGridItem, NProgress, NEmpty, NSpin
} from 'naive-ui'
import {
  CheckmarkCircleOutline, FlameOutline, TrophyOutline,
  CalendarOutline, StarOutline, MedalOutline,
  LockClosedOutline, FitnessOutline
} from '@vicons/ionicons5'

const todayChecked = ref(false)
const currentStreak = ref(0)
const totalCheckins = ref(0)
const monthlyCheckins = ref(0)
const checkinLoading = ref(false)
const checkinHistory = ref<boolean[]>(Array(7).fill(false))
const badges = ref<any[]>([])
const animateStats = ref(false)
const initialLoading = ref(true)
const loadError = ref('')

// ── Animated display values ──
const displayStreak = ref(0)
const displayTotal = ref(0)
const displayMonthly = ref(0)
const displayBadges = ref(0)

function animateValue(refVal: ref<number>, target: number, duration = 600) {
  const start = refVal.value
  const startTime = performance.now()
  function step(now: number) {
    const elapsed = now - startTime
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    refVal.value = Math.round(start + (target - start) * eased)
    if (progress < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

const badgeIcons: Record<string, any> = {
  streak_1: StarOutline,
  streak_7: FlameOutline,
  streak_30: MedalOutline,
  score_80: TrophyOutline,
  checkin_30: TrophyOutline,
}

const badgeColors: Record<string, string> = {
  streak_1: '#f59e0b',
  streak_7: '#ef4444',
  streak_30: '#8b5cf6',
  score_80: '#10b981',
  checkin_30: '#3b82f6',
}

// ── All possible badges (earned + locked) ──
const allBadges = [
  { type: 'streak_1', name: '初次打卡', desc: '完成第一次打卡', icon: StarOutline, color: '#f59e0b' },
  { type: 'streak_7', name: '连续达人', desc: '连续打卡7天', icon: FlameOutline, color: '#ef4444' },
  { type: 'streak_30', name: '月度冠军', desc: '连续打卡30天', icon: MedalOutline, color: '#8b5cf6' },
  { type: 'checkin_30', name: '累计30次', desc: '累计完成30次打卡', icon: TrophyOutline, color: '#3b82f6' },
  { type: 'score_80', name: '训练之星', desc: '训练评分达到80分', icon: TrophyOutline, color: '#10b981' },
]

const badgeMap = computed(() => {
  const map: Record<string, boolean> = {}
  badges.value.forEach((b: any) => { map[b.type] = true })
  return map
})

// ── Motivational text ──
const motivateText = computed(() => {
  const s = currentStreak.value
  if (s >= 30) return '月度王者，无人能挡！'
  if (s >= 14) return '两周坚持，已成习惯！'
  if (s >= 8) return '太棒了，继续保持！'
  if (s >= 4) return '已经养成好习惯！'
  if (s >= 2) return '坚持就是胜利！'
  return '迈出第一步！'
})

// ── Next milestone ──
const nextMilestone = computed(() => {
  const s = currentStreak.value
  if (s < 7) return { target: 7, name: '连续达人徽章', icon: FlameOutline, color: '#ef4444' }
  if (s < 30) return { target: 30, name: '月度冠军徽章', icon: MedalOutline, color: '#8b5cf6' }
  return { target: 60, name: '终极坚持勋章', icon: TrophyOutline, color: '#f59e0b' }
})

const weekDays = ['一', '二', '三', '四', '五', '六', '日']

const weekCompleted = computed(() => checkinHistory.value.filter(Boolean).length)
const weekRate = computed(() => Math.round((weekCompleted.value / 7) * 100))

function getWeekDayIndex(date: Date): number {
  const d = date.getDay()
  return d === 0 ? 6 : d - 1
}

async function loadStatus() {
  const s = await checkinApi.status()
      currentStreak.value = s.streak_days || 0
      const cards: Array<{ date: string; streak: number }> = s.recent_cards || []
      totalCheckins.value = cards.length > 0 ? cards.length : 0

      const now = new Date()
      const todayStr = now.toISOString().slice(0, 10)
      todayChecked.value = cards.some(c => c.date?.slice(0, 10) === todayStr)

      const thisMonth = now.toISOString().slice(0, 7)
      monthlyCheckins.value = cards.filter(c => c.date?.startsWith(thisMonth)).length

      const history = Array(7).fill(false)
      for (const card of cards) {
        const cardDate = new Date(card.date)
        const idx = getWeekDayIndex(cardDate)
        const todayIdx = getWeekDayIndex(now)
        const diffDays = Math.floor((now.getTime() - cardDate.getTime()) / 86400000)
        if (diffDays >= 0 && diffDays <= todayIdx) {
          history[idx] = true
        }
      }
      checkinHistory.value = history

      // Trigger count-up animation
      if (!animateStats.value) {
        animateStats.value = true
        setTimeout(() => {
          animateValue(displayStreak, currentStreak.value)
          animateValue(displayTotal, totalCheckins.value)
          animateValue(displayMonthly, monthlyCheckins.value)
          animateValue(displayBadges, badges.value.length)
        }, 300)
      }
}

async function loadBadges() {
  const list = await checkinApi.badges()
      badges.value = (list || []).map((b: any) => ({
        name: b.name || b.type || '徽章',
        type: b.type,
        icon: badgeIcons[b.type] || StarOutline,
        color: badgeColors[b.type] || '#f59e0b',
        earned: true
      }))
      animateValue(displayBadges, badges.value.length)
}

async function loadPageData() {
  initialLoading.value = true
  loadError.value = ''

  // 首次进入页面时，路由切换和开发代理偶尔会让首个请求失败。
  // 短暂重试一次，避免把默认的 0 误当成真实数据展示给用户。
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      await Promise.all([loadStatus(), loadBadges()])
      initialLoading.value = false
      return
    } catch (error) {
      if (attempt === 0) {
        await new Promise(resolve => setTimeout(resolve, 250))
        continue
      }
      console.error('加载打卡数据失败', error)
      loadError.value = '打卡数据加载失败，请点击重试'
    }
  }
  initialLoading.value = false
}

function handleCheckin() {
  if (todayChecked.value) return
  checkinLoading.value = true
  checkinApi.checkin()
    .then(() => {
      todayChecked.value = true
      currentStreak.value++
      totalCheckins.value++
      monthlyCheckins.value++
      const todayIdx = getWeekDayIndex(new Date())
      checkinHistory.value[todayIdx] = true
      animateValue(displayStreak, currentStreak.value)
      animateValue(displayTotal, totalCheckins.value)
      animateValue(displayMonthly, monthlyCheckins.value)
      loadBadges()
    })
    .catch(() => { alert('打卡失败，请重试') })
    .finally(() => { checkinLoading.value = false })
}

const earnedBadges = computed(() => badges.value.filter((b: any) => b.earned))

const todayIdx = computed(() => {
  const d = new Date().getDay()
  return d === 0 ? 6 : d - 1
})

onMounted(() => {
  loadPageData()
})
</script>

<script lang="ts">
export default { name: 'CheckinView' }
</script>

<template>
  <div class="checkin-wrapper">
    <!-- Background images -->
    <div class="bg-image bg-image-left"></div>
    <div class="bg-image bg-image-right"></div>
    <!-- Purple top fade -->
    <div class="bg-purple-top"></div>
    <!-- Top decorative patterns -->
    <div class="bg-pattern-top">
      <span class="deco-ring deco-ring-1"></span>
      <span class="deco-ring deco-ring-2"></span>
      <span class="deco-ring deco-ring-3"></span>
    </div>

    <div class="checkin-page">

      <div v-if="initialLoading || loadError" class="checkin-loading">
        <n-spin v-if="initialLoading" size="large" />
        <template v-else>
          <n-text type="error">{{ loadError }}</n-text>
          <n-button type="primary" @click="loadPageData">重新加载</n-button>
        </template>
      </div>

      <!-- Background glows -->
      <div class="bg-glow bg-glow-top"></div>
      <div class="bg-glow bg-glow-bottom"></div>

    <!-- ═══ Hero Banner ═══ -->
    <div class="hero-banner">
      <div class="hero-glow"></div>
      <div class="hero-decor hero-decor-1"></div>
      <div class="hero-decor hero-decor-2"></div>

      <div class="hero-inner">
        <!-- Left: Streak core -->
        <div class="hero-left">
          <div class="streak-header">
            <span class="streak-icon">🔥</span>
            <span class="streak-label">连续打卡</span>
          </div>
          <div class="streak-number">
            <span class="streak-big-num">{{ displayStreak }}</span>
            <span class="streak-unit">天</span>
          </div>
          <p class="streak-motivate">{{ motivateText }}</p>
        </div>

        <!-- Right: Growth + Checkin -->
        <div class="hero-right">
          <div class="growth-section">
            <div class="growth-header">
              <span class="growth-label">距离{{ nextMilestone.name }}</span>
              <span class="growth-fraction">{{ currentStreak }} / {{ nextMilestone.target }}</span>
            </div>
            <div class="growth-bar-track">
              <div
                class="growth-bar-fill"
                :style="{ width: Math.round((currentStreak / nextMilestone.target) * 100) + '%' }"
              ></div>
            </div>
            <p class="growth-hint">
              还需坚持 <strong>{{ nextMilestone.target - currentStreak }}</strong> 天即可获得下一枚徽章
            </p>
          </div>
          <n-button
            size="large"
            :disabled="todayChecked"
            :loading="checkinLoading"
            @click="handleCheckin"
            :class="todayChecked ? 'checkin-btn done' : 'checkin-btn'"
          >
            <template #icon>
              <n-icon :component="todayChecked ? CheckmarkCircleOutline : FlameOutline" />
            </template>
            {{ todayChecked ? '今日打卡成功' : '立即打卡' }}
          </n-button>
        </div>
      </div>
    </div>

    <!-- ═══ Stats Cards ═══ -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon" style="background:rgba(16,185,129,0.1);color:#10b981">
          <n-icon size="22" :component="CheckmarkCircleOutline" />
        </div>
        <span class="stat-num">{{ displayTotal }}</span>
        <span class="stat-label">累计打卡</span>
        <span class="stat-desc">累计完成 {{ displayTotal }} 次训练签到</span>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:rgba(59,130,246,0.1);color:#3b82f6">
          <n-icon size="22" :component="CalendarOutline" />
        </div>
        <span class="stat-num">{{ displayMonthly }}</span>
        <span class="stat-label">本月打卡</span>
        <span class="stat-desc">本月坚持训练 {{ displayMonthly }} 天</span>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:rgba(139,92,246,0.1);color:#8b5cf6">
          <n-icon size="22" :component="TrophyOutline" />
        </div>
        <span class="stat-num">{{ displayBadges }}</span>
        <span class="stat-label">获得徽章</span>
        <span class="stat-desc">{{ displayBadges > 0 ? `已获得 ${displayBadges} 枚荣誉徽章` : '继续努力获得第一枚徽章' }}</span>
      </div>
    </div>

    <!-- ═══ Weekly Checkin ═══ -->
    <div class="panel-card">
      <div class="panel-header">
        <span class="panel-title">本周打卡</span>
        <span class="panel-extra">完成 {{ weekCompleted }} / 7 · {{ weekRate }}%</span>
      </div>
      <n-progress
        :percentage="weekRate"
        :height="6"
        color="#10b981"
        rail-color="#f1f5f9"
        :show-indicator="false"
        style="margin-bottom: 20px;"
      />
      <div class="week-grid">
        <div
          v-for="(day, idx) in weekDays"
          :key="idx"
          class="day-item"
          :class="{
            checked: checkinHistory[idx],
            today: idx === todayIdx,
            past: idx < todayIdx && !checkinHistory[idx]
          }"
        >
          <span class="day-label">{{ day }}</span>
          <div class="day-dot">
            <n-icon
              v-if="checkinHistory[idx]"
              size="18"
              :component="CheckmarkCircleOutline"
            />
            <span v-else-if="idx === todayIdx" class="day-dot-text">今</span>
            <span v-else class="day-dot-empty"></span>
          </div>
          <span class="day-status">
            {{ checkinHistory[idx] ? '完成' : idx === todayIdx ? '今日' : '待完成' }}
          </span>
        </div>
      </div>
    </div>

    <!-- ═══ Growth Goals ═══ -->
    <div class="panel-card">
      <div class="panel-header">
        <span class="panel-title">🎯 今日目标</span>
      </div>
      <div class="goal-list">
        <div class="goal-item done">
          <n-icon size="18" :component="CheckmarkCircleOutline" color="#10b981" />
          <span>完成今日打卡</span>
          <n-tag type="success" size="tiny" round :bordered="false">已完成</n-tag>
        </div>
        <div class="goal-item">
          <div class="goal-dot"></div>
          <span>完成一次训练</span>
          <n-tag type="default" size="tiny" round :bordered="false">待完成</n-tag>
        </div>
        <div class="goal-item">
          <div class="goal-dot"></div>
          <span>保持训练15分钟</span>
          <n-tag type="default" size="tiny" round :bordered="false">待完成</n-tag>
        </div>
      </div>
      <div style="margin-top:16px;">
        <n-progress
          :percentage="todayChecked ? 33 : 0"
          :height="8"
          color="linear-gradient(90deg, #f59e0b, #ef4444)"
          rail-color="#f1f5f9"
          :show-indicator="false"
        />
        <span style="font-size:12px;color:#94a3b8;margin-top:6px;display:block;">完成度 {{ todayChecked ? 33 : 0 }}%</span>
      </div>
    </div>

    <!-- ═══ Streak Progress ═══ -->
    <div v-if="currentStreak < 60" class="panel-card">
      <div class="panel-header">
        <span class="panel-title">🔥 连续成长</span>
        <span class="panel-extra">{{ currentStreak }} / {{ nextMilestone.target }} 天</span>
      </div>
      <p class="milestone-desc">
        再坚持 <strong>{{ nextMilestone.target - currentStreak }}</strong> 天即可获得：
      </p>
      <div class="milestone-badge">
        <div class="milestone-icon" :style="{ background: nextMilestone.color + '15', color: nextMilestone.color }">
          <n-icon size="24" :component="nextMilestone.icon" />
        </div>
        <span class="milestone-name">{{ nextMilestone.name }}</span>
      </div>
      <n-progress
        :percentage="Math.round((currentStreak / nextMilestone.target) * 100)"
        :height="8"
        color="linear-gradient(90deg, #f59e0b, #ef4444)"
        rail-color="#f1f5f9"
        :show-indicator="false"
        style="margin-top: 12px;"
      />
    </div>

    <!-- ═══ Badges ═══ -->
    <div class="panel-card">
      <div class="panel-header">
        <span class="panel-title">成就徽章</span>
      </div>
      <div class="badges-row">
        <div
          v-for="badge in allBadges"
          :key="badge.type"
          class="badge-item"
          :class="{ earned: badgeMap[badge.type], locked: !badgeMap[badge.type] }"
        >
          <div
            class="badge-icon-box"
            :style="{
              background: badgeMap[badge.type] ? badge.color + '15' : '#f1f5f9',
              color: badgeMap[badge.type] ? badge.color : '#cbd5e1'
            }"
          >
            <n-icon size="26" :component="badgeMap[badge.type] ? badge.icon : LockClosedOutline" />
          </div>
          <span class="badge-item-name">{{ badge.name }}</span>
          <span v-if="badgeMap[badge.type]" class="badge-item-status earned-text">已获得</span>
          <span v-else class="badge-item-status locked-text">{{ badge.desc }}</span>
        </div>
      </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── Wrapper ── */
.checkin-wrapper {
  position: relative;
  min-height: calc(100vh - 64px - 56px);
  background: linear-gradient(180deg, #faf9ff 0%, #f5f4ff 55%, #ffffff 100%);
}

/* ── Page ── */
.checkin-page {
  position: relative;
  max-width: 700px;
  margin: -24px auto 0;
  padding: 24px 24px 40px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: calc(100vh - 64px - 56px);
}

.checkin-loading {
  position: absolute;
  inset: 0;
  z-index: 20;
  min-height: 360px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  border-radius: 20px;
  background: rgba(250, 249, 255, 0.96);
  backdrop-filter: blur(6px);
}

.checkin-page::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(rgba(108,99,255,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(108,99,255,0.04) 1px, transparent 1px);
  background-size: 30px 30px, 30px 30px;
  pointer-events: none;
  z-index: 0;
}

.bg-glow {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
  filter: blur(80px);
}
.bg-glow-top {
  width: 300px; height: 300px;
  top: -60px; left: -80px;
  background: rgba(255,152,0,0.06);
}
.bg-glow-bottom {
  width: 260px; height: 260px;
  bottom: 10%; right: -60px;
  background: rgba(239,68,68,0.05);
}

.bg-image {
  position: absolute;
  top: 0;
  min-height: 100%;
  width: 300px;
  z-index: 1;
  background-repeat: no-repeat;
  opacity: 0.5;
  pointer-events: none;
}
.bg-image-left {
  left: 0;
  background-image: url('/media/pictures/checkin_left.jpg');
  background-position: left bottom;
  background-size: 100% auto;
}
.bg-image-right {
  right: 0;
  background-image: url('/media/pictures/checkin_right.png');
  background-position: right bottom;
  background-size: 100% auto;
}

.bg-purple-top {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 400px;
  z-index: 2;
  background: linear-gradient(180deg, rgba(108,99,255,0.12) 0%, rgba(140,130,255,0.06) 30%, transparent 100%);
  pointer-events: none;
}

/* ── Top Decorative Patterns ── */
.bg-pattern-top {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 380px;
  z-index: 3;
  pointer-events: none;
}

/* Scattered soft dots */
.bg-pattern-top::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background:
    radial-gradient(circle at 12% 18%, rgba(108,99,255,0.09) 0%, transparent 7%),
    radial-gradient(circle at 88% 12%, rgba(108,99,255,0.07) 0%, transparent 10%),
    radial-gradient(circle at 48% 30%, rgba(140,120,255,0.06) 0%, transparent 9%),
    radial-gradient(circle at 22% 45%, rgba(108,99,255,0.08) 0%, transparent 5%),
    radial-gradient(circle at 78% 40%, rgba(140,120,255,0.06) 0%, transparent 7%),
    radial-gradient(circle at 35% 10%, rgba(168,150,255,0.10) 0%, transparent 3%),
    radial-gradient(circle at 62% 22%, rgba(168,150,255,0.08) 0%, transparent 4%),
    radial-gradient(circle at 8% 38%, rgba(108,99,255,0.06) 0%, transparent 6%),
    radial-gradient(circle at 92% 32%, rgba(108,99,255,0.07) 0%, transparent 5%),
    radial-gradient(circle at 55% 48%, rgba(140,120,255,0.05) 0%, transparent 8%);
}

/* Subtle wavy line */
.bg-pattern-top::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 200px;
  background:
    radial-gradient(ellipse 800px 60px at 50% 0%, rgba(168,150,255,0.06) 0%, transparent 100%);
}

/* Thin decorative rings */
.deco-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(168,150,255,0.1);
  pointer-events: none;
}
.deco-ring-1 {
  width: 180px; height: 180px;
  top: -60px; right: -40px;
}
.deco-ring-2 {
  width: 120px; height: 120px;
  top: 40px; left: -30px;
  border-color: rgba(168,150,255,0.07);
}
.deco-ring-3 {
  width: 200px; height: 200px;
  top: -30px; left: 40%;
  border-color: rgba(168,150,255,0.06);
}

/* ── Hero Banner ── */
.hero-banner {
  position: relative;
  z-index: 1;
  background: linear-gradient(135deg, #FF9800, #FF7043, #FF5252);
  border-radius: 20px;
  padding: 32px 36px;
  overflow: hidden;
}
.hero-glow {
  position: absolute;
  width: 280px; height: 280px;
  top: -80px; right: -60px;
  border-radius: 50%;
  background: rgba(255,255,255,0.04);
  filter: blur(60px);
  pointer-events: none;
}
.hero-decor {
  position: absolute;
  border-radius: 50%;
  background: rgba(255,255,255,0.05);
  pointer-events: none;
}
.hero-decor-1 { width: 80px; height: 80px; bottom: -20px; left: 20%; }
.hero-decor-2 { width: 40px; height: 40px; top: 24px; right: 35%; }
.hero-inner {
  position: relative;
  z-index: 1;
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 32px;
}

/* ── Left: Streak ── */
.hero-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.streak-header {
  display: flex;
  align-items: center;
  gap: 6px;
}
.streak-icon { font-size: 16px; line-height: 1; }
.streak-label {
  font-size: 13px;
  color: rgba(255,255,255,0.75);
  font-weight: 500;
}
.streak-number {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.streak-big-num {
  font-size: 64px;
  font-weight: 800;
  line-height: 1;
  color: #fff;
  animation: breathe-num 3s ease-in-out infinite;
}
@keyframes breathe-num {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.03); }
}
.streak-unit {
  font-size: 18px;
  font-weight: 500;
  color: rgba(255,255,255,0.8);
}
.streak-motivate {
  font-size: 13px;
  color: rgba(255,255,255,0.65);
  margin: 0;
}

/* ── Right: Growth + Checkin ── */
.hero-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 14px;
  min-width: 220px;
}
.growth-section {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.growth-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.growth-label {
  font-size: 12px;
  color: rgba(255,255,255,0.7);
}
.growth-fraction {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255,255,255,0.85);
}
.growth-bar-track {
  width: 100%;
  height: 6px;
  background: rgba(255,255,255,0.15);
  border-radius: 3px;
  overflow: hidden;
}
.growth-bar-fill {
  height: 100%;
  background: rgba(255,255,255,0.65);
  border-radius: 3px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.growth-hint {
  font-size: 11px;
  color: rgba(255,255,255,0.55);
  margin: 0;
}
.growth-hint strong {
  color: rgba(255,255,255,0.8);
  font-weight: 600;
}

/* Checkin button */
.checkin-btn {
  background: rgba(255,255,255,0.18) !important;
  backdrop-filter: blur(10px) !important;
  color: #fff !important;
  border: 1px solid rgba(255,255,255,0.25) !important;
  border-radius: 12px !important;
  padding: 10px 24px !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  height: auto !important;
  transition: all 0.3s ease !important;
}
.checkin-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.12);
  background: rgba(255,255,255,0.25) !important;
}
.checkin-btn.done {
  background: rgba(255,255,255,0.28) !important;
  border-color: rgba(255,255,255,0.35) !important;
}
.checkin-btn.done:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.12);
}

/* ── Stats Row ── */
.stats-row {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.stat-card {
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(18px);
  border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.8);
  box-shadow: 0 12px 40px rgba(108,99,255,0.08);
  padding: 20px 16px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  transition: all 0.25s ease;
}
.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 16px 44px rgba(108,99,255,0.14);
}
.stat-icon {
  width: 44px; height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stat-num {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.2;
}
.stat-label {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
}
.stat-desc {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

/* ── Panel Card (unified) ── */
.panel-card {
  position: relative;
  z-index: 1;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(18px);
  border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.8);
  box-shadow: 0 12px 40px rgba(108,99,255,0.08);
  padding: 24px 28px;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}
.panel-title { font-size: 17px; font-weight: 600; color: #1e293b; }
.panel-extra { font-size: 13px; color: #94a3b8; }

/* ── Week Grid ── */
.week-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
}
.day-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 4px;
  border-radius: 12px;
  transition: all 0.25s ease;
}
.day-item.today {
  background: rgba(59,130,246,0.06);
}
.day-label {
  font-size: 12px;
  color: #94a3b8;
}
.day-item.today .day-label {
  color: #3b82f6;
  font-weight: 600;
}
.day-dot {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.day-item.checked .day-dot {
  background: #10b981;
  color: #fff;
  animation: pop-in 0.35s ease;
}
@keyframes pop-in {
  0% { transform: scale(0.8); }
  60% { transform: scale(1.15); }
  100% { transform: scale(1); }
}
.day-item.past .day-dot {
  background: #fee2e2;
}
.day-dot-text {
  font-size: 12px;
  font-weight: 600;
  color: #3b82f6;
}
.day-dot-empty {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #d1d5db;
}
.day-status {
  font-size: 10px;
  color: #94a3b8;
}
.day-item.checked .day-status { color: #10b981; }
.day-item.today .day-status { color: #3b82f6; }

/* ── Goals ── */
.goal-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.goal-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #f8fafc;
  font-size: 14px;
  color: #475569;
}
.goal-item.done {
  background: rgba(16,185,129,0.05);
}
.goal-dot {
  width: 18px; height: 18px;
  border-radius: 50%;
  border: 2px solid #d1d5db;
  flex-shrink: 0;
}

/* ── Milestone ── */
.milestone-desc {
  font-size: 14px;
  color: #64748b;
  margin: 0 0 14px;
}
.milestone-desc strong {
  color: #ef4444;
  font-size: 18px;
}
.milestone-badge {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}
.milestone-icon {
  width: 44px; height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.milestone-name {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

/* ── Badges ── */
.badges-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 10px;
}
.badge-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 8px;
  border-radius: 14px;
  text-align: center;
  transition: all 0.25s ease;
  cursor: default;
}
.badge-item.earned {
  background: rgba(16,185,129,0.04);
}
.badge-item.earned:hover {
  transform: rotate(2deg) scale(1.03);
}
.badge-item.locked:hover {
  transform: rotate(-2deg) scale(1.03);
}
.badge-icon-box {
  width: 50px; height: 50px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
}
.badge-item-name {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
}
.badge-item-status {
  font-size: 10px;
}
.earned-text { color: #10b981; }
.locked-text { color: #94a3b8; }

/* ── Mobile ── */
@media (max-width: 640px) {
  .checkin-page {
    padding: 16px;
    margin: -16px auto 0;
    gap: 14px;
  }
  .hero-banner {
    padding: 24px 20px;
  }
  .hero-inner {
    flex-direction: column;
    text-align: center;
    gap: 20px;
  }
  .hero-left {
    align-items: center;
  }
  .hero-right {
    align-items: center;
    min-width: 0;
    width: 100%;
  }
  .streak-big-num {
    font-size: 48px;
  }
  .streak-motivate {
    font-size: 12px;
  }
  .stats-row {
    grid-template-columns: 1fr;
  }
  .week-grid {
    gap: 4px;
  }
  .day-item {
    padding: 8px 2px;
  }
  .badges-row {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
