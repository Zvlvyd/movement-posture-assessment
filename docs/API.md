# API 接口文档

Base URL: `http://localhost:8002`

所有需要认证的接口在 Header 中携带：
```
Authorization: Bearer <access_token>
```

---

## 1. 认证

### POST /api/auth/register
注册新用户
```
Body: { "username": "str", "password": "str", "email": "str" }
Response 200: { "id": int, "username": "str", "role": "trainee", ... }
```

### POST /api/auth/login
登录获取 token
```
Body: { "username": "str", "password": "str" }
Response 200: { "access_token": "str", "token_type": "bearer" }
```

---

## 2. 体态评估（新系统）

### WebSocket /api/assessment/ws?token=<jwt>
实时评估 WebSocket 连接。客户端发送视频帧，服务端返回角度数据和最终报告。

**客户端 → 服务端消息：**

| type | 说明 | payload |
|------|------|---------|
| `start` | 开始评估 | `{}` |
| `frame` | 视频帧(base64) | `{ "data": "base64_jpeg" }` |
| `movement_done` | 当前动作完成 | `{}` |
| `finish` | 提前结束 | `{}` |

**服务端 → 客户端消息：**

| type | 说明 | payload |
|------|------|---------|
| `assessment_started` | 评估已开始 | `{ "total_movements": 5, "movements": [...] }` |
| `movement_ready` | 下一个动作准备 | `{ "index": 0, "name": "str", "instruction": "str" }` |
| `angles_update` | 实时角度数据 | `{ "angles": { "left_knee": 45.2, ... }, "plateau_detected": false }` |
| `movement_completed` | 动作完成 | `{ "index": 0, "rom_summary": {...} }` |
| `assessment_complete` | 评估完成 | `{ "record_id": 123, "overall_score": 85, "risk_level": "低风险", "dimensions": [...], "muscle_analysis": {...}, "suggestions": [...] }` |
| `error` | 错误 | `{ "message": "str" }` |

### POST /api/assessment/submit
提交姿态数据，返回评估结果（非实时模式）
```
Body: {
  "keypoints_front": [[x,y], ...],  // 17 个关键点
  "keypoints_side": [[x,y], ...],   // 可选
  "movement_frames": [[[x,y],...], ...]  // 可选，多帧关键点
}
Response 200: {
  "id": int,
  "overall_score": 85.5,
  "risk_level": "低风险",
  "balance_score": 80, "flexibility_score": 90,
  "upper_limb_score": 75, "core_score": 85, "symmetry_score": 92,
  "posture_problems": [...],
  "muscle_analysis": { "tight_muscles": [...], "weak_muscles": [...] },
  "rom_analysis": [...],
  "suggestions": [...],
  "summary": "str"
}
```

### GET /api/assessment/records
获取用户所有评估记录（列表，不含展开数据）
```
Response 200: [{
  "id": int, "test_date": "2026-06-25T...",
  "balance_score": 80, "flexibility_score": 90,
  "upper_limb_score": 75, "core_score": 85, "symmetry_score": 92,
  "overall_score": 85.5, "risk_level": "低风险"
}]
```

### GET /api/assessment/records/{id}
获取单条评估详情（含完整报告数据）
```
Response 200: 同上结构 + posture_problems + muscle_analysis + rom_analysis + suggestions + summary + chart_data
```

---

## 3. FMS 筛查（旧系统，兼容保留）

### WebSocket /api/fms/ws?token=<jwt>
实时 FMS 筛查 WebSocket。

**客户端 → 服务端：**

| type | 说明 |
|------|------|
| `start` | 开始筛查 |
| `frame` | 视频帧(base64) |
| `skip` | 跳过当前测试 |
| `finish` | 结束筛查 |

**服务端 → 客户端：**

| type | 说明 |
|------|------|
| `test_ready` | 测试准备就绪 |
| `score_update` | 实时评分更新 |
| `fms_complete` | 筛查完成，含总分/雷达图/问题标签 |

### POST /api/fms/screen
提交 FMS 筛查数据
```
Body: {
  "balance_duration": float,    // 单腿站立时长(秒)
  "flexibility_depth": float,   // 体前屈深度(cm)
  "flexibility_trunk": float,   // 躯干角
  "flexibility_arm": float,     // 手臂比率
  "upper_limb_distance": float, // 背后触肩距离(cm)
  "core_duration": float,       // 平板支撑时长(秒)
  "symmetry_left": float,       // 左侧值
  "symmetry_right": float       // 右侧值
}
```

### GET /api/fms/records
获取用户 FMS 记录列表

### GET /api/fms/records/{id}
获取单条 FMS 记录详情

---

## 4. 训练处方

### GET /api/prescription
获取用户当前训练处方
```
Response 200: [{
  "id": int, "fms_record_id": int, "assessment_record_id": int|null,
  "phase": int, "status": "ACTIVE"|"LOCKED"|"COMPLETED",
  "difficulty": int, "created_at": "datetime",
  "items": [{ "exercise_name": "str", "sets": 3, "reps": 12, "duration_sec": 60, ... }]
}]
```

---

## 5. 训练记录

### POST /api/training/log
记录训练完成

### GET /api/training/logs
获取训练历史

---

## 6. 学习模块

### GET /api/learning/courses
获取课程列表

### GET /api/learning/courses/{id}
获取课程详情

---

## 7. 打卡

### POST /api/checkin
每日打卡

### GET /api/checkin/badges
获取徽章列表

---

## 8. 记录统计

### GET /api/records/stats
获取用户统计数据

---

## 9. 管理

### GET /api/admin/users
用户管理（管理员）

---

## 通用说明

### 认证错误响应
```json
HTTP 401: { "detail": "Not authenticated" }
HTTP 403: { "detail": "Forbidden" }
```

### WebSocket 错误响应
服务端接受连接后，如验证失败，发送：
```json
{ "type": "error", "message": "令牌无效或已过期" }
```
随后关闭连接 (code 4001)。

### 跨域
CORS 已对以下源开放：
- http://localhost:5173
- http://localhost:5179
- http://10.244.112.152:5173
- http://10.244.112.152:5179