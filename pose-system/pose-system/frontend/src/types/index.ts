export type UserRole = 'admin' | 'coach' | 'trainee';

export interface User {
  id: number; username: string; role: UserRole;
  phone?: string; avatar?: string; gender?: string;
  is_active: boolean; created_at?: string;
}

export interface TokenResponse {
  access_token: string; token_type: string; user: User;
}

// Radar chart data
export interface RadarChartData {
  labels: string[];
  values: number[];
}

export interface ProblemTag {
  name: string;
  description?: string;
  severity?: number;
}

// FMS (kept for backward compat)
export interface FMSRecord {
  id: number; user_id: number; test_date: string;
  balance_score: number; flexibility_score: number;
  upper_limb_score: number; core_score: number;
  symmetry_score: number; overall_score: number;
  risk_level: string;
  radar_data?: RadarChartData;
  problem_tags?: ProblemTag[];
}

// Assessment problem detail
export interface PostureProblem {
  flag: string; severity: string; weight: number;
}

export interface ROMAnalysisItem {
  joint: string; ratio: number; status: string; detail?: string;
}

export interface AsymmetryFinding {
  joint: string; diff_pct: number; side: string; severity?: string;
}

export interface MuscleAnalysis {
  tight_muscles: string[];
  weak_muscles: string[];
}

// Assessment (new)
export interface AssessmentRecord {
  id: number; user_id: number; test_date: string;
  balance_score: number; flexibility_score: number;
  upper_limb_score: number; core_score: number;
  symmetry_score: number; overall_score: number;
  risk_level: string;
  posture_problems?: PostureProblem[];
  rom_analysis?: ROMAnalysisItem[];
  asymmetry_findings?: AsymmetryFinding[];
  muscle_analysis?: MuscleAnalysis;
  chart_data?: RadarChartData;
  suggestions?: string[];
  summary?: string;
}

export interface PrescriptionItem {
  id: number; action_name: string; phase: string;
  sets: number; reps: number; duration: number;
  order_index: number; difficulty: number;
}

export interface Prescription {
  id: number; user_id: number; fms_record_id: number;
  phase: number; status: string; difficulty: number;
  created_at: string; items: PrescriptionItem[];
}

export interface TrainingRecord {
  id: number; user_id: number; prescription_id: number;
  start_time: string; end_time?: string;
  total_score?: number; mode: string;
}

export interface TrainingStats {
  total_sessions_7d: number; total_sessions_30d: number;
  average_score: number; current_streak: number;
}

export interface ActionItem {
  id: number; name: string; category: string;
  difficulty: number; description?: string;
  video_url?: string; target_body_parts?: string; thumbnail_url?: string;
}

// Common error type shared between LearnableAction and LearnableActionDetail
export interface CommonError {
  name: string; feedback: string; joint: string; threshold: number;
}

// Standard Learning types
export interface LearnableAction {
  name: string; action_id: string; family: string; family_name: string;
  category: string; subcategory: string; difficulty: number;
  intensity: string; phases: string[]; target_body_parts: string[];
  description: string; steps: string[]; cues: string[];
  views: string[]; has_standard_angles: boolean;
  common_errors: CommonError[];
  video_url?: string;
  thumbnail_url?: string;
  media?: Array<{ id: number; media_type: string; url: string; file_path: string; original_filename?: string }>;
}

export interface StandardAngles {
  [joint: string]: { min: number; max: number; optimal: number };
}

export interface KeyCheck {
  joint: string; rule: string; threshold: number;
  unit: string; direction: string;
}

export interface LearnableActionDetail {
  name: string; action_id: string; family: string; family_name: string;
  category: string; subcategory: string; difficulty: number;
  intensity: string; phases: string[]; target_body_parts: string[];
  description: string; steps: string[]; cues: string[];
  views: string[]; has_standard_angles: boolean;
  common_errors: CommonError[];
  standard_keypoints: {
    [view: string]: {
      description: string;
      target_angles: StandardAngles;
      key_checks: KeyCheck[];
    };
  };
  contraindications?: Record<string, number>;
  video_url?: string;
  thumbnail_url?: string;
  media?: Array<{ id: number; media_type: string; url: string; file_path: string; original_filename?: string }>;
}

export interface AngleDiff {
  joint: string; user: number | null; standard_optimal: number;
  standard_range: string; diff: number | null; status: 'good' | 'close' | 'warning' | 'bad' | 'unknown';
}

export interface LearningFeedback {
  name: string; joint: string; severity: string; message: string; diff: number;
}

export interface LearningComparison {
  type: 'comparison';
  frame: number;
  user_angles: { [key: string]: number };
  user_keypoints: number[][] | null;
  user_confidences: number[] | null;
  /** YOLO 推理时帧的实际宽度（用于前端坐标缩放） */
  frame_width: number;
  /** YOLO 推理时帧的实际高度（用于前端坐标缩放） */
  frame_height: number;
  standard_angles: StandardAngles;
  diffs: AngleDiff[];
  feedbacks: LearningFeedback[];
  overall_score: number | null;
  best_score: number;
  session_phase?: string;
  /** 动作类型: "rep" = 计数类, "hold" = 计时类 */
  exercise_type?: string;
  /** 动作次数计数（如弓步蹲、深蹲等），由 FSM 状态机计算 */
  rep_count?: number;
  /** 静态保持类动作的累计保持时长（秒） */
  hold_time?: number;
  /** FSM 当前状态名 */
  fsm_state?: string;
}

export interface BodyConfirmed {
  type: 'body_confirmed';
  message: string;
  session_phase: string;
}

export interface LearningComplete {
  type: 'learning_complete';
  record_id: number | null;
  total_score: number;
  best_score: number;
  duration: number;
  frame_count: number;
  /** 动作类型 */
  exercise_type?: string;
  /** 完成的总次数（如弓步蹲、深蹲等） */
  rep_count?: number;
  /** 有效动作帧数（得分 >= 50 的帧），用于计算综合分 */
  passing_frames?: number;
  /** 静态保持类动作的累计保持时长（秒） */
  hold_time?: number;
  summary: string[];
  feedback_counts: { [key: string]: number };
  angle_history: Array<{
    time: number;
    angles: { [key: string]: number };
    score?: number;
  }>;
  best_frame_kp?: number[][] | null;
  best_frame_conf?: number[] | null;
  best_frame_fw?: number;
  best_frame_fh?: number;
  best_frame_angles?: Record<string, number>;
  best_frame_diffs?: AngleDiff[];
  best_frame_feedbacks?: LearningFeedback[];
  auto_triggered: boolean;
}

// ── Prescription V2 ────────────────────────
export interface PlanItemV2 {
  id: number; plan_id: number;
  action_id: string; action_name: string;
  family_name?: string; category?: string;
  phase: string; sets: number; reps: number; duration_seconds: number;
  order_index: number; difficulty: number; intensity: string;
  notes?: string; is_substitution: boolean;
  steps?: string[]; cues?: string[]; display_type?: string; display_url?: string;
}

export interface PlanMeta {
  problems?: string[];
  severity?: string;
  generation_time?: number;
}

export interface PlanV2 {
  id: number; user_id: number;
  assessment_record_id?: number; fms_record_id?: number;
  plan_name: string; overall_strategy?: string;
  status: string; generation_method: string;
  template_version?: string;
  plan_meta?: PlanMeta;
  created_at?: string; activated_at?: string; completed_at?: string;
  items: PlanItemV2[];
}

export interface GenerateV2Request {
  assessment_record_id: number; fms_record_id: number;
  user_level?: number; force_local?: boolean;
}

export interface ActionLibItem {
  id: string; family: string; family_name: string; name: string;
  category: string; subcategory: string;
  difficulty: number; intensity: string;
  target_body_parts: string[]; phases: string[];
  default_sets: number; default_reps: number; default_duration_seconds: number;
  description: string; steps: string[]; cues: string[];
  display_type: string; display_url: string;
}

export interface ActionLibResponse {
  actions: ActionLibItem[];
  total: number;
  families: Array<{
    family: string; family_name: string; family_name_en: string;
    category: string; variant_count: number; difficulty_range: string;
  }>;
}

export type LearningWSMessage =
  | { type: 'session_ready'; action: LearnableAction; current_view: string; standard_angles: StandardAngles; key_checks: KeyCheck[]; instruction: string }
  | LearningComparison
  | BodyConfirmed
  | { type: 'view_switched'; view: string; standard_angles: StandardAngles; key_checks: KeyCheck[] }
  | LearningComplete
  | { type: 'error'; message: string };

// ── Admin Types ────────────────────────────
export interface AdminUser {
  id: number; username: string; role: UserRole;
  phone?: string; gender?: string; is_active: boolean;
  last_login_at?: string; last_active_at?: string;
  created_at?: string; deleted_at?: string;
}

export interface AdminUserListResponse {
  items: AdminUser[];
  total: number; page: number; page_size: number;
}

export interface AdminDashboard {
  total_users: number; active_users: number; deleted_users: number;
  role_distribution: Record<string, number>;
  dau: number; wau: number; mau: number;
  registration_trend: Array<{ date: string; count: number }>;
  dau_trend: Array<{ date: string; count: number }>;
  system_activity: {
    fms_screens: number; assessments: number;
    prescriptions: number; checkins: number;
  };
  api_stats: Array<{ action: string; count: number }>;
  error_rate: number;
}

export interface AdminUserDetail {
  id: number; username: string; role: string;
  phone?: string; gender?: string; is_active: boolean;
  last_login_at?: string; last_active_at?: string; created_at?: string;
  stats: {
    fms_records: number; assessments: number;
    prescriptions: number; checkins: number;
    streak_days: number;
    classes: Array<{ id: number; name: string }>;
  };
}

export interface SystemConfigMap {
  [key: string]: {
    value: string;
    description?: string;
    updated_at?: string;
  };
}

export interface StorageInfo {
  uploads_size_mb: number; uploads_size_bytes: number;
  model_files: Record<string, { size_mb: number; size_bytes: number }>;
}

export interface SystemLogEntry {
  id: number; user_id?: number; action: string;
  detail?: string; ip_address?: string; created_at: string;
}

// ── Coach Action Library Types ─────────────
export interface ActionMediaItem {
  id: number; media_type: string;
  url: string; file_path: string;
  original_filename?: string; file_size?: number; sort_order: number;
}

export interface UnifiedAction {
  source: 'db' | 'json' | 'custom';
  id?: number; json_id?: string;
  name: string; family?: string; family_name?: string;
  category?: string; subcategory?: string;
  difficulty: number; intensity?: string;
  target_body_parts: string[]; phases?: string[];
  description?: string; steps?: string[]; cues?: string[];
  contraindications?: Record<string, number>;
  video_url?: string; thumbnail_url?: string;
  media: ActionMediaItem[];
  is_custom: boolean;
  has_standard_angles: boolean;
  is_visible?: boolean;
  created_at?: string; updated_at?: string;
}

export interface UnifiedActionListResponse {
  items: UnifiedAction[];
  total: number; page: number; page_size: number;
  families: string[]; categories: string[];
}

// ── Student Class Types ─────────────────────
export interface CoachBrief {
  id: number;
  username: string;
  phone?: string;
}

export interface MyClassInfo {
  class_id: number;
  class_name: string;
  description?: string;
  invite_code?: string;
  coach: CoachBrief;
  student_count: number;
  created_at: string;
}

export interface MyClassListResponse {
  classes: MyClassInfo[];
}

export interface JoinClassResponse {
  message: string;
  class_info: MyClassInfo;
}

// ── Message Types ─────────────────────────
export interface Conversation {
  partner_id: number;
  partner_name: string;
  partner_role: string;
  last_message: string;
  last_time: string;
  unread_count: number;
}

export interface ConversationListResponse {
  conversations: Conversation[];
  total: number;
}

export interface MessageItem {
  id: number;
  sender_id: number;
  receiver_id: number;
  content: string;
  is_read: boolean;
  related_type?: string;
  related_id?: number;
  created_at: string;
}

export interface MessageWithResponse {
  partner: { id: number; username: string; role: string };
  messages: MessageItem[];
  total: number;
}

// ── Change Request Types ──────────────────
export interface ChangeRequestItem {
  id: number;
  plan_id: number;
  plan_name: string;
  student_id: number;
  student_name: string;
  coach_id?: number;
  status: string;
  original_snapshot?: string;
  proposed_items?: string;
  coach_items?: string;
  coach_notes?: string;
  student_notes?: string;
  created_at: string;
  updated_at?: string;
}

export interface ChangeRequestListResponse {
  requests: ChangeRequestItem[];
  total: number;
}
