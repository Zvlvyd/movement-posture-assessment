# 修改日志

## 2026-06-26 — 模块优化集成：FMS 增强 + 实时训练重写 + 处方训练

详见 [docs/upgrades/2026-06-26-v2-module-optimization.md](upgrades/2026-06-26-v2-module-optimization.md)

### 新增功能
- 🆕 处方训练模块（多动作顺序执行 + 独立报告）
- 🆕 训练报告页（统计卡片、成绩进度条、错误历史）
- 🆕 FMS 报告增强（颜色编码进度条、风险预警 Alert、编号建议列表）
- 🆕 实时训练重写（7 动作自选、完成计数、错误追踪、模式区分反馈面板）
- 🆕 跳跃式开合跳 + 硬拉 2 个新动作（含 FSM 状态机）

### 算法优化
- 🔧 FMS 肩部评估：双手检测 + 加权距离（垂直 70%/水平 30%）
- 🔧 FMS 评分引擎：摇摆惩罚、臀降惩罚、自动建议生成
- 🔧 FMS 视频合并报告：生成 radar_data/suggestions/problem_tags

### 架构调整
- 📐 `TrainingRecord.prescription_id` 改为 nullable（支持自由训练）
- 📐 `TrainingWebSocketHandler` 开始支持 prescription_id=null
- 📐 MySQL training_record 表 ALTER COLUMN

### 修改文件（12 个）
| 文件 | 类型 |
|------|------|
| `models/fms/scoring.py` | 增强 |
| `backend/services/fms_service.py` | 增强 |
| `backend/services/training_service.py` | 增强 |
| `backend/database/models.py` | Schema |
| `backend/schemas/business.py` | Schema |
| `models/action_recognizer/squat_fsm.py` | 增强 |
| `frontend/src/pages/TrainingPage.tsx` | 重写 |
| `frontend/src/pages/FMSScreeningPage.tsx` | 增强 |
| `frontend/src/pages/FMSReportPage.tsx` | 增强 |
| `frontend/src/pages/TrainingReportPage.tsx` | 新建 |
| `frontend/src/pages/PrescriptionTrainingPage.tsx` | 新建 |
| `frontend/src/pages/PrescriptionTrainingReportPage.tsx` | 新建 |
| `frontend/src/App.tsx` | 路由 |
| `frontend/src/components/MainLayout.tsx` | 导航 |

## 2026-06-25 — WebSocket 连接修复 + FMS 模块恢复 + 数据库迁移

### 问题
1. FMS 筛查页面和体态评估页面的 WebSocket 连接失败
2. /api/prescription 返回 500 错误
3. 旧 FMS 模块文件被删除导致后端无法启动

### 修改清单

**backend/routers/assessment.py** (L79-103)
- WebSocket 端点改为先 ws.accept() 再验证 token
- 无效 token 返回 JSON 错误消息而非 HTTP 403
- 添加 try/except 包裹 handle_session

**backend/routers/fms.py** (L33-57)
- 同上：ws.accept() 前置，JSON 错误响应替代 HTTP 403

**backend/services/assessment_service.py** (L235-238)
- 移除 handle_session() 中的 await ws.accept()（已移至路由层）

**backend/services/fms_service.py** (L70)
- 移除 handle_session() 中的 await ws.accept()（已移至路由层）

**backend/main.py** (L21-23)
- 取消注释 fms 路由导入和注册

**models/fms/scoring.py** — 新建
- FMSScoringEngine 评分引擎 + Score 数据类

**models/fms/radar_report.py** — 新建
- RadarReport.generate() 雷达图数据生成

**models/fms/problem_tagger.py** — 新建
- ProblemTagger.tag() 问题标记

**frontend/src/pages/AssessmentPage.tsx**
- onclose 不再覆盖服务端错误消息

**数据库**
- prescription 表新增 assessment_record_id INT NULL
- 外键 fk_prescription_assessment → assessment_record(id)

### 关键设计决策
| 决策 | 理由 |
|------|------|
| WebSocket 先 accept 再验证 | 浏览器收到 HTTP 403 触发 onerror 且无法获取错误详情 |
| FMS 旧模块最小化重建 | 兼容旧 fms_service.py 接口，避免修改调用方 |
| assessment_record_id nullable | 兼容旧 FMS 数据，新评估填充此字段 |