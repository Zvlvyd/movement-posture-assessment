<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { recordsApi } from '../../services/api'
import { NCard, NButton, NSpace, NSpin, NEmpty, NStatistic, NDataTable, NTag, NModal, NDescriptions, NDescriptionsItem, NIcon, NPopconfirm, useMessage } from 'naive-ui'
import { ArrowBackOutline, FitnessOutline, ChevronForwardOutline, TimeOutline, TrophyOutline, FlameOutline, CalendarOutline, TrendingUpOutline } from '@vicons/ionicons5'

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent])

const router = useRouter()
const message = useMessage()
const loading = ref(true)
const stats = ref({ total_sessions_7d: 0, total_sessions_30d: 0, average_score: 0, current_streak: 0 })
const recentRecords = ref<any[]>([])
const selectedRecord = ref<any>(null)
const showDetailModal = ref(false)

const accuracy = computed(() => {
  const avg = stats.value?.average_score
  return avg != null ? Math.round(Number(avg)) : 0
})

const sortedRecords = computed(() => {
  return [...recentRecords.value].sort((a, b) => {
    const ta = a.start_time ? new Date(a.start_time).getTime() : 0
    const tb = b.start_time ? new Date(b.start_time).getTime() : 0
    return tb - ta
  })
})

const lastTrainingDate = computed(() => {
  const latest = sortedRecords.value[0]
  return latest?.start_time ? new Date(latest.start_time).toLocaleDateString('zh-CN') : '--'
})

const categoryDistribution = computed(() => {
  const map: Record<string, number> = {}
  recentRecords.value.forEach(r => {
    const cat = r.category || '未分类'
    map[cat] = (map[cat] || 0) + 1
  })
  return Object.entries(map).map(([label, count]) => ({ label, count })).sort((a, b) => b.count - a.count)
})

const trendData = computed(() => {
  const list = sortedRecords.value.slice(0, 14).reverse()
  const dates = list.map(r => r.start_time ? new Date(r.start_time).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }) : '--')
  const scores = list.map(r => r.total_score != null ? Math.round(r.total_score) : 0)
  return { dates, scores }
})

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { top: 24, right: 16, bottom: 24, left: 40 },
  xAxis: {
    type: 'category',
    data: trendData.value.dates,
    axisLine: { lineStyle: { color: '#e2e8f0' } },
    axisLabel: { color: '#64748b', fontSize: 11 }
  },
  yAxis: {
    type: 'value',
    min: 0,
    max: 100,
    splitLine: { lineStyle: { color: '#f1f5f9' } },
    axisLabel: { color: '#64748b', fontSize: 11 }
  },
  series: [{
    type: 'line',
    data: trendData.value.scores,
    smooth: true,
    symbol: 'circle',
    symbolSize: 8,
    lineStyle: { color: '#3b82f6', width: 3 },
    itemStyle: { color: '#3b82f6', borderWidth: 2, borderColor: '#fff' },
    areaStyle: {
      color: {
        type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: 'rgba(59,130,246,0.25)' },
          { offset: 1, color: 'rgba(59,130,246,0.02)' }
        ]
      }
    }
  }]
}))

const categoryChartOption = computed(() => ({
  tooltip: { trigger: 'item' },
  grid: { top: 16, right: 16, bottom: 60, left: 16 },
  xAxis: {
    type: 'category',
    data: categoryDistribution.value.map(d => d.label),
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#64748b', fontSize: 11, rotate: 30, overflow: 'truncate', width: 60 }
  },
  yAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: '#f1f5f9' } },
    axisLabel: { color: '#64748b', fontSize: 11 }
  },
  series: [{
    type: 'bar',
    data: categoryDistribution.value.map(d => d.count),
    barWidth: '40%',
    itemStyle: {
      color: {
        type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: '#60a5fa' },
          { offset: 1, color: '#3b82f6' }
        ]
      },
      borderRadius: [8, 8, 0, 0]
    }
  }]
}))

async function deleteRecord(row: any) {
  try {
    await recordsApi.delete(row.id)
    message.success('已删除')
    recentRecords.value = recentRecords.value.filter(r => r.id !== row.id)
  } catch { message.error('删除失败') }
}

const columns = [
  { title: '时间', key: 'start_time', width: 140,
    render: (row: any) => row.start_time ? new Date(row.start_time).toLocaleString('zh-CN') : '--'
  },
  { title: '动作', key: 'action_name', width: 80,
    render: (row: any) => row.action_name || '--'
  },
  { title: '综合分', key: 'total_score', width: 70, align: 'center',
    render: (row: any) => row.total_score != null ? h('strong', null, String(Math.round(row.total_score))) : '--'
  },
  { title: '最佳分', key: 'best_score', width: 70, align: 'center',
    render: (row: any) => row.best_score != null ? h('span', { style: { color: '#7c3aed', fontWeight: 600 } }, String(Math.round(row.best_score))) : '--'
  },
  { title: '时长', key: 'duration', width: 60, align: 'center',
    render: (row: any) => row.duration ? `${Math.round(row.duration)}s` : '--'
  },
  {
    title: '操作', key: 'actions', width: 120,
    render: (row: any) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { type: 'primary', size: 'small', onClick: () => openDetail(row) }, { default: () => '查看' }),
        h(NPopconfirm, { onPositiveClick: () => deleteRecord(row) }, {
          trigger: () => h(NButton, { type: 'error', size: 'small' }, { default: () => '删除' }),
          default: () => '确认删除此训练记录？'
        })
      ]
    })
  }
]

const suggestions = computed(() => {
  const acc = accuracy.value
  const list = []
  if (acc >= 85) {
    list.push('整体动作表现优秀，建议保持当前训练节奏，每周进行 1-2 次进阶挑战。')
  } else if (acc >= 70) {
    list.push('动作达标率良好，可在常规训练中增加 1-2 个弱项动作专项练习。')
  } else if (acc >= 60) {
    list.push('动作表现仍有提升空间，建议降低动作难度，优先强化基础模式。')
  } else {
    list.push('当前动作达标率较低，建议从基础动作开始，配合教练或 AI 方案循序渐进。')
  }
  if (stats.value.current_streak >= 7) {
    list.push(`已连续打卡 ${stats.value.current_streak} 天，请继续保持训练习惯。`)
  } else {
    list.push('建议保持每周至少 3 次训练频率，以形成稳定的运动习惯。')
  }
  return list
})

function openDetail(row: any) {
  selectedRecord.value = row
  showDetailModal.value = true
}

function modeLabel(mode: string) {
  return mode === 'standard_learning' ? '标准学习' : mode === 'basic' ? '基础训练' : mode === 'advanced' ? '进阶训练' : mode === 'prescription' ? '方案训练' : mode || '--'
}

onMounted(async () => {
  try {
    const [s, history] = await Promise.all([
      recordsApi.stats(),
      recordsApi.history(90)
    ])
    stats.value = s
    recentRecords.value = (history || [])
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="report-center">
    <n-button text size="small" @click="router.push('/profile')">
      <template #icon><n-icon :component="ArrowBackOutline" /></template>
      返回个人中心
    </n-button>

    <n-card class="report-hero" :bordered="false">
      <div class="report-hero-content">
        <div class="report-icon" style="background: rgba(59,130,246,0.12); color: #3b82f6;">
          <n-icon size="32" :component="FitnessOutline" />
        </div>
        <div>
          <h1 class="report-title">标准动作分析报告</h1>
          <p class="report-desc">追踪标准动作训练表现与达标率趋势</p>
        </div>
      </div>
    </n-card>

    <n-spin v-if="loading" size="large" class="loading" />

    <template v-else>
      <!-- Overview Stats -->
      <n-card title="训练概览" class="report-card">
        <n-space align="center" size="large" wrap>
          <n-statistic label="动作达标率">
            <template #default>{{ accuracy }}</template>
            <template #suffix>%</template>
          </n-statistic>
          <n-statistic label="近 7 天训练">
            <template #default>{{ stats.total_sessions_7d }}</template>
            <template #suffix>次</template>
          </n-statistic>
          <n-statistic label="近 30 天训练">
            <template #default>{{ stats.total_sessions_30d }}</template>
            <template #suffix>次</template>
          </n-statistic>
          <n-statistic label="连续打卡">
            <template #default>{{ stats.current_streak }}</template>
            <template #suffix>天</template>
          </n-statistic>
          <n-statistic label="最近训练">
            <template #default>{{ lastTrainingDate }}</template>
          </n-statistic>
        </n-space>
      </n-card>

      <!-- Trend Charts -->
      <div class="two-col">
        <n-card title="评分趋势（近 14 次）" class="report-card chart-card">
          <div v-if="trendData.dates.length" class="chart-wrap">
            <v-chart :option="trendOption" autoresize class="chart" />
          </div>
          <n-empty v-else description="暂无评分趋势数据" />
        </n-card>

        <n-card title="动作分类分布" class="report-card chart-card">
          <div v-if="categoryDistribution.length" class="chart-wrap">
            <v-chart :option="categoryChartOption" autoresize class="chart" />
          </div>
          <n-empty v-else description="暂无分类分布数据" />
        </n-card>
      </div>

      <!-- Records Table -->
      <n-card title="训练记录明细" class="report-card">
        <n-data-table
          v-if="sortedRecords.length"
          :columns="columns"
          :data="sortedRecords"
          :row-key="(row: any) => row.id || row.start_time"
          :pagination="{ pageSize: 8 }"
          size="small"
        />
        <n-empty v-else description="暂无训练记录" />
      </n-card>

      <!-- AI Suggestions -->
      <n-card v-if="suggestions.length" title="训练建议" class="report-card suggestion-card">
        <div class="suggestion-list">
          <div v-for="(item, index) in suggestions" :key="index" class="suggestion-item">
            <div class="suggestion-num">{{ String(index + 1).padStart(2, '0') }}</div>
            <p>{{ item }}</p>
          </div>
        </div>
      </n-card>
    </template>

    <!-- Record Detail Modal -->
    <n-modal v-model:show="showDetailModal" preset="card" title="训练记录详情" style="width: 480px;">
      <n-descriptions v-if="selectedRecord" :column="1" bordered size="small" label-style="width: 100px">
        <n-descriptions-item label="记录 ID">{{ selectedRecord.id }}</n-descriptions-item>
        <n-descriptions-item label="训练动作">{{ selectedRecord.action_name || '--' }}</n-descriptions-item>
        <n-descriptions-item label="开始时间">{{ selectedRecord.start_time ? new Date(selectedRecord.start_time).toLocaleString('zh-CN') : '--' }}</n-descriptions-item>
        <n-descriptions-item label="动作分类">{{ selectedRecord.category || '--' }}</n-descriptions-item>
        <n-descriptions-item label="综合评分">{{ selectedRecord.total_score != null ? `${Math.round(selectedRecord.total_score)} 分` : '--' }}</n-descriptions-item>
        <n-descriptions-item label="最佳评分">{{ selectedRecord.best_score != null ? `${Math.round(selectedRecord.best_score)} 分` : '--' }}</n-descriptions-item>
        <n-descriptions-item label="训练时长">{{ selectedRecord.duration ? `${Math.round(selectedRecord.duration)} 秒` : '--' }}</n-descriptions-item>
      </n-descriptions>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showDetailModal = false">关闭</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.report-center {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.report-hero {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border-radius: 20px;
  color: #fff;
}
.report-hero-content {
  display: flex;
  align-items: center;
  gap: 18px;
}
.report-icon {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.report-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #fff;
}
.report-desc {
  margin: 6px 0 0;
  font-size: 14px;
  color: rgba(255,255,255,0.8);
}
.report-card {
  border-radius: 16px;
  background: rgba(255,255,255,0.95);
  box-shadow: 0 8px 30px rgba(59,130,246,0.08);
}
.loading { display: flex; justify-content: center; padding: 60px 0; }

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.chart-card :deep(.n-card__content) { padding-bottom: 8px; overflow: visible; }
.chart-wrap {
  width: 100%;
  height: 340px;
}
.chart {
  width: 100%;
  height: 100%;
}

.suggestion-card {
  background: linear-gradient(135deg, #eff6ff, #f8fafc);
}
.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.suggestion-item {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 14px 16px;
  border-radius: 12px;
  background: rgba(255,255,255,0.8);
}
.suggestion-num {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #3b82f6;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}
.suggestion-item p {
  margin: 0;
  font-size: 14px;
  color: #334155;
  line-height: 1.7;
}

@media (max-width: 768px) {
  .report-center { padding: 16px; }
  .two-col { grid-template-columns: 1fr; }
  .chart-wrap { height: 240px; }
}
</style>
