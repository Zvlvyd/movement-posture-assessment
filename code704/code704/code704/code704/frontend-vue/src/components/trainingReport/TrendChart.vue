<script setup lang="ts">
import { computed } from 'vue'
import * as echarts from 'echarts'
import VChart from 'vue-echarts'
import type { TrendPoint } from '../../mock/standardTrainingReportMock'

const props = defineProps<{ points: TrendPoint[] }>()

const option = computed(() => {
  if (!props.points?.length) return null
  return {
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['动作质量', '标准度', '稳定性'],
      bottom: 0,
      textStyle: { color: '#94a3b8', fontSize: 11 },
    },
    grid: { left: 10, right: 10, bottom: 36, top: 10, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: props.points.map(d => d.index),
      axisLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { color: '#b0b0c0', fontSize: 10 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f8f9fb' } },
      axisLabel: { color: '#b0b0c0', fontSize: 10 },
    },
    series: [
      {
        name: '动作质量', type: 'line', smooth: true, symbol: 'none',
        data: props.points.map(d => d.score),
        lineStyle: { width: 3, color: '#7c3aed' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(124,58,237,0.12)' },
            { offset: 1, color: 'rgba(124,58,237,0)' },
          ]),
        },
      },
      {
        name: '标准度', type: 'line', smooth: true, symbol: 'none',
        data: props.points.map(d => d.standard),
        lineStyle: { width: 2, color: '#6366f1' },
      },
      {
        name: '稳定性', type: 'line', smooth: true, symbol: 'none',
        data: props.points.map(d => d.stability),
        lineStyle: { width: 2, color: '#d97706' },
      },
    ],
  }
})
</script>

<template>
  <div style="background:#fff;border-radius:14px;box-shadow:0 1px 8px rgba(0,0,0,0.03);padding:18px 20px;">
    <div style="display:flex;align-items:center;gap:8px;font-size:15px;font-weight:700;color:#1e293b;margin-bottom:4px;">
      <span style="color:#7c3aed;">📈</span>
      <span>质量趋势</span>
    </div>
    <div style="width:100%;height:300px;">
      <v-chart v-if="option" :option="option" autoresize style="width:100%;height:100%;" />
      <div v-else style="display:flex;align-items:center;justify-content:center;height:100%;color:#94a3b8;">暂无趋势数据</div>
    </div>
  </div>
</template>
