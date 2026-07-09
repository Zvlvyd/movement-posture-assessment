import type { PlanV2 } from '../types'

export function shouldUseMock(): boolean {
  if (typeof window !== 'undefined') {
    const url = new URL(window.location.href)
    if (url.searchParams.has('mock')) return true
    return localStorage.getItem('training_use_mock') === 'true'
  }
  return false
}

export const mockPlans: PlanV2[] = [
  {
    id: 1,
    user_id: 1,
    plan_name: '上肢力量与体态矫正',
    status: 'active',
    generation_method: 'deepseek',
    difficulty: 3,
    created_at: '2026-07-01T08:00:00Z',
    items: [
      { id: 101, plan_id: 1, action_id: 'w1', action_name: '猫式伸展', phase: 'warmup', sets: 1, reps: 10, duration: 30, order_index: 1, alternative: false },
      { id: 102, plan_id: 1, action_id: 'w2', action_name: '肩关节环绕', phase: 'warmup', sets: 1, reps: 15, duration: 25, order_index: 2, alternative: false },
      { id: 103, plan_id: 1, action_id: 'm1', action_name: '俯卧撑', phase: 'main', sets: 3, reps: 12, duration: 45, order_index: 3, alternative: false, notes: '保持核心收紧' },
      { id: 104, plan_id: 1, action_id: 'm2', action_name: '弹力带划船', phase: 'main', sets: 3, reps: 15, duration: 40, order_index: 4, alternative: false },
      { id: 105, plan_id: 1, action_id: 'm3', action_name: '平板支撑', phase: 'main', sets: 2, reps: 1, duration: 60, order_index: 5, alternative: false },
      { id: 106, plan_id: 1, action_id: 'c1', action_name: '胸部拉伸', phase: 'cooldown', sets: 1, reps: 1, duration: 30, order_index: 6, alternative: false },
    ]
  },
  {
    id: 2,
    user_id: 1,
    plan_name: '下肢力量与稳定性训练',
    status: 'active',
    generation_method: 'local',
    difficulty: 2,
    created_at: '2026-07-03T10:00:00Z',
    items: [
      { id: 201, plan_id: 2, action_id: 'w3', action_name: '腿部动态拉伸', phase: 'warmup', sets: 1, reps: 12, duration: 35, order_index: 1, alternative: false },
      { id: 202, plan_id: 2, action_id: 'm4', action_name: '徒手深蹲', phase: 'main', sets: 3, reps: 15, duration: 45, order_index: 2, alternative: false, notes: '膝盖不要超过脚尖' },
      { id: 203, plan_id: 2, action_id: 'm5', action_name: '弓步蹲', phase: 'main', sets: 3, reps: 12, duration: 50, order_index: 3, alternative: false },
      { id: 204, plan_id: 2, action_id: 'm6', action_name: '臀桥', phase: 'main', sets: 3, reps: 20, duration: 40, order_index: 4, alternative: false },
      { id: 205, plan_id: 2, action_id: 'c2', action_name: '腿部静态拉伸', phase: 'cooldown', sets: 1, reps: 1, duration: 40, order_index: 5, alternative: false },
      { id: 206, plan_id: 2, action_id: 'c3', action_name: '泡沫轴放松', phase: 'cooldown', sets: 1, reps: 1, duration: 60, order_index: 6, alternative: false },
    ]
  },
  {
    id: 3,
    user_id: 1,
    plan_name: '核心强化与柔韧提升',
    status: 'active',
    generation_method: 'deepseek',
    difficulty: 4,
    created_at: '2026-07-05T14:00:00Z',
    items: [
      { id: 301, plan_id: 3, action_id: 'w4', action_name: '躯干扭转', phase: 'warmup', sets: 1, reps: 10, duration: 20, order_index: 1, alternative: false },
      { id: 302, plan_id: 3, action_id: 'w5', action_name: '髋关节活动', phase: 'warmup', sets: 1, reps: 12, duration: 25, order_index: 2, alternative: false },
      { id: 303, plan_id: 3, action_id: 'm7', action_name: '悬垂举腿', phase: 'main', sets: 3, reps: 10, duration: 50, order_index: 3, alternative: false, notes: '控制下落速度' },
      { id: 304, plan_id: 3, action_id: 'm8', action_name: '俄罗斯转体', phase: 'main', sets: 3, reps: 20, duration: 40, order_index: 4, alternative: false },
      { id: 305, plan_id: 3, action_id: 'm9', action_name: '死虫式', phase: 'main', sets: 2, reps: 12, duration: 45, order_index: 5, alternative: false },
      { id: 306, plan_id: 3, action_id: 'm10', action_name: '侧平板支撑', phase: 'main', sets: 2, reps: 1, duration: 35, order_index: 6, alternative: false },
      { id: 307, plan_id: 3, action_id: 'c4', action_name: '婴儿式放松', phase: 'cooldown', sets: 1, reps: 1, duration: 45, order_index: 7, alternative: false },
    ]
  },
]

export const mockProgress: Record<number, {
  completed_item_ids: number[]
  items: Array<{ plan_item_id: number; sets_done: number; total_sets: number; latest_reps: number; latest_score: number }>
}> = {
  1: {
    completed_item_ids: [101, 102],
    items: [
      { plan_item_id: 101, sets_done: 1, total_sets: 1, latest_reps: 10, latest_score: 85 },
      { plan_item_id: 102, sets_done: 1, total_sets: 1, latest_reps: 15, latest_score: 92 },
      { plan_item_id: 103, sets_done: 0, total_sets: 3, latest_reps: 0, latest_score: 0 },
      { plan_item_id: 104, sets_done: 0, total_sets: 3, latest_reps: 0, latest_score: 0 },
      { plan_item_id: 105, sets_done: 0, total_sets: 2, latest_reps: 0, latest_score: 0 },
      { plan_item_id: 106, sets_done: 0, total_sets: 1, latest_reps: 0, latest_score: 0 },
    ]
  },
  2: {
    completed_item_ids: [],
    items: [
      { plan_item_id: 201, sets_done: 0, total_sets: 1, latest_reps: 0, latest_score: 0 },
      { plan_item_id: 202, sets_done: 0, total_sets: 3, latest_reps: 0, latest_score: 0 },
      { plan_item_id: 203, sets_done: 0, total_sets: 3, latest_reps: 0, latest_score: 0 },
      { plan_item_id: 204, sets_done: 0, total_sets: 3, latest_reps: 0, latest_score: 0 },
      { plan_item_id: 205, sets_done: 0, total_sets: 1, latest_reps: 0, latest_score: 0 },
      { plan_item_id: 206, sets_done: 0, total_sets: 1, latest_reps: 0, latest_score: 0 },
    ]
  },
  3: {
    completed_item_ids: [301, 302, 303, 304, 305, 306, 307],
    items: [
      { plan_item_id: 301, sets_done: 1, total_sets: 1, latest_reps: 10, latest_score: 90 },
      { plan_item_id: 302, sets_done: 1, total_sets: 1, latest_reps: 12, latest_score: 88 },
      { plan_item_id: 303, sets_done: 3, total_sets: 3, latest_reps: 10, latest_score: 78 },
      { plan_item_id: 304, sets_done: 3, total_sets: 3, latest_reps: 20, latest_score: 82 },
      { plan_item_id: 305, sets_done: 2, total_sets: 2, latest_reps: 12, latest_score: 95 },
      { plan_item_id: 306, sets_done: 2, total_sets: 2, latest_reps: 1, latest_score: 76 },
      { plan_item_id: 307, sets_done: 1, total_sets: 1, latest_reps: 1, latest_score: 94 },
    ]
  },
}
