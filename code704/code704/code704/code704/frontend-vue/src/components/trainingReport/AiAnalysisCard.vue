<script setup lang="ts">
import { computed } from 'vue'
import { NTag, NIcon } from 'naive-ui'
import { SparklesOutline, CheckmarkCircleOutline, PulseOutline, TrendingUpOutline, ShieldCheckmarkOutline } from '@vicons/ionicons5'
import type { ReportSummary } from '../../mock/standardTrainingReportMock'

const props = defineProps<{ analysis: ReportSummary }>()

const blocks = computed(() => {
  const t = props.analysis
  const hasData = !!(t.text && t.text !== '暂无分析数据。')
  return {
    conclusion: {
      label: '训练结论',
      icon: CheckmarkCircleOutline,
      text: hasData ? t.text : '本次动作执行完成，系统已采集完整关节角度数据用于比对分析。',
    },
    features: {
      label: '动作特征',
      icon: PulseOutline,
      tags: t.tags.length > 0 ? t.tags : ['动作完成', '数据已采集', '待进一步分析'],
    },
    suggestion: {
      label: 'AI 建议',
      icon: TrendingUpOutline,
      text: hasData ? t.nextSuggestion : '建议保持当前动作节奏，后续可尝试在不同条件下验证动作一致性。',
      tip: t.mainIssue && t.mainIssue !== '无' && t.mainIssue !== '无明显问题'
        ? `需关注：${t.mainIssue}`
        : '当前动作模式稳定，未检测到异常偏差。',
    },
  }
})
</script>

<template>
  <section class="ai">
    <div class="ai-head">
      <span class="ai-head-title">
        <n-icon size="17" :component="SparklesOutline" class="ai-head-icon" />
        AI 训练分析
      </span>
      <n-tag size="tiny" round :bordered="false" class="ai-head-tag">AI 评估</n-tag>
    </div>

    <div class="ai-body">
      <!-- 结论 -->
      <div class="ai-block">
        <div class="ai-block-head">
          <n-icon size="15" :component="blocks.conclusion.icon" class="ai-block-icon" />
          <span>{{ blocks.conclusion.label }}</span>
        </div>
        <p class="ai-block-text">{{ blocks.conclusion.text }}</p>
      </div>

      <!-- 特征标签 -->
      <div class="ai-block">
        <div class="ai-block-head">
          <n-icon size="15" :component="blocks.features.icon" class="ai-block-icon" />
          <span>{{ blocks.features.label }}</span>
        </div>
        <div class="ai-tags">
          <n-tag v-for="tag in blocks.features.tags" :key="tag" size="small" round :bordered="false" class="ai-tag">
            {{ tag }}
          </n-tag>
        </div>
      </div>

      <!-- 建议 -->
      <div class="ai-block ai-block--sug">
        <div class="ai-block-head">
          <n-icon size="15" :component="blocks.suggestion.icon" class="ai-block-icon" />
          <span>{{ blocks.suggestion.label }}</span>
        </div>
        <p class="ai-block-text">{{ blocks.suggestion.text }}</p>
        <div class="ai-tip">
          <n-icon size="12" :component="ShieldCheckmarkOutline" />
          <span>{{ blocks.suggestion.tip }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.ai {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.025);
  padding: 18px 22px;
}

.ai-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.ai-head-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
}

.ai-head-icon { color: #7c3aed; }

.ai-head-tag {
  background: #f5f3ff !important;
  color: #7c3aed !important;
  font-weight: 600;
}

.ai-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ai-block {
  padding: 12px 14px;
  border-radius: 10px;
  background: #f8f9fb;
}

.ai-block--sug {
  background: #f0fdfa;
}

.ai-block-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #475569;
}

.ai-block-icon { color: #7c3aed; }

.ai-block-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: #64748b;
}

.ai-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ai-tag {
  background: #f5f3ff !important;
  color: #7c3aed !important;
  font-weight: 500;
  border: none !important;
}

.ai-tip {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 8px;
  padding: 7px 10px;
  border-radius: 8px;
  background: #ccfbf1;
  font-size: 12px;
  color: #0d9488;
  font-weight: 500;
}

@media (max-width: 768px) {
  .ai { padding: 14px 16px; }
  .ai-block { padding: 10px 12px; }
}
</style>
