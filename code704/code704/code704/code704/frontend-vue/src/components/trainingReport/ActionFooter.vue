<script setup lang="ts">
import { NButton, NIcon, NSpace } from 'naive-ui'
import { RefreshOutline, ArrowBackOutline, ListOutline } from '@vicons/ionicons5'

defineEmits<{
  (e: 'restart'): void
  (e: 'backToPlan'): void
  (e: 'viewAllPlans'): void
}>()
</script>

<template>
  <div class="footer">
    <n-space justify="center" size="medium" wrap>
      <n-button size="large" round class="btn-primary" @click="$emit('restart')">
        <template #icon><n-icon :component="RefreshOutline" /></template>
        重新训练
      </n-button>
      <n-button size="large" round class="btn-secondary" @click="$emit('backToPlan')">
        <template #icon><n-icon :component="ArrowBackOutline" /></template>
        返回训练计划
      </n-button>
      <n-button size="large" round text class="btn-tertiary" @click="$emit('viewAllPlans')">
        <template #icon><n-icon :component="ListOutline" /></template>
        查看全部计划
      </n-button>
    </n-space>
  </div>
</template>

<style scoped>
.footer {
  padding: 8px 0 0;
  text-align: center;
}

.btn-primary {
  min-width: 150px;
  font-weight: 700 !important;
  background: #7c3aed !important;
  border: none !important;
  color: #fff !important;
  box-shadow: 0 4px 14px -2px rgba(124,58,237,0.22) !important;
}
.btn-primary:hover {
  background: #6d28d9 !important;
  box-shadow: 0 6px 20px -2px rgba(124,58,237,0.30) !important;
  transform: translateY(-1px);
}

.btn-secondary {
  min-width: 150px;
  font-weight: 600 !important;
  border: 1px solid #e2e8f0 !important;
  color: #64748b !important;
  background: #fff !important;
}
.btn-secondary:hover {
  border-color: #c4b5fd !important;
  color: #7c3aed !important;
}

.btn-tertiary {
  min-width: 120px;
  font-weight: 500 !important;
  color: #b0b0c0 !important;
}
.btn-tertiary:hover {
  color: #7c3aed !important;
}

@media (max-width: 640px) {
  .btn-primary, .btn-secondary { min-width: 130px; }
}
</style>
