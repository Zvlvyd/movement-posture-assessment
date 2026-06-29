export interface User {
  id: number; username: string; role: string;
  phone?: string; avatar?: string; gender?: string;
  is_active: boolean; created_at?: string;
}
export interface TokenResponse {
  access_token: string; token_type: string; user: User;
}
// FMS (kept for backward compat)
export interface FMSRecord {
  id: number; user_id: number; test_date: string;
  balance_score: number; flexibility_score: number;
  upper_limb_score: number; core_score: number;
  symmetry_score: number; overall_score: number;
  risk_level: string; radar_data?: any; problem_tags?: any[];
}
// Assessment (new)
export interface AssessmentRecord {
  id: number; user_id: number; test_date: string;
  balance_score: number; flexibility_score: number;
  upper_limb_score: number; core_score: number;
  symmetry_score: number; overall_score: number;
  risk_level: string;
  posture_problems?: any[]; rom_analysis?: any[];
  asymmetry_findings?: any[]; muscle_analysis?: any;
  chart_data?: any; suggestions?: string[]; summary?: string;
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

// Standard Learning types
export interface LearnableAction {
  name: string; action_id: string; family: string; family_name: string;
  category: string; subcategory: string; difficulty: number;
  intensity: string; phases: string[]; target_body_parts: string[];
  description: string; steps: string[]; cues: string[];
  views: string[]; has_standard_angles: boolean; common_errors: string[];
}

export interface StandardAngles {
  [joint: string]: { min: number; max: number; optimal: number };
}

export interface LearnableActionDetail {
  name: string; action_id: string; family: string; family_name: string;
  category: string; subcategory: string; difficulty: number;
  intensity: string; phases: string[]; target_body_parts: string[];
  description: string; steps: string[]; cues: string[];
  views: string[]; has_standard_angles: boolean;
  common_errors: Array<{
    name: string; feedback: string; joint: string; threshold: number;
  }>;
  standard_keypoints: {
    [view: string]: {
      description: string;
      target_angles: StandardAngles;
      key_checks: Array<{
        joint: string; rule: string; threshold: number;
        unit: string; direction: string;
      }>;
    };
  };
  contraindications?: Record<string, number>;
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
  standard_angles: StandardAngles;
  diffs: AngleDiff[];
  feedbacks: LearningFeedback[];
  overall_score: number | null;
  best_score: number;
}

export interface LearningComplete {
  type: 'learning_complete';
  record_id: number | null;
  total_score: number;
  best_score: number;
  duration: number;
  frame_count: number;
  summary: string[];
  feedback_counts: { [key: string]: number };
  angle_history: any[];
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
export interface PlanV2 {
  id: number; user_id: number;
  assessment_record_id?: number; fms_record_id?: number;
  plan_name: string; overall_strategy?: string;
  status: string; generation_method: string;
  template_version?: string; plan_meta?: any;
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
  actions: ActionLibItem[]; total: number; families: Array<{family:string; family_name:string; family_name_en:string; category:string; variant_count:number; difficulty_range:string}>;
}

export type LearningWSMessage =
  | { type: 'session_ready'; action: LearnableAction; current_view: string; standard_angles: StandardAngles; key_checks: any[]; instruction: string }
  | LearningComparison
  | { type: 'view_switched'; view: string; standard_angles: StandardAngles; key_checks: any[] }
  | LearningComplete
  | { type: 'error'; message: string };
