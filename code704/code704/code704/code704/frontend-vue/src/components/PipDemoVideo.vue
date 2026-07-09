<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick, computed } from 'vue'
import {
  VolumeMuteOutline,
  VolumeHighOutline,
  ChevronDownOutline,
  CloseOutline
} from '@vicons/ionicons5'
import { NButton, NIcon, NTag } from 'naive-ui'

interface Props {
  src: string
  visible: boolean
  currentTime?: number
  muted?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  currentTime: 0,
  muted: true
})

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'minimize'): void
  (e: 'update:muted', value: boolean): void
  (e: 'timeupdate', value: number): void
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const wrapperRef = ref<HTMLElement | null>(null)

const isVideo = computed(() => /\.(mp4|webm|mov|avi)$/i.test(props.src))

defineExpose({ videoRef })

const isDragging = ref(false)
const position = ref({ x: 0, y: 0 })
const dragStart = ref({ x: 0, y: 0, left: 0, top: 0 })

const isSmallScreen = ref(false)

function checkScreenSize() {
  isSmallScreen.value = window.innerWidth < 768
}

function getDefaultPosition() {
  const margin = isSmallScreen.value ? 12 : 20
  const width = isSmallScreen.value ? 160 : 200
  if (isSmallScreen.value) {
    return { x: window.innerWidth - width - margin, y: 80 }
  }
  return { x: window.innerWidth - width - margin, y: window.innerHeight - 150 }
}

function clampPosition(x: number, y: number) {
  const rect = wrapperRef.value?.getBoundingClientRect()
  const w = rect?.width ?? (isSmallScreen.value ? 160 : 200)
  const h = rect?.height ?? 120
  const margin = 8
  return {
    x: Math.max(margin, Math.min(window.innerWidth - w - margin, x)),
    y: Math.max(margin, Math.min(window.innerHeight - h - margin, y))
  }
}

function resetPosition() {
  position.value = getDefaultPosition()
}

function onMouseDown(e: MouseEvent | TouchEvent) {
  if (!wrapperRef.value) return
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  isDragging.value = true
  dragStart.value = {
    x: clientX,
    y: clientY,
    left: position.value.x,
    top: position.value.y
  }
}

function onMouseMove(e: MouseEvent | TouchEvent) {
  if (!isDragging.value) return
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  const dx = clientX - dragStart.value.x
  const dy = clientY - dragStart.value.y
  position.value = clampPosition(dragStart.value.left + dx, dragStart.value.top + dy)
}

function onMouseUp() {
  isDragging.value = false
}

function toggleMute() {
  emit('update:muted', !props.muted)
}

function emitCurrentTime() {
  const video = videoRef.value
  if (video) {
    emit('timeupdate', video.currentTime)
  }
}

watch(() => props.visible, async (visible) => {
  if (visible) {
    checkScreenSize()
    resetPosition()
    await nextTick()
    const video = videoRef.value
    if (video) {
      video.currentTime = props.currentTime || 0
      try { await video.play() } catch { /* ignore */ }
    }
  } else {
    emitCurrentTime()
  }
})

watch(() => props.currentTime, (time) => {
  const video = videoRef.value
  if (video && Math.abs(video.currentTime - time) > 0.5) {
    video.currentTime = time
  }
})

watch(() => props.muted, (muted) => {
  const video = videoRef.value
  if (video) video.muted = muted
})

onMounted(() => {
  checkScreenSize()
  resetPosition()
  window.addEventListener('resize', () => {
    checkScreenSize()
    position.value = clampPosition(position.value.x, position.value.y)
  })
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
  window.addEventListener('touchmove', onMouseMove, { passive: false })
  window.addEventListener('touchend', onMouseUp)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkScreenSize)
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
  window.removeEventListener('touchmove', onMouseMove)
  window.removeEventListener('touchend', onMouseUp)
})

const wrapperStyle = computed(() => ({
  transform: `translate3d(${position.value.x}px, ${position.value.y}px, 0)`,
  cursor: isDragging.value ? 'grabbing' : 'grab'
}))
</script>

<template>
  <Teleport to="body">
    <Transition name="pip-fade">
      <div
        v-if="visible"
        ref="wrapperRef"
        class="pip-demo-wrapper"
        :style="wrapperStyle"
        :class="{ 'is-dragging': isDragging, 'is-small': isSmallScreen }"
      >
        <div class="pip-demo-inner">
          <div class="pip-header" @mousedown.stop="onMouseDown" @touchstart.stop="onMouseDown">
            <n-tag size="small" round class="pip-label">示范</n-tag>
            <div class="pip-actions">
              <n-button v-if="isVideo" text size="tiny" class="pip-action-btn" @click.stop="toggleMute">
                <template #icon>
                  <n-icon :component="muted ? VolumeMuteOutline : VolumeHighOutline" />
                </template>
              </n-button>
              <n-button text size="tiny" class="pip-action-btn" @click.stop="isVideo && emitCurrentTime(); emit('minimize')">
                <template #icon>
                  <n-icon :component="ChevronDownOutline" />
                </template>
              </n-button>
              <n-button text size="tiny" class="pip-action-btn" @click.stop="isVideo && emitCurrentTime(); emit('close')">
                <template #icon>
                  <n-icon :component="CloseOutline" />
                </template>
              </n-button>
            </div>
          </div>
          <div class="pip-video-box" :class="{ 'is-image': !isVideo }">
            <img v-if="!isVideo" :src="src" class="pip-media" alt="示范" />
            <video
              v-else
              ref="videoRef"
              :src="src"
              class="pip-media"
              :muted="muted"
              loop
              playsinline
              autoplay
            />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.pip-demo-wrapper {
  position: fixed;
  top: 0;
  left: 0;
  width: 200px;
  z-index: 9999;
  border-radius: 16px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 12px 32px rgba(42, 35, 92, 0.18), 0 4px 12px rgba(139, 92, 246, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.6);
  transition: box-shadow 0.3s ease;
  user-select: none;
}

.pip-demo-wrapper.is-small {
  width: 160px;
}

.pip-demo-wrapper.is-dragging {
  transition: none;
  box-shadow: 0 18px 40px rgba(42, 35, 92, 0.24), 0 6px 16px rgba(139, 92, 246, 0.16);
}

.pip-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.12) 0%, rgba(59, 130, 246, 0.08) 100%);
  border-bottom: 1px solid rgba(139, 92, 246, 0.1);
}

.pip-label {
  font-weight: 700;
  color: #6d5df6;
  background: rgba(255, 255, 255, 0.7);
}

.pip-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.pip-action-btn {
  color: #64748b;
  transition: color 0.2s;
}

.pip-action-btn:hover {
  color: #6d5df6;
}

.pip-video-box {
  width: 100%;
  aspect-ratio: 4 / 3;
  background: #000;
}

.pip-video-box.is-image {
  aspect-ratio: auto;
  background: #f5f5f5;
}

.pip-video-box.is-image .pip-media {
  width: 100%;
  height: auto;
  object-fit: contain;
  max-height: 60vh;
}

.pip-media {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.pip-fade-enter-active .pip-demo-inner,
.pip-fade-leave-active .pip-demo-inner {
  transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}

.pip-fade-enter-from .pip-demo-inner,
.pip-fade-leave-to .pip-demo-inner {
  opacity: 0;
  transform: scale(0.85);
}
</style>
