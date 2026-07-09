export interface User {
  id: number
  username: string
  role: string
  phone?: string
  avatar?: string
  gender?: string
  is_active: boolean
  created_at?: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface FMSRecord {
  id: number
  user_id: number
  test_date: string
  balance_score: number
  flexibility_score: number
  upper_limb_score: number
  core_score: number
  symmetry_score: number
  overall_score: number
  risk_level: string
  radar_data?: any
  problem_tags?: any[]
}

export interface AssessmentRecord {
  id: number
  user_id: number
  test_date: string
  balance_score: number
  flexibility_score: number
  upper_limb_score: number
  core_score: number
  symmetry_score: number
  overall_score: number
  risk_level: string
  posture_problems?: any[]
  rom_analysis?: any[]
  asymmetry_findings?: any[]
  muscle_analysis?: any
  chart_data?: any
  suggestions?: string[]
  summary?: string
}

export interface PrescriptionItem {
  id: number
  action_name: string
  phase: string
  sets: number
  reps: number
  duration: number
  order_index: number
  difficulty: number
}

export interface Prescription {
  id: number
  user_id: number
  fms_record_id: number
  phase: number
  status: string
  difficulty: number
  created_at: string
  items: PrescriptionItem[]
}

export interface TrainingRecord {
  id: number
  user_id: number
  prescription_id: number
  start_time: string
  end_time?: string
  total_score?: number
  mode: string
}

export interface TrainingStats {
  total_sessions_7d: number
  total_sessions_30d: number
  average_score: number
  current_streak: number
}

export interface ActionItem {
  id: number
  name: string
  category: string
  difficulty: number
  description?: string
  video_url?: string
}

export interface LearnableAction {
  name: string
  action_id: string
  family: string
  family_name: string
  category: string
  subcategory: string
  difficulty: number
  intensity: string
  phases: string[]
  target_body_parts: string[]
  description: string
  steps: string[]
  cues: string[]
  views: string[]
  has_standard_angles: boolean
  common_errors: CommonError[]
}

export interface CommonError {
  name: string
  feedback: string
  joint: string
  threshold: number
}

export interface StandardAngles {
  [joint: string]: { min: number; max: number; optimal: number }
}

export interface KeyCheck {
  joint: string
  rule: string
  threshold: number
  unit: string
  direction: string
}

export interface LearnableActionDetail extends LearnableAction {
  standard_keypoints: {
    [view: string]: {
      description: string
      target_angles: StandardAngles
      key_checks: KeyCheck[]
    }
  }
  contraindications?: Record<string, number>
}

export interface AngleDiff {
  joint: string
  user: number | null
  standard_optimal: number
  standard_min?: number
  standard_max?: number
  standard_range: string
  diff: number | null
  status: 'good' | 'close' | 'warning' | 'bad' | 'unknown'
  percent?: number
}

export interface AngleHistoryEntry {
  frame: number
  angles: Record<string, number>
  score: number | null
}

export interface LearningFeedback {
  name: string
  joint: string
  severity: string
  message: string
  diff: number
}

export interface LearningComparison {
  type: 'comparison'
  frame: number
  user_angles: { [key: string]: number }
  standard_angles: StandardAngles
  diffs: AngleDiff[]
  feedbacks: LearningFeedback[]
  overall_score: number | null
  best_score: number
}

export interface LearningComplete {
  type: 'learning_complete'
  record_id: number | null
  total_score: number
  best_score: number
  duration: number
  frame_count: number
  summary: string[]
  feedback_counts: { [key: string]: number }
  angle_history: AngleHistoryEntry[]
  best_frame_kp?: number[][] | null
  best_frame_conf?: number[] | null
  best_frame_fw?: number
  best_frame_fh?: number
  best_frame_angles?: Record<string, number>
  best_frame_diffs?: AngleDiff[]
  best_frame_feedbacks?: LearningFeedback[]
  exercise_type?: string
  rep_count?: number
  hold_time?: number
  auto_triggered?: boolean
}

export type LearningWSMessage =
  | { type: 'session_ready'; action: LearnableAction; current_view: string; standard_angles: StandardAngles; key_checks: any[]; instruction: string }
  | LearningComparison
  | { type: 'view_switched'; view: string; standard_angles: StandardAngles; key_checks: any[] }
  | LearningComplete
  | { type: 'error'; message: string }

// ── Prescription v2 ─────────────────────────────────────────
export interface PlanItemV2 {
  id: number
  plan_id: number
  action_id: string
  action_name: string
  phase: string
  sets: number
  reps: number
  duration: number
  order_index: number
  alternative: boolean
  notes?: string
}

export interface PlanV2 {
  id: number
  user_id: number
  plan_name: string
  status: string
  generation_method: string
  difficulty: number
  created_at: string
  items: PlanItemV2[]
  overall_strategy?: string
  plan_meta?: {
    training_config?: {
      training_goal: string
      training_duration: number
      training_frequency: number
      user_level: number
      user_level_label: string
    }
  }
}

export interface PlanListResponse {
  plans: PlanV2[]
  total: number
}

export interface PlanResponse extends PlanV2 {}

export interface GenerateV2Request {
  assessment_record_id?: number
  fms_record_id?: number
  training_level?: string
  use_deepseek?: boolean
  training_goal?: string
  training_duration?: number
  training_frequency?: number
}

export interface GenerateV2Response {
  success: boolean
  plan?: PlanV2
  generation_method: string
  error_message: string
  fallback_used: boolean
}

export interface ActivateResponse {
  success: boolean
  message: string
  bridge_prescription_id?: number
}

export interface ActionLibAction {
  action_id: string
  name: string
  family: string
  family_name: string
  difficulty: number
  intensity: string
  target_muscles: string[]
  description: string
  phases: string[]
}

export interface ActionLibResponse {
  actions: ActionLibAction[]
  total: number
  families: string[]
}

// ── Coach ───────────────────────────────────────────────────
export interface CoachSummary {
  total_students: number
  active_today: number
  weekly_trainings: number
  avg_score: number
}

export interface ClassItem {
  id: number
  name: string
  description?: string
  student_count?: number
  created_at?: string
}

export interface ClassStudent {
  id: number
  username: string
  role: string
  is_active: boolean
  phone?: string
  avatar?: string
}

export interface StudentProfile {
  user: User
  fms_records: FMSRecord[]
  assessment_records: AssessmentRecord[]
  prescriptions: Prescription[]
  training_records: any[]
  badges: BadgeItem[]
  checkin_stats: any
  risk_level?: string
  streak_days?: number
  total_sessions?: number
}

// ── Admin ───────────────────────────────────────────────────
export interface AdminUser {
  id: number
  username: string
  role: string
  is_active: boolean
  created_at: string
  phone?: string
}

export interface SystemConfig {
  db_type: string
  host: string
  port: number
  model_path: string
  deepseek_model: string
}

export interface SystemLog {
  id: number
  user_id?: number
  username?: string
  action: string
  detail?: string
  ip_address?: string
  created_at: string
}

// ── Checkin / Badges ────────────────────────────────────────
export interface CheckinStatus {
  streak_days: number
  today_checked: boolean
  total_checkins: number
  total_sessions_7d?: number
  total_sessions_30d?: number
  average_score?: number
}

export interface BadgeItem {
  id: number
  badge_type: string
  name: string
  description: string
  earned_at: string
}
export interface MyClassInfo {
  class_id: number
  class_name: string
  description?: string
  invite_code?: string
  coach: { id: number; username: string; phone?: string }
  student_count: number
  created_at: string
}

export interface Conversation {
  partner_id: number
  partner_name: string
  partner_role: string
  last_message: string
  last_time: string
  unread_count: number
}

export interface MessageItem {
  id: number
  sender_id: number
  receiver_id: number
  content: string
  is_read: boolean
  related_type?: string
  related_id?: number
  created_at: string
}

export interface ChangeRequestItem {
  id: number
  plan_id: number
  plan_name: string
  student_id: number
  student_name: string
  coach_id?: number
  status: string
  original_snapshot?: string
  proposed_items?: string
  coach_items?: string
  coach_notes?: string
  student_notes?: string
  created_at: string
  updated_at?: string
}
