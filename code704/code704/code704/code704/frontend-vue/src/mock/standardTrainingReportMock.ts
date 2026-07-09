/**
 * 标准动作学习训练完成报告 — Mock 数据
 */
export interface ReportSummary {
  text: string
  tags: string[]
  mainIssue: string
  nextSuggestion: string
}

export interface ReportMetric {
  name: string
  value: number | string
  unit?: string
  icon: string
  color: string
}

export interface BestPoseMetrics {
  quality: number
  stability: number
  standard: number
  keyAngles: Array<{ joint: string; value: number; status: 'good' | 'close' | 'warning' | 'bad' }>
  detailedAngles: Array<{ joint: string; user: number; standard: number; diff: number; status: 'good' | 'close' | 'warning' | 'bad' }>
  skeletonImage?: string
  frameTip?: string
}

export interface RadarDimension { name: string; value: number; max: number }
export interface TrendPoint { index: number; score: number; standard: number; stability: number }
export interface SuggestionItem { title: string; desc: string; icon: string; color: string }
export interface SuggestionGroup { title: string; icon: string; color: string; items: SuggestionItem[] }

export interface StandardTrainingReport {
  id: number | string
  actionName: string
  completedAt: string
  bestScore: number
  encouragement: string
  metrics: ReportMetric[]
  aiAnalysis: ReportSummary
  bestPose: BestPoseMetrics
  radarDimensions: RadarDimension[]
  trendData: TrendPoint[]
  suggestions: SuggestionGroup[]
}

const STATUS_COLORS: Record<string, string> = {
  good: '#6366f1', close: '#d97706', warning: '#d97706', bad: '#ef4444'
}
export function getStatusColor(status: string): string {
  return STATUS_COLORS[status] || '#94a3b8'
}

export const mockStandardTrainingReport: StandardTrainingReport = {
  id: 'sr-20260706-001',
  actionName: '标准俯卧撑',
  completedAt: '2026-07-07 10:30',
  bestScore: 100,
  encouragement: '肘、肩、髋、踝四个关键关节角度与标准参考值吻合，躯干直线保持稳定，未检测到塌腰、耸肩等代偿问题。',
  metrics: [
    { name: '总评分', value: 100, unit: '分', icon: 'TrophyOutline', color: '#7c3aed' },
    { name: '动作质量', value: 100, unit: '%', icon: 'ShieldCheckmarkOutline', color: '#a78bfa' },
    { name: '用时', value: '3分25秒', unit: '', icon: 'TimeOutline', color: '#a78bfa' },
    { name: '比对帧数', value: 412, unit: '帧', icon: 'VideocamOutline', color: '#a78bfa' }
  ],
  aiAnalysis: {
    text: '系统逐帧比对了用户动作与标准动作的肘、肩、髋、踝四个关节角度，偏差均在 ±5° 以内，躯干直线保持稳定，下沉与推起节奏均匀。',
    tags: ['肘肩髋踝四关节达标', '躯干直线稳定', '节奏均匀', '未检测到代偿'],
    mainIssue: '无明显问题',
    nextSuggestion: '这次动作已达到标准要求，后续可尝试窄距变式，检验不同支撑宽度下关节对位是否依然稳定。'
  },
  bestPose: {
    quality: 100, stability: 96, standard: 98,
    keyAngles: [
      { joint: '左肘角度', value: 48, status: 'good' },
      { joint: '右肘角度', value: 50, status: 'good' },
      { joint: '躯干直线', value: 96, status: 'good' },
    ],
    detailedAngles: [
      { joint: '左肘角度', user: 48, standard: 50, diff: -2, status: 'good' },
      { joint: '右肘角度', user: 50, standard: 50, diff: 0, status: 'good' },
      { joint: '肩-髋-踝连线', user: 96, standard: 92, diff: 4, status: 'good' },
      { joint: '髋部高度', user: 93, standard: 88, diff: 5, status: 'good' },
      { joint: '头部中立', user: 94, standard: 90, diff: 4, status: 'good' },
      { joint: '手掌间距', user: 86, standard: 85, diff: 1, status: 'good' },
    ],
    skeletonImage: '',
    frameTip: 'AI 自动抓拍最佳帧序列'
  },
  radarDimensions: [
    { name: '标准度', value: 98, max: 100 },
    { name: '稳定性', value: 96, max: 100 },
    { name: '控制力', value: 92, max: 100 },
    { name: '协调性', value: 90, max: 100 },
    { name: '完成度', value: 100, max: 100 },
  ],
  trendData: [
    { index: 1, score: 68, standard: 75, stability: 70 },
    { index: 2, score: 74, standard: 78, stability: 72 },
    { index: 3, score: 80, standard: 82, stability: 76 },
    { index: 4, score: 84, standard: 87, stability: 80 },
    { index: 5, score: 88, standard: 90, stability: 84 },
    { index: 6, score: 92, standard: 93, stability: 88 },
    { index: 7, score: 95, standard: 95, stability: 91 },
    { index: 8, score: 97, standard: 96, stability: 93 },
    { index: 9, score: 98, standard: 97, stability: 95 },
    { index: 10, score: 100, standard: 98, stability: 96 },
  ],
  suggestions: [
    {
      title: '优势', icon: 'ThumbsUpOutline', color: '#7c3aed',
      items: [
        { title: '关节角度准', desc: '肘、肩、髋、踝四个关键关节与标准偏差均在 ±5° 以内。', icon: 'BodyOutline', color: '#7c3aed' },
        { title: '身体稳定', desc: '躯干从头到尾保持直线，核心收紧，无塌腰或撅臀。', icon: 'PulseOutline', color: '#7c3aed' },
        { title: '节奏均匀', desc: '下沉 2 秒、推起 1 秒，全程速率稳定。', icon: 'CheckmarkCircleOutline', color: '#7c3aed' },
      ]
    },
    {
      title: '风险判断', icon: 'WarningOutline', color: '#d97706',
      items: [
        { title: '推起末段未完全锁定', desc: '最后一段肘关节打开角度不足，长期可能导致关节受力不均。', icon: 'FitnessOutline', color: '#d97706' },
      ]
    },
    {
      title: '下一步策略', icon: 'BulbOutline', color: '#0d9488',
      items: [
        { title: '慢速验证', desc: '尝试 3 秒慢速下沉，检查低速下关节轨迹是否依然吻合标准。', icon: 'TrendingUpOutline', color: '#0d9488' },
        { title: '变式测试', desc: '窄距或宽距各执行一次，检验不同支撑面下动作是否稳定。', icon: 'SchoolOutline', color: '#0d9488' },
      ]
    }
  ]
}

export function fetchMockStandardTrainingReport(id?: string | string[]): Promise<StandardTrainingReport> {
  return new Promise(resolve => {
    setTimeout(() => resolve({ ...mockStandardTrainingReport, id: id ?? mockStandardTrainingReport.id }), 500)
  })
}
