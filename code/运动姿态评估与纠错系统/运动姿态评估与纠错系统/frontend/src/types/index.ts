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
  video_url?: string;
}

// Standard Learning types
export interface LearnableAction {
  name: string; category: string; description: string;
  video_url: string; views: string[]; common_errors: string[];
}

export interface StandardAngles {
  [joint: string]: { min: number; max: number; optimal: number };
}

export interface LearnableActionDetail {
  name: string; category: string; description: string;
  video_url: string; views: string[];
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

export type LearningWSMessage =
  | { type: 'session_ready'; action: LearnableAction; current_view: string; standard_angles: StandardAngles; key_checks: any[]; instruction: string }
  | LearningComparison
  | { type: 'view_switched'; view: string; standard_angles: StandardAngles; key_checks: any[] }
  | LearningComplete
  | { type: 'error'; message: string };
