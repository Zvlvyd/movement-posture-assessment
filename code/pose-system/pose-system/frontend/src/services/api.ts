import axios from "axios";
import type { TokenResponse, User, FMSRecord, AssessmentRecord, ActionItem } from "../types";

const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = "Bearer " + token;
  return config;
});

api.interceptors.response.use(r => r, (error) => {
  if (error.response?.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "/login";
  }
  return Promise.reject(error);
});

// ── Coach ──────────────────────────────────────────────────
export const coachApi = {
  summary: () => api.get("/coach/summary").then(r => r.data),
  classes: () => api.get("/coach/classes").then(r => r.data),
  createClass: (name: string, description: string = "") =>
    api.post("/coach/classes", null, { params: { name, description } }).then(r => r.data),
  updateClass: (classId: number, data: { name?: string; description?: string }) =>
    api.put(`/coach/classes/${classId}`, data).then(r => r.data),
  deleteClass: (classId: number) =>
    api.delete(`/coach/classes/${classId}`).then(r => r.data),
  classStats: (id: number) => api.get(`/coach/classes/${id}/stats`).then(r => r.data),
  classTrend: (id: number, days: number = 14) =>
    api.get(`/coach/classes/${id}/trend`, { params: { days } }).then(r => r.data),
  addStudent: (classId: number, studentId: number) =>
    api.post(`/coach/classes/${classId}/students`, null, { params: { student_id: studentId } }).then(r => r.data),
  removeStudent: (classId: number, studentId: number) =>
    api.delete(`/coach/classes/${classId}/students/${studentId}`).then(r => r.data),
  students: (classId?: number) =>
    api.get("/coach/students", { params: classId ? { class_id: classId } : {} }).then(r => r.data),
  availableTrainees: (keyword: string) =>
    api.get("/coach/available-trainees", { params: { keyword } }).then(r => r.data),
  studentProfile: (id: number) => api.get(`/coach/students/${id}/profile`).then(r => r.data),
  // Student prescription management
  studentPlans: (studentId: number) =>
    api.get(`/coach/students/${studentId}/plans`).then(r => r.data),
  studentPlanDetail: (studentId: number, planId: number) =>
    api.get(`/coach/students/${studentId}/plans/${planId}`).then(r => r.data),
  deleteStudentPlan: (studentId: number, planId: number) =>
    api.delete(`/coach/students/${studentId}/plans/${planId}`).then(r => r.data),
  // Action library management
  listActions: (params?: Record<string, any>) =>
    api.get("/coach/actions", { params }).then(r => r.data),
  getAction: (id: string | number) =>
    api.get(`/coach/actions/${id}`).then(r => r.data),
  updateAction: (id: number, data: Record<string, unknown>) =>
    api.put(`/coach/actions/${id}`, data).then(r => r.data),
  createAction: (data: Record<string, unknown>) =>
    api.post("/coach/actions", data).then(r => r.data),
  uploadActionMedia: (actionId: number, file: File, mediaType: string, onProgress?: (pct: number) => void) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post(`/coach/actions/${actionId}/upload-media`, fd, {
      params: { media_type: mediaType },
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 600000,
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
      },
    }).then(r => r.data);
  },
  deleteActionMedia: (mediaId: number) =>
    api.delete(`/coach/actions/media/${mediaId}`).then(r => r.data),
};

// ── Admin ──────────────────────────────────────────────────
export const adminApi = {
  users: (params?: Record<string, any>) =>
    api.get("/admin/users", { params }).then(r => r.data),
  changeRole: (userId: number, role: string) =>
    api.put(`/admin/users/${userId}/role`, null, { params: { role } }).then(r => r.data),
  toggleStatus: (userId: number, isActive: boolean) =>
    api.put(`/admin/users/${userId}/status`, null, { params: { is_active: isActive } }).then(r => r.data),
  deleteUser: (userId: number) =>
    api.delete(`/admin/users/${userId}`).then(r => r.data),
  restoreUser: (userId: number) =>
    api.post(`/admin/users/${userId}/restore`).then(r => r.data),
  userDetail: (userId: number) =>
    api.get(`/admin/users/${userId}`).then(r => r.data),
  batchOperation: (data: { user_ids: number[]; operation: string }) =>
    api.post("/admin/users/batch", data).then(r => r.data),
  dashboard: () => api.get("/admin/dashboard").then(r => r.data),
  config: () => api.get("/admin/config").then(r => r.data),
  updateConfig: (data: Record<string, string>) =>
    api.put("/admin/config", data).then(r => r.data),
  storage: () => api.get("/admin/storage").then(r => r.data),
  logs: (params?: Record<string, any>) =>
    api.get("/admin/logs", { params }).then(r => r.data),
  exportUsers: () =>
    api.get("/admin/export/users", { responseType: "blob" }).then(r => r.data),
  exportLogs: (limit?: number) =>
    api.get("/admin/export/logs", { params: { limit }, responseType: "blob" }).then(r => r.data),
};

// ── User (profile, password, cycle config) ─────────────────
export const userApi = {
  updateProfile: (data: { username?: string; phone?: string; gender?: string }) =>
    api.put<User>("/auth/me", data).then(r => r.data),
  changePassword: (data: { old_password: string; new_password: string }) =>
    api.put("/auth/change-password", data).then(r => r.data),
  getCycleConfig: () => api.get("/auth/cycle-config").then(r => r.data),
  updateCycleConfig: (data: { cycle_length?: number; period_length?: number; last_period_date?: string }) =>
    api.put("/auth/cycle-config", data).then(r => r.data),
};

// Auth
export const authApi = {
  register: (data: { username: string; password: string; phone?: string; gender?: string }) =>
    api.post<User>("/auth/register", data),
  login: (data: { username: string; password: string }) =>
    api.post<TokenResponse>("/auth/login", data).then(r => r.data),
  me: () => api.get<User>("/auth/me").then(r => r.data),
};

// FMS (kept for backward compat)
export const fmsApi = {
  submit: (data: any) => api.post<FMSRecord>("/fms/screen", data).then(r => r.data),
  getRecords: () => api.get<FMSRecord[]>("/fms/records").then(r => r.data),
  getRecord: (id: number) => api.get<FMSRecord>("/fms/records/" + id).then(r => r.data),
  deleteRecord: (id: number) => api.delete<{ success: boolean; message: string }>("/fms/records/" + id).then(r => r.data),
  /** 上传单个 FMS 动作的视频（test_index: 0-4），后端逐帧处理并返回该动作评分 */
  uploadSingleTestVideo: (testIndex: number, file: File, onProgress?: (pct: number) => void) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post<any>("/fms/upload-video/" + testIndex, formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 600000, // 10 分钟超时
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    }).then(r => r.data);
  },
  /** 合并所有已上传的单个动作评分，生成最终 FMS 报告 */
  combineResults: () => api.post<any>("/fms/upload-video-combine").then(r => r.data),
  /** 上传 FMS 筛查视频（旧版，上传包含5个动作的完整视频） */
  uploadVideo: (file: File, onProgress?: (pct: number) => void) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post<any>("/fms/upload-video", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 600000, // 10 分钟超时
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    }).then(r => r.data);
  },
};

// Assessment (new)
export const assessmentApi = {
  submit: (data: { keypoints_front: number[][]; keypoints_side?: number[][]; movement_frames?: number[][][] }) =>
    api.post<AssessmentRecord>("/assessment/submit", data).then(r => r.data),
  getRecords: () => api.get<AssessmentRecord[]>("/assessment/records").then(r => r.data),
  getRecord: (id: number) => api.get<AssessmentRecord>("/assessment/records/" + id).then(r => r.data),
  deleteRecord: (id: number) => api.delete<{ success: boolean; message: string }>("/assessment/records/" + id).then(r => r.data),
  generateReport: (id: number, regenerate: boolean = false) =>
    api.post<{ report: string; cached: boolean }>(
      `/assessment/records/${id}/generate-report`, null, { params: { regenerate } }
    ).then(r => r.data),
};

// Prescription V2 (new)
export const prescriptionV2Api = {
  generate: (data: import("../types").GenerateV2Request) =>
    api.post<{success:boolean; plan?:import("../types").PlanV2; generation_method:string; error_message:string; fallback_used:boolean}>(
      "/prescription-v2/generate", data
    ).then(r => r.data),
  list: () =>
    api.get<{plans:import("../types").PlanV2[]; total:number}>("/prescription-v2/plans").then(r => r.data),
  get: (id: number) =>
    api.get<import("../types").PlanV2>("/prescription-v2/plans/" + id).then(r => r.data),
  delete: (id: number) =>
    api.delete<{success: boolean; message: string}>("/prescription-v2/plans/" + id).then(r => r.data),
  activate: (id: number) =>
    api.post<{success:boolean; message:string; bridge_prescription_id?:number}>(
      "/prescription-v2/plans/" + id + "/activate"
    ).then(r => r.data),
  getActions: () =>
    api.get<import("../types").ActionLibResponse>("/prescription-v2/actions").then(r => r.data),
  // Test helpers (mock record creation)
  mockAssessment: (data: { problems: string[]; severities: Record<string, string> }) =>
    api.post<{success: boolean; record_id: number; overall_score: number; risk_level: string}>(
      "/prescription-v2/test/mock-assessment", data
    ).then(r => r.data),
  mockFMS: (data: Record<string, number>) =>
    api.post<{success: boolean; record_id: number; overall_score: number; risk_level: string}>(
      "/prescription-v2/test/mock-fms", data
    ).then(r => r.data),
  mockBoth: (data: { assessment: { problems: string[]; severities: Record<string, string> }; fms: Record<string, number> }) =>
    api.post<{success: boolean; assessment_record_id: number; fms_record_id: number}>(
      "/prescription-v2/test/mock-both", data
    ).then(r => r.data),
};

// Records & stats (training module removed — stub)
export const recordsApi = {
  stats: async () => ({ total_sessions_7d: 0, total_sessions_30d: 0, average_score: 0, current_streak: 0 }),
  history: async (_days = 30) => [],
};

// Check-in
export const checkinApi = {
  checkin: () => api.post("/checkin").then(r => r.data),
  status: () => api.get("/checkin/status").then(r => r.data),
  badges: () => api.get("/checkin/badges").then(r => r.data),
};

// Learning
export const learningApi = {
  getActions: (category?: string) => api.get<ActionItem[]>("/learning/actions", { params: { category } }).then(r => r.data),
  getAction: (id: number) => api.get<ActionItem>("/learning/actions/" + id).then(r => r.data),
  // Standard learning (new)
  getLearnable: () => api.get<import("../types").LearnableAction[]>("/learning/learnable").then(r => r.data),
  getLearnableDetail: (name: string) => api.get<import("../types").LearnableActionDetail>("/learning/learnable/" + encodeURIComponent(name)).then(r => r.data),
  getViews: (name: string) => api.get<{name: string; views: string[]}>("/learning/views/" + encodeURIComponent(name)).then(r => r.data),
};

// Learning WebSocket
export function createLearningWS(token: string): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return new WebSocket(`${protocol}//${host}/api/learning/ws?token=${token}`);
}
