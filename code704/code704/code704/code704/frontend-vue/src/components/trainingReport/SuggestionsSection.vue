<script setup lang="ts">
import { computed } from 'vue'
import type { SuggestionGroup } from '../../mock/standardTrainingReportMock'

const props = defineProps<{ groups: SuggestionGroup[] }>()

const COLUMNS = [
  { key: 'strength',   title: '优势',       dot: '#7c3aed' },
  { key: 'risk',       title: '风险判断',   dot: '#d97706' },
  { key: 'strategy',   title: '下一步策略', dot: '#0d9488' },
]

const enriched = computed(() => {
  return COLUMNS.map((col, i) => {
    const g = props.groups[i]
    // 风险判断列为空 → 系统判断
    if (i === 1 && (!g || g.items.length === 0)) {
      return {
        ...col,
        items: [{ title: '当前动作稳定，无明显异常风险。', desc: '' }],
      }
    }
    // 策略列为空 → 默认策略
    if (i === 2 && (!g || g.items.length === 0)) {
      return {
        ...col,
        items: [{ title: '维持当前训练节奏，逐步提升动作自动化水平。', desc: '' }],
      }
    }
    if (!g) return { ...col, items: [] }
    return {
      ...col,
      items: g.items.map(item => ({
        title: item.title,
        desc: item.desc,
      })),
    }
  })
})
</script>

<template>
  <section class="sug">
    <div class="sug-hd">总结与建议</div>

    <div class="sug-cols">
      <div v-for="col in enriched" :key="col.key" class="sug-col">
        <!-- 栏头 -->
        <div class="sug-col-hd">
          <span class="sug-col-dot" :style="{ background: col.dot }"></span>
          <span class="sug-col-title">{{ col.title }}</span>
        </div>

        <!-- 条目 -->
        <div class="sug-items">
          <div v-for="item in col.items" :key="item.title" class="sug-item">
            <template v-if="item.desc">
              <span class="sug-item-title">{{ item.title }}</span>
              <span class="sug-item-desc">{{ item.desc }}</span>
            </template>
            <!-- 风险判断列：纯系统语句，不拆分标题/描述 -->
            <template v-else>
              <span class="sug-item-sys">{{ item.title }}</span>
            </template>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.sug {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.025);
  padding: 18px 22px;
}

.sug-hd {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 14px;
}

.sug-cols {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}

.sug-col {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sug-col-hd {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f1f5f9;
}

.sug-col-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.sug-col-title {
  font-size: 13px;
  font-weight: 700;
  color: #475569;
}

.sug-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sug-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 6px 0;
}

.sug-item-title {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.sug-item-desc {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.55;
}

/* 系统判断语句 */
.sug-item-sys {
  font-size: 13px;
  color: #d97706;
  font-weight: 500;
}

@media (max-width: 1024px) {
  .sug-cols {
    grid-template-columns: 1fr;
  }
}
</style>
