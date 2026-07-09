<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  movementName: string
  instruction: string
  mediaSrcs?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  mediaSrcs: () => []
})

function isVideo(src: string) {
  return /\.(mp4|webm|mov|avi)$/i.test(src)
}
const videoRef = ref<HTMLVideoElement | null>(null)

defineExpose({ videoRef })
</script>

<template>
  <div class="movement-demo">
    <div class="demo-title">{{ movementName }}</div>

    <div v-if="mediaSrcs.length > 0" class="media-grid">
      <div v-for="(src, i) in mediaSrcs" :key="i" class="media-box">
        <img v-if="!isVideo(src)" :src="src" :alt="movementName" class="media-content" />
        <video v-else :ref="(el: any) => { if (i === 0) videoRef = el }" :src="src" controls muted loop class="media-content" />
      </div>
    </div>
    <div v-else class="media-box">
      <div class="media-placeholder">
        <span class="placeholder-icon">🖼️</span>
        <span>暂无示范</span>
      </div>
    </div>

    <div class="instruction-tip">
      💡 {{ instruction }}
    </div>
  </div>
</template>

<style scoped>
.movement-demo {
  text-align: center;
  padding: 12px 0;
}

.demo-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 12px;
  color: #1a1a2e;
}

.media-grid {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.media-box {
  flex: 1;
  min-width: 180px;
  max-width: 320px;
  min-height: 240px;
  background: #f5f5f5;
  border-radius: 16px;
  border: 1px dashed #d9d9d9;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.media-content {
  width: 100%;
  max-height: 320px;
  object-fit: contain;
  border-radius: 16px;
}

.media-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #bbb;
  font-size: 13px;
  padding: 40px 0;
}

.placeholder-icon {
  font-size: 40px;
  margin-bottom: 8px;
}

.instruction-tip {
  background: #e6f7ff;
  border: 1px solid #91d5ff;
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 14px;
  color: #0050b3;
  line-height: 1.6;
  text-align: left;
}

:global(.dark) .demo-title { color: #e2e8f0; }
:global(.dark) .media-box { background: rgba(255,255,255,0.04); border-color: rgba(255,255,255,0.1); }
:global(.dark) .instruction-tip { background: rgba(24,144,255,0.1); border-color: rgba(24,144,255,0.25); color: #91caff; }

@media (max-width: 520px) {
  .media-grid { flex-direction: column; align-items: center; }
  .media-box { max-width: 100%; min-height: 180px; }
  .media-content { max-height: 240px; }
}
</style>
