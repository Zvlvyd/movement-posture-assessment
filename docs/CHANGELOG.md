# 修改日志

## 2026-06-30 — 标准学习模块重构：58 动作 + 10 家族全量接入

### 后端

#### 标准学习 — 从 5 动作扩展到 58 动作 (10 家族)
- 🆕 `UnifiedActionLoader` 合并 `action_library.json` (58动作/10家族) 与 `standard_actions.json` (标准角度数据)
- 🆕 `/api/learning/learnable` 返回全部 58 动作，含 `family`/`family_name`/`steps`/`cues`/`has_standard_angles`
- 🆕 `/api/learning/learnable/{name}` 详情新增家族、步骤、要领、目标部位、禁忌症字段
- 🔧 `RealtimeLearningService` 无标准角度的动作优雅降级（正常显示骨骼关键点，不做角度差异分析）
- 🔧 `StandardActionLoader` 类移除，全部替换为 `UnifiedActionLoader`

### 前端

#### LearningPage 重构
- 🆕 家族筛选器（10 个中文家族名：俯卧撑/深蹲/拉伸/核心抗伸展…）
- 🆕 动作卡片增强：家族名标签、强度标签（低/中/高）、`has_standard_angles` 实时对比徽章
- 🆕 详情 Modal：动作步骤（编号列表）、动作要领（标签云）、目标部位、适用训练阶段
- 🔧 分类筛选改为动态提取（从 DB + JSON 数据源汇总唯一值）
- 🔧 搜索支持动作名称、描述、家族名、目标部位全文搜索

#### 类型定义更新
- 🆕 `LearnableAction`/`LearnableActionDetail` 扩展：`family`/`family_name`/`subcategory`/`intensity`/`phases`/`steps`/`cues`/`has_standard_angles`
- 🆕 `ActionItem` 新增 `target_body_parts`/`thumbnail_url`


## 2026-06-27 — Bug 修复：FMS 骨架冻结 + 训练误计数 + 多机浏览器访问

### Bug 修复

#### FMS 实时筛查 — 骨架首次识别后冻结不动
- 🐛 `_eval_balance` 平衡测试 1 秒后自动标记完成 → 后端跳过后续所有帧 → 骨架冻结
- 🔧 移除 `dur > 1` 自动完成逻辑，改为用户手动点击"下一步"结束测试并计分
- 🔧 帧处理跳过条件从 `("done", "skipped", "awaiting_user")` 收紧为仅 `"awaiting_user"`
- 🔧 评估逻辑加 `if test["status"] in ("ready", "running")` 保护，已完成/跳过仍返回关键点供骨架持续更新
- 🔧 `_eval_plank` 平板支撑同步去除自动结束，改为手动结束
- 🔧 `next_test` 消息增强：当用户点击"下一步"时自动结算当前运行中测试的分数

#### 实时训练 — 深蹲次数无动作时疯狂增长
- 🐛 FSM 状态机 7 个动作均缺少 `complete → 初始状态` 回路，到达后永远卡住
- 🐛 前端每帧检测 `fsm_state === 'complete'` 直接 `count++`，卡住后每帧都累加
- 🔧 `squat_fsm.py`：为深蹲/弓步蹲/俯卧撑/平板支撑/肩推/开合跳/硬拉均添加回路转换
  - 以深蹲为例：`complete → standing` 需 `knee < 140°` 才触发，站立不动（150-175°）不会误触发
- 🔧 `TrainingPage.tsx`：计数改为 `prevFsmStateRef` 检测状态变化，仅在首次进入 `complete` 时 +1

### 多机浏览器访问

- 🆕 `.env` 文件支持：内置简易加载器，无需安装 `python-dotenv`
- 🆕 `CORS_ALLOW_LAN=true` 自动探测本机局域网 IP 加入 CORS 白名单
- 🆕 `CORS_EXTRA_ORIGINS` 手动追加额外来源（逗号分隔）
- 🆕 Vite 开启 HTTPS（自签名证书 `cert.key`/`cert.crt`），解决 `getUserMedia` 摄像头限制
- 🆕 后端启动时打印本机 IP、CORS 白名单、数据库连接信息，便于调试
- 🆕 `.env.example` 环境变量模板
- 📐 `CORS_ORIGINS` 从固定列表改为 `@property` 动态计算

### 修改文件（6 个）

| 文件 | 类型 |
|------|------|
| `config/settings.py` | 增强（.env 加载 + CORS 动态计算） |
| `backend/main.py` | 增强（启动配置打印） |
| `backend/services/fms_service.py` | Bug 修复（5 处改动） |
| `models/action_recognizer/squat_fsm.py` | Bug 修复（7 个 FSM 回路） |
| `frontend/src/pages/TrainingPage.tsx` | Bug 修复（状态变化计数） |
| `frontend/vite.config.ts` | 增强（HTTPS） |

### 新增文件（4 个）

| 文件 | 用途 |
|------|------|
| `.env` | 运行环境配置（CORS_ALLOW_LAN=true） |
| `.env.example` | 环境变量模板 |
| `frontend/cert.key` + `frontend/cert.crt` | Vite HTTPS 自签名证书 |
| `docs/第一次检查-技术文档.md` + `.docx` | 第一次检查技术文档 |

---

## 2026-06-27 — 管理员/教练登录 + 学员档案 + 体态评估 AI 报告

### 新增功能
- 🆕 管理员登录（默认账号 `admin/admin123`，角色感知跳转 → `/admin`）
- 🆕 教练登录（默认账号 `coach/coach123`，角色感知跳转 → `/coach`）
- 🆕 登录页数学验证码（可复用组件 `MathCaptcha`）
- 🆕 登录页首次使用引导（"开始运动能力评估"）
- 🆕 种子账号自动创建（后端启动时幂等生成）
- 🆕 班级管理添加学员改用下拉选择（班级名称 + 学员搜索）
- 🆕 学员完整档案页 `StudentDetailPage`（FMS + 体态评估 + 处方 + 训练记录 + 徽章）
- 🆕 教练管理页学员名点击可进入档案页
- 🆕 DeepSeek API 体态评估 AI 报告生成（`deepseek-v4-pro`）
- 🆕 体态评估报告页 AI 报告卡片（生成/缓存/重新生成）

### 模块化重构
- 📐 提取 `MathCaptcha` 可复用验证码组件（`components/MathCaptcha.tsx`）
- 📐 提取 `useRoleNavigate` 角色感知导航 Hook（`hooks/useRoleNavigate.ts`）
- 📐 提取 `AiReportSection` AI 报告独立组件（`components/AiReportSection.tsx`）
- 📐 提取 `deepseek_service` DeepSeek 调用服务（`backend/services/deepseek_service.py`）
- 📐 `CoachPage` 从双 return 重构为单 return + 条件渲染（Modal 在两种视图下均可触发）

### 后端变更
- 🔧 `config/settings.py` — 新增种子账号 + DeepSeek API 配置
- 🔧 `backend/database/seed.py` — 新增 `seed_users()` 幂等种子函数
- 🔧 `backend/main.py` — 启动时调用 `seed_users()`
- 🔧 `backend/routers/coach.py` — 教练路由增加 ADMIN 权限、新增学员档案、学员搜索接口
- 🔧 `backend/routers/assessment.py` — 新增 `POST /records/{id}/generate-report` AI 报告端点
- 🔧 `requirements.txt` — 新增 `httpx>=0.27.0`

### 前端变更
- 🔧 `LoginPage.tsx` — 角色感知跳转 + 验证码 + 首次引导（使用独立模块）
- 🔧 `App.tsx` — `RoleIndexRedirect` 复用 `roleToPath` 工具函数、新增 `/coach/student/:id` 路由
- 🔧 `CoachPage.tsx` — 添加学员弹窗改用 Select 下拉 + 学员搜索、学员名可点击
- 🔧 `AssessmentReportPage.tsx` — 引入 `AiReportSection`、修复 4 个预存 TS 错误
- 🆕 `MathCaptcha.tsx` — 可复用验证码组件（展示 + `useCaptchaRule` hook）
- 🆕 `useRoleNavigate.ts` — 角色路由映射 hook
- 🆕 `StudentDetailPage.tsx` — 学员完整档案页（SVG 雷达图 + 三标签页）
- 🆕 `AiReportSection.tsx` — AI 报告卡片组件（含简易 Markdown 渲染器）

### 修改文件（15 个 + 4 个新建）

| 文件 | 类型 |
|------|------|
| `config/settings.py` | 配置 |
| `backend/database/seed.py` | 新增 `seed_users()` |
| `backend/main.py` | 启动流程 |
| `backend/routers/coach.py` | 增强（权限+搜索+档案） |
| `backend/routers/assessment.py` | 新增 AI 报告端点 |
| `backend/services/deepseek_service.py` | 新建 |
| `requirements.txt` | 依赖 |
| `frontend/src/App.tsx` | 路由（+学员详情） |
| `frontend/src/pages/LoginPage.tsx` | 增强 |
| `frontend/src/pages/CoachPage.tsx` | 增强（下拉+点击） |
| `frontend/src/pages/AssessmentReportPage.tsx` | 增强（AI 报告） |
| `frontend/src/pages/StudentDetailPage.tsx` | 新建 |
| `frontend/src/components/MathCaptcha.tsx` | 新建 |
| `frontend/src/components/AiReportSection.tsx` | 新建 |
| `frontend/src/hooks/useRoleNavigate.ts` | 新建 |
| `README.md` | 更新 |

### 关键设计决策
| 决策 | 理由 |
|------|------|
| 管理员可访问教练 API | Admin 需查看教练管理页面，`COACH_OR_ADMIN` 元组统一权限 |
| 验证码使用 `useRef` 而非 `useCallback` 闭包 | Ant Design Form 缓存旧 validator 导致正确结果也被拒绝 |
| 验证码结果限制个位数（1-4 随机数） | 避免两位数结果，降低用户认知负担 |
| AI 报告缓存在 `report_data` JSON | 避免数据库迁移，已有字段复用 |
| `deepseek-v4-pro` 兼容 `reasoning_content` 回退 | 思维链模型可能将内容放在 reasoning 字段 |：FMS 增强 + 实时训练重写 + 处方训练

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