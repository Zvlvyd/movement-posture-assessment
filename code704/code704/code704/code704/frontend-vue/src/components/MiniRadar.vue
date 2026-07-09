<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  scores: Record<string, number>
  size?: number
}>()

const dims = ['balance_score', 'flexibility_score', 'upper_limb_score', 'core_score', 'symmetry_score']
const labels: Record<string, string> = {
  balance_score: '平衡', flexibility_score: '灵活', upper_limb_score: '上肢',
  core_score: '核心', symmetry_score: '对称',
}

const s = computed(() => props.size || 220)
const cx = computed(() => s.value / 2)
const cy = computed(() => s.value / 2)
const r = computed(() => s.value * 0.36)

const points = computed(() =>
  dims.map((d, i) => {
    const angle = (Math.PI * 2 * i) / dims.length - Math.PI / 2
    const val = Math.max((props.scores[d] || 0) / 100, 0.05)
    return {
      x: cx.value + r.value * val * Math.cos(angle),
      y: cy.value + r.value * val * Math.sin(angle),
      label: labels[d],
      score: props.scores[d] ?? '-',
    }
  })
)

const polyPoints = computed(() => points.value.map(p => `${p.x},${p.y}`).join(' '))

function ringPoints(scale: number): string {
  return dims
    .map((_, i) => {
      const a = (Math.PI * 2 * i) / dims.length - Math.PI / 2
      return `${cx.value + r.value * scale * Math.cos(a)},${cy.value + r.value * scale * Math.sin(a)}`
    })
    .join(' ')
}

function axisLine(i: number): { x2: number; y2: number } {
  const a = (Math.PI * 2 * i) / dims.length - Math.PI / 2
  return { x2: cx.value + r.value * Math.cos(a), y2: cy.value + r.value * Math.sin(a) }
}
</script>

<template>
  <svg :width="s" :height="s" :viewBox="`0 0 ${s} ${s}`" class="mini-radar">
    <!-- Rings -->
    <polygon
      v-for="scale in [0.25, 0.5, 0.75, 1]"
      :key="scale"
      :points="ringPoints(scale)"
      fill="none"
      stroke="#e2e8f0"
      stroke-width="1"
    />
    <!-- Axes -->
    <line
      v-for="(_, i) in dims"
      :key="'ax' + i"
      :x1="cx"
      :y1="cy"
      :x2="axisLine(i).x2"
      :y2="axisLine(i).y2"
      stroke="#e2e8f0"
      stroke-width="1"
    />
    <!-- Data polygon -->
    <polygon :points="polyPoints" fill="rgba(59,130,246,0.2)" stroke="#3b82f6" stroke-width="2" />
    <!-- Points + labels -->
    <g v-for="(p, i) in points" :key="'pt' + i">
      <circle :cx="p.x" :cy="p.y" r="4" fill="#3b82f6" />
      <text
        :x="p.x + (p.x > cx ? 9 : p.x < cx ? -9 : 0)"
        :y="p.y + (p.y > cy ? 15 : p.y < cy ? -7 : -7)"
        font-size="11"
        :text-anchor="p.x > cx ? 'start' : p.x < cx ? 'end' : 'middle'"
        fill="#334155"
      >
        {{ p.label }}:{{ p.score }}
      </text>
    </g>
  </svg>
</template>

<style scoped>
.mini-radar {
  display: block;
  margin: 0 auto;
}
</style>
