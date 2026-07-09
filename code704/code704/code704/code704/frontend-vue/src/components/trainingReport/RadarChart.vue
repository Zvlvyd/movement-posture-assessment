<script setup lang="ts">
import { computed } from 'vue'
import * as echarts from 'echarts'
import VChart from 'vue-echarts'
import type { RadarDimension } from '../../mock/standardTrainingReportMock'

const props = defineProps<{ dimensions: RadarDimension[] }>()

const option = computed(() => ({
  radar: {
    indicator: props.dimensions.map(d => ({ name: d.name, max: d.max })),
    radius: '58%',
    center: ['50%', '46%'],
    splitNumber: 4,
    axisName: { color: '#b0b0c0', fontSize: 11 },
    splitLine: { lineStyle: { color: '#f1f5f9' } },
    splitArea: { areaStyle: { color: ['#fff', '#fafbfc', '#fff', '#fafbfc'] } },
    axisLine: { lineStyle: { color: '#e8ecf0' } },
  },
  series: [{
    type: 'radar',
    data: [{
      value: props.dimensions.map(d => d.value),
      areaStyle: { color: 'rgba(124,58,237,0.10)' },
      lineStyle: { width: 1.5, color: '#a78bfa' },
      itemStyle: { color: '#a78bfa', borderColor: '#fff', borderWidth: 1.5 },
      symbol: 'circle',
      symbolSize: 3,
    }],
  }],
}))
</script>

<template>
  <section class="chart-box">
    <div class="chart-hd">能力评分</div>
    <v-chart v-if="dimensions.length" class="chart-canvas" :option="option" autoresize />
    <div v-else class="chart-empty">暂无能力数据</div>
  </section>
</template>

<style scoped>
.chart-box {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.025);
  padding: 16px 20px;
}
.chart-hd {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 2px;
}
.chart-canvas {
  width: 100%;
  height: 290px;
}
.chart-empty {
  height: 290px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #b0b0c0;
  font-size: 13px;
}
@media (max-width: 768px) {
  .chart-canvas, .chart-empty { height: 250px; }
}
</style>
