import axios, { type AxiosError } from 'axios'
import type {
  TokenResponse, User, FMSRecord, AssessmentRecord,
  Prescription, TrainingRecord, TrainingStats, ActionItem,
  LearnableAction, LearnableActionDetail,
  PlanV2, PlanListResponse, PlanResponse, GenerateV2Request, GenerateV2Response,
  ActivateResponse, ActionLibResponse, CoachSummary, ClassItem, ClassStudent,
  AdminUser, SystemConfig, SystemLog, CheckinStatus, BadgeItem,
  StudentProfile
} from '../types'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = 'Bearer ' + token
  return config
})

api.interceptors.response.use(
  r => r,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ── Auth ────────────────────────────────────────────────────
export const authApi = {
  register: (data: { username: string; password: string; phone?: string; gender?: string }) =>
    api.post<User>('/auth/register', data),
  login: (data: { username: string; password: string }) =>
    api.post<TokenResponse>('/auth/login', data).then(r => r.data),
  me: () => api.get<User>('/auth/me').then(r => r.data)
}

// ── User (profile, password, cycle config) ─────────────────
export const userApi = {
  updateProfile: (data: { username?: string; phone?: string; gender?: string }) =>
    api.put<User>('/auth/me', data).then(r => r.data),
  changePassword: (data: { old_password: string; new_password: string }) =>
    api.put('/auth/change-password', data).then(r => r.data),
  getCycleConfig: () => api.get('/auth/cycle-config').then(r => r.data),
  updateCycleConfig: (data: { cycle_length?: number; period_length?: number; last_period_date?: string }) =>
    api.put('/auth/cycle-config', data).then(r => r.data)
}

// ── FMS ─────────────────────────────────────────────────────
export const fmsApi = {
  submit: (data: any) => api.post<FMSRecord>('/fms/screen', data).then(r => r.data),
  getRecords: () => api.get<FMSRecord[]>('/fms/records').then(r => r.data),
  getRecord: (id: number) => api.get<FMSRecord>('/fms/records/' + id).then(r => r.data),
  deleteRecord: (id: number) => api.delete<{ success: boolean; message: string }>('/fms/records/' + id).then(r => r.data),
  uploadSingleTestVideo: (testIndex: number, file: File, onProgress?: (pct: number) => void) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<any>('/fms/upload-video/' + testIndex, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      }
    }).then(r => r.data)
  },
  combineResults: () => api.post<any>('/fms/upload-video-combine').then(r => r.data),
  uploadVideo: (file: File, onProgress?: (pct: number) => void) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<any>('/fms/upload-video', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      }
    }).then(r => r.data)
  }
}

// ── Assessment ──────────────────────────────────────────────
export const assessmentApi = {
  submit: (data: { keypoints_front: number[][]; keypoints_side?: number[][]; movement_frames?: number[][][] }) =>
    api.post<AssessmentRecord>('/assessment/submit', data).then(r => r.data),
  getRecords: () => api.get<AssessmentRecord[]>('/assessment/records').then(r => r.data),
  getRecord: (id: number) => api.get<AssessmentRecord>('/assessment/records/' + id).then(r => r.data),
  deleteRecord: (id: number) => api.delete<{ message: string }>('/assessment/records/' + id).then(r => r.data),
  generateReport: (id: number, regenerate: boolean = false) =>
    api.post<{ report: string; cached: boolean }>(
      `/assessment/records/${id}/generate-report`, null, { params: { regenerate } }
    ).then(r => r.data)
}

// ── Prescription v1 ─────────────────────────────────────────
export const prescriptionApi = {
  generate: (fmsRecordId: number) => api.post<Prescription>('/prescription/generate/' + fmsRecordId).then(r => r.data),
  list: () => api.get<Prescription[]>('/prescription').then(r => r.data),
  get: (id: number) => api.get<Prescription>('/prescription/' + id).then(r => r.data),
  generatePlans: (fmsRecordId: number) =>
    api.post('/prescription/generate-plans/' + fmsRecordId).then(r => r.data),
  activatePrescription: (fmsRecordId: number) =>
    api.post<Prescription>('/prescription/activate/' + fmsRecordId).then(r => r.data),
  posturePlan: (assessmentRecordId: number) =>
    api.post('/prescription/posture-plan/' + assessmentRecordId).then(r => r.data)
}

// ── Prescription v2 ─────────────────────────────────────────
export const prescriptionV2Api = {
  generate: (data: GenerateV2Request) =>
    api.post<GenerateV2Response>('/prescription-v2/generate', data).then(r => r.data),
  list: () =>
    api.get<PlanListResponse>('/prescription-v2/plans').then(r => r.data),
  get: (id: number) =>
    api.get<PlanResponse>('/prescription-v2/plans/' + id).then(r => r.data),
  delete: (id: number) =>
    api.delete<{ success: boolean; message: string }>('/prescription-v2/plans/' + id).then(r => r.data),
  activate: (id: number) =>
    api.post<ActivateResponse>('/prescription-v2/plans/' + id + '/activate').then(r => r.data),
  saveProgress: (data: { plan_id: number; plan_item_id: number; action_name: string; best_score: number; rep_count: number; hold_time_seconds: number; duration_seconds: number }) =>
    api.post<{ success: boolean; record_id: number }>('/prescription-v2/progress', data).then(r => r.data),
  getProgress: (planId: number) =>
    api.get<any>('/prescription-v2/plans/' + planId + '/progress').then(r => r.data),
  getActions: () =>
    api.get<ActionLibResponse>('/prescription-v2/actions').then(r => r.data)
}

// ── Records & Stats ─────────────────────────────────────────
export const recordsApi = {
  stats: async (): Promise<TrainingStats> => {
    try {
      const r = await api.get('/learning/stats').then(r => r.data)
      return {
        total_sessions_7d: r.total_sessions_7d || 0,
        total_sessions_30d: r.total_sessions_30d || 0,
        average_score: r.average_score || 0,
        current_streak: r.current_streak || 0
      }
    } catch {
      return { total_sessions_7d: 0, total_sessions_30d: 0, average_score: 0, current_streak: 0 }
    }
  },
  history: async (_days = 30) => {
    try { return await api.get('/learning/records').then(r => r.data) }
    catch { return [] }
  },
  delete: async (id: number) => {
    return api.delete(`/assessment/records/${id}`).then(r => r.data)
  }
}

// ── Check-in ────────────────────────────────────────────────
export const checkinApi = {
  checkin: () => api.post<any>('/checkin').then(r => r.data),
  status: () => api.get<any>('/checkin/status').then(r => r.data),
  badges: () => api.get<any>('/checkin/badges').then(r => r.data)
}

// ── Coach ───────────────────────────────────────────────────
export const coachApi = {
  summary: () => api.get<CoachSummary>('/coach/summary').then(r => r.data),
  classes: () => api.get<ClassItem[]>('/coach/classes').then(r => r.data),
  createClass: (name: string, description: string = '') =>
    api.post('/coach/classes', null, { params: { name, description } }).then(r => r.data),
  updateClass: (classId: number, data: { name?: string; description?: string }) =>
    api.put('/coach/classes/' + classId, data).then(r => r.data),
  deleteClass: (classId: number) =>
    api.delete('/coach/classes/' + classId).then(r => r.data),
  classStats: (id: number) => api.get<ClassItem>('/coach/classes/' + id + '/stats').then(r => r.data),
  classTrend: (id: number, days: number = 14) =>
    api.get('/coach/classes/' + id + '/trend', { params: { days } }).then(r => r.data),
  addStudent: (classId: number, studentId: number) =>
    api.post('/coach/classes/' + classId + '/students', null, { params: { student_id: studentId } }).then(r => r.data),
  removeStudent: (classId: number, studentId: number) =>
    api.delete(`/coach/classes/${classId}/students/${studentId}`).then(r => r.data),
  students: (classId?: number) =>
    api.get<ClassStudent[]>('/coach/students', { params: classId ? { class_id: classId } : {} }).then(r => r.data),
  availableTrainees: (keyword: string) =>
    api.get<AdminUser[]>('/coach/available-trainees', { params: { keyword } }).then(r => r.data),
  studentProfile: (id: number) =>
    api.get<StudentProfile>('/coach/students/' + id + '/profile').then(r => r.data),
  studentPlans: (studentId: number) =>
    api.get(`/coach/students/${studentId}/plans`).then(r => r.data),
  studentPlanDetail: (studentId: number, planId: number) =>
    api.get(`/coach/students/${studentId}/plans/${planId}`).then(r => r.data),
  deleteStudentPlan: (studentId: number, planId: number) =>
    api.delete(`/coach/students/${studentId}/plans/${planId}`).then(r => r.data),
  trainingRecords: (studentId: number, days: number = 30) =>
    api.get(`/coach/students/${studentId}/training-records`, { params: { days } }).then(r => r.data),
  trainingStats: (studentId: number) =>
    api.get(`/coach/students/${studentId}/training-stats`).then(r => r.data),
  listActions: (params?: Record<string, any>) =>
    api.get('/coach/actions', { params }).then(r => r.data),
  getAction: (id: string | number) =>
    api.get('/coach/actions/' + id).then(r => r.data),
  updateAction: (id: number, data: Record<string, unknown>) =>
    api.put('/coach/actions/' + id, data).then(r => r.data),
  createAction: (data: Record<string, unknown>) =>
    api.post('/coach/actions', data).then(r => r.data),
  uploadActionMedia: (actionId: number, file: File, mediaType: string, onProgress?: (pct: number) => void) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/coach/actions/${actionId}/upload-media`, formData, {
      params: { media_type: mediaType },
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 600000,
      onUploadProgress: e => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
      }
    }).then(r => r.data)
  },
  deleteActionMedia: (mediaId: number) =>
    api.delete('/coach/actions/media/' + mediaId).then(r => r.data),
  deleteAction: (id: number) =>
    api.delete('/coach/actions/' + id).then(r => r.data),
  setActionVisibility: (identifier: string, visible: boolean) =>
    api.put(`/coach/actions/${encodeURIComponent(identifier)}/visibility`, { visible }).then(r => r.data),
  regenerateCode: (classId: number) =>
    api.post(`/coach/classes/${classId}/regenerate-code`).then(r => r.data),
  listChangeRequests: (status?: string) =>
    api.get('/coach/change-requests', { params: status ? { status } : {} }).then(r => r.data),
  getChangeRequest: (id: number) =>
    api.get(`/coach/change-requests/${id}`).then(r => r.data),
  approveChangeRequest: (id: number) =>
    api.put(`/coach/change-requests/${id}/approve`).then(r => r.data),
  adjustChangeRequest: (id: number, items: any[], coachNotes = '') =>
    api.put(`/coach/change-requests/${id}/adjust`, { items, coach_notes: coachNotes }).then(r => r.data),
  rejectChangeRequest: (id: number, coachNotes: string) =>
    api.put(`/coach/change-requests/${id}/reject`, { coach_notes: coachNotes }).then(r => r.data)
}

// ── Messages ───────────────────────────────────────────────
export const messageApi = {
  conversations: (page = 1) => api.get('/messages', { params: { page } }).then(r => r.data),
  unreadCount: () => api.get('/messages/unread-count').then(r => r.data),
  getWith: (partnerId: number) => api.get(`/messages/with/${partnerId}`).then(r => r.data),
  send: (receiverId: number, content: string, relatedType?: string, relatedId?: number) =>
    api.post('/messages', null, {
      params: { receiver_id: receiverId, content, related_type: relatedType, related_id: relatedId }
    }).then(r => r.data),
  markRead: (messageId: number) => api.put(`/messages/${messageId}/read`).then(r => r.data)
}

// ── Student classes ────────────────────────────────────────
export const studentClassApi = {
  join: (inviteCode: string) => api.post('/class/join', { invite_code: inviteCode }).then(r => r.data),
  myClasses: () => api.get('/class/my-classes').then(r => r.data),
  classDetail: (id: number) => api.get(`/class/my-classes/${id}`).then(r => r.data),
  leaveClass: (id: number) => api.delete(`/class/my-classes/${id}/leave`).then(r => r.data)
}

// ── Plan editing ───────────────────────────────────────────
export const planEditApi = {
  edit: (planId: number, data: Record<string, unknown>) =>
    api.put(`/prescription-v2/plans/${planId}`, data).then(r => r.data),
  submitChange: (planId: number, notes = '') =>
    api.post(`/prescription-v2/plans/${planId}/submit-change`, { student_notes: notes }).then(r => r.data),
  myChangeRequests: () => api.get('/prescription-v2/change-requests').then(r => r.data)
}

// ── Admin ───────────────────────────────────────────────────
export const adminApi = {
  users: (params?: Record<string, any>) => api.get<AdminUser[] | any>('/admin/users', { params }).then(r => r.data),
  changeRole: (userId: number, role: string) =>
    api.put('/admin/users/' + userId + '/role', null, { params: { role } }).then(r => r.data),
  toggleStatus: (userId: number, isActive: boolean) =>
    api.put('/admin/users/' + userId + '/status', null, { params: { is_active: isActive } }).then(r => r.data),
  deleteUser: (userId: number) => api.delete('/admin/users/' + userId).then(r => r.data),
  restoreUser: (userId: number) => api.post(`/admin/users/${userId}/restore`).then(r => r.data),
  userDetail: (userId: number) => api.get('/admin/users/' + userId).then(r => r.data),
  batchOperation: (data: { user_ids: number[]; operation: string }) => api.post('/admin/users/batch', data).then(r => r.data),
  dashboard: () => api.get('/admin/dashboard').then(r => r.data),
  config: () => api.get<SystemConfig>('/admin/config').then(r => r.data),
  updateConfig: (data: Record<string, string>) => api.put('/admin/config', data).then(r => r.data),
  storage: () => api.get('/admin/storage').then(r => r.data),
  logs: (params: Record<string, any> | number = {}) =>
    api.get<SystemLog[] | any>('/admin/logs', { params: typeof params === 'number' ? { limit: params } : params }).then(r => r.data),
  exportUsers: () => api.get('/admin/export/users', { responseType: 'blob' }).then(r => r.data),
  exportLogs: (limit?: number) => api.get('/admin/export/logs', { params: { limit }, responseType: 'blob' }).then(r => r.data)
}

// ── Learning ────────────────────────────────────────────────
export const learningApi = {
  getActions: (category?: string) => api.get<ActionItem[]>('/learning/actions', { params: { category } }).then(r => r.data),
  getAction: (id: number) => api.get<ActionItem>('/learning/actions/' + id).then(r => r.data),
  getLearnable: () => api.get<LearnableAction[]>('/learning/learnable').then(r => r.data),
  getLearnableDetail: (name: string) =>
    api.get<LearnableActionDetail>('/learning/learnable/' + encodeURIComponent(name)).then(r => r.data),
  getViews: (name: string) =>
    api.get<{ name: string; views: string[] }>('/learning/views/' + encodeURIComponent(name)).then(r => r.data),
  getReport: (id: string | number) =>
    api.get('/learning/reports/' + encodeURIComponent(String(id))).then(r => r.data)
}

// ── WebSocket ───────────────────────────────────────────────
export function createLearningWS(token: string): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return new WebSocket(`${protocol}//${host}/api/learning/ws?token=${token}`)
}

export default api
