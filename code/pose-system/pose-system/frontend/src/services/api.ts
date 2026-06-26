import axios from "axios";
import type { TokenResponse, User, FMSRecord, AssessmentRecord, Prescription, TrainingRecord, TrainingStats, ActionItem } from "../types";

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
  /** 上传单个 FMS 动作的视频（test_index: 0-4），后端逐帧处理并返回该动作评分 */
  uploadSingleTestVideo: (testIndex: number, file: File, onProgress?: (pct: number) => void) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post<any>("/fms/upload-video/" + testIndex, formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 300000, // 5 分钟超时
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
      timeout: 300000, // 5 分钟超时
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
};

// Prescription
export const prescriptionApi = {
  generate: (fmsRecordId: number) => api.post<Prescription>("/prescription/generate/" + fmsRecordId).then(r => r.data),
  list: () => api.get<Prescription[]>("/prescription").then(r => r.data),
  get: (id: number) => api.get<Prescription>("/prescription/" + id).then(r => r.data),
};

// Training
export const trainingApi = {
  start: (data: { prescription_id: number; mode: string }) => api.post<TrainingRecord>("/training/start", data).then(r => r.data),
  end: (id: number, score?: number) => api.post<TrainingRecord>("/training/" + id + "/end", null, { params: { score } }).then(r => r.data),
  getRecords: () => api.get<TrainingRecord[]>("/training/records").then(r => r.data),
};

// Records & stats
export const recordsApi = {
  stats: () => api.get<TrainingStats>("/records/stats").then(r => r.data),
  history: (days = 30) => api.get<TrainingRecord[]>("/records/history", { params: { days } }).then(r => r.data),
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
