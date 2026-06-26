# 运动姿态评估与纠错系统

基于 YOLO-Pose 人体关键点检测的实时运动姿态评估与纠错系统。

## 功能模块

### 核心业务

| 模块 | 入口 | 说明 |
|------|------|------|
| **FMS 功能性运动筛查** | `/fms` → `/fms/report/:id` | 5 维度评估（平衡/灵活/上肢/核心/对称），支持实时摄像头 + 视频上传 |
| **体态评估** | `/assessment` → `/assessment/report/:id` | 三视角静态照片采集 + ROM 定向验证 + 多证据融合 |
| **实时训练** | `/training` → `/training/report/:id` | 7 动作自选、WebSocket 逐帧纠错、完成计数、双模式评分（基础/进阶） |
| **处方训练** | `/prescription-training` → `/prescription-training/report/:id` | 基于评估结果的个性化处方 → 顺序多动作训练 → 独立报告 |
| **标准学习** | `/learning` | 摄像头实时对比标准动作 + 精细化反馈 |
| **每日打卡** | `/checkin` | 连续打卡 + 徽章激励系统 |
| **教练管理** | `/coach` | 班级管理 + 学员 FMS 档案（coach/admin 角色） |
| **系统管理** | `/admin` | 用户权限 + 系统配置（admin 角色） |

### 通用功能

- JWT 登录/注册（trainee / coach / admin 三角色）
- 个人中心（`/profile`）
- 训练处方自动生成（基于 FMS 或体态评估结果）

## 技术栈

| 层 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Vite + Ant Design 5 |
| 后端 | Python FastAPI + SQLAlchemy ORM |
| 数据库 | MySQL 8.0（默认）/ SQLite |
| 姿态检测 | YOLOv8-Pose (Ultralytics) |
| 实时通信 | WebSocket（逐帧双向） |
| 图表 | Recharts（雷达图） |

## 架构概览

```
┌─────────────────────────────────────────────────┐
│                    前端 (React)                    │
│  pages/          components/      services/api.ts │
│  (路由页面)       (MainLayout 等)   (axios 封装)    │
└──────────────────────┬──────────────────────────┘
                       │ HTTP REST + WebSocket
┌──────────────────────┴──────────────────────────┐
│                 后端 (FastAPI)                     │
│                                                    │
│  routers/ ──→ services/ ──→ models/               │
│  (路由层)     (业务逻辑)     (算法引擎)              │
│                 │                                  │
│                 ├── base.py (WebSocket 基类)        │
│                 └── model_manager (YOLO 单例)       │
│                                                    │
│  schemas/       database/        config/           │
│  (Pydantic)     (ORM + 连接)     (应用配置)         │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────┐
│              MySQL 8.0 / SQLite                    │
│  user | fms_record | assessment_record |           │
│  prescription | training_record | check_in_card    │
└─────────────────────────────────────────────────┘
```

**数据流：** Router（参数校验）→ Service（编排）→ Model（算法）→ DB  
**实时流：** WebSocket → Service.handle() → ModelManager.get_keypoints() → AngleCalculator → Scorer → FSM → 逐帧响应

---

## 项目结构

### 后端 — `code/pose-system/pose-system/`

```
├── run.py                           # 启动入口：uvicorn backend.main:app
├── config/                          # 全局配置（模块化）
│   ├── settings.py                  #   数据库/模型/认证/CORS 配置
│   └── constants.py                 #   硬编码常量（评分阈值等）
├── backend/
│   ├── main.py                      # FastAPI 应用工厂 + CORS + 路由注册
│   ├── config.py                    # （已废弃，config/settings.py 替代）
│   ├── routers/                     # API 路由层 — 参数校验 + 调用 Service
│   │   ├── auth.py                  #   /api/auth/*          登录/注册/个人信息
│   │   ├── fms.py                   #   /api/fms/*           FMS 筛查 + 视频上传 + WS
│   │   ├── assessment.py            #   /api/assessment/*    体态评估 + 多视角 WS
│   │   ├── multi_view_assessment.py #   /api/multi-view/*   三视角照片上传/验证提交
│   │   ├── training.py              #   /api/training/*      训练启动/结束/记录 + WS
│   │   ├── prescription.py          #   /api/prescription/*  处方生成/列表/详情
│   │   ├── learning.py              #   /api/learning/*      标准动作库 + 学习 WS
│   │   ├── checkin.py               #   /api/checkin/*       打卡/徽章
│   │   ├── records.py               #   /api/records/*       训练历史/统计
│   │   ├── coach.py                 #   /api/coach/*         教练管理
│   │   └── admin.py                 #   /api/admin/*         系统管理
│   ├── services/                    # 业务逻辑层 — 编排算法 + 数据持久化
│   │   ├── base.py                  #   BaseWebSocketHandler（YOLO 共享 + 帧解码）
│   │   ├── fms_service.py           #   FMSService + RealtimeFMSService + VideoFMSService
│   │   ├── assessment_service.py    #   RealtimeAssessmentService + VerificationWebSocketHandler
│   │   ├── training_service.py      #   TrainingService + TrainingWebSocketHandler
│   │   ├── learning_service.py      #   LearningWebSocketHandler
│   │   ├── prescription_service.py  #   处方 CRUD + 生成逻辑
│   │   ├── auth_service.py          #   JWT 签发/验证
│   │   └── report_service.py        #   训练历史/统计分析
│   ├── schemas/                     # Pydantic 请求/响应模型
│   │   ├── business.py              #   FMS/Assessment/Prescription/Training/MultiView
│   │   └── user.py                  #   User/Token 模型
│   └── database/                    # 数据库层
│       ├── connection.py            #   SessionLocal 工厂 + get_db 依赖
│       ├── models.py                #   SQLAlchemy ORM（8 张表）
│       └── seed.py                  #   种子数据（默认管理员等）
├── models/                          # 算法模型（纯 Python，与 Web 框架无关）
│   ├── engine.py                    #   ModelManager 线程安全 YOLO 单例
│   ├── yolo_pose_engine.py          #   YOLOPoseEngine（Ultralytics 封装）
│   ├── angle_calculator.py          #   AngleCalculator — 17 关键点 → 关节角度
│   ├── scoring.py                   #   DualModeScorer — 基础/进阶双模式评分
│   ├── posture_analyzer.py          #   PostureAnalyzer — 正/背/侧三视角体态分析
│   ├── action_recognizer/           # 动作识别（FSM 状态机）
│   │   ├── state_machine.py         #   通用状态机引擎
│   │   ├── action_definitions.py    #   动作定义（关节映射/评测标准）
│   │   └── squat_fsm.py             #   7 动作 FSM（深蹲/弓步/俯卧撑/平板/肩推/开合跳/硬拉）
│   ├── fms/                         # FMS 评分子系统
│   │   ├── scoring.py               #   FMSScoringEngine + Score（摇摆/臀降惩罚）
│   │   ├── radar_report.py          #   RadarReport 雷达图数据生成
│   │   └── problem_tagger.py        #   ProblemTagger 问题自动标记
│   ├── assessment/                  # 体态评估子系统（多视角 + 融合）
│   │   ├── movement_definitions.py  #   动作定义（ROM 关节映射）
│   │   ├── scoring.py               #   UnifiedScoringEngine 统一评分
│   │   ├── rom_tracker.py           #   ROMTracker ROM 实时跟踪
│   │   ├── asymmetry_analyzer.py    #   AsymmetryAnalyzer 左右不对称
│   │   ├── report_generator.py      #   ReportGenerator 评估报告
│   │   ├── multi_view_analyzer.py   #   MultiViewAnalyzer 三视角合并分析
│   │   ├── multi_view_session.py    #   MultiViewSessionStore 内存会话存储
│   │   ├── velocity_analyzer.py     #   VelocityAnalyzer 左右速度不对称
│   │   ├── fusion_engine.py         #   FusionEngine 静态+ROM+速度加权融合
│   │   └── verification_mapper.py   #   VerificationMapper 问题→验证动作映射
│   ├── prescription/                # 处方推荐子系统
│   │   ├── problem_exercise_mapper.py  # 问题→训练动作映射
│   │   └── recommendation_engine.py    # RecommendationEngine 推荐算法
│   └── knowledge/                   # 知识库（JSON）
│       ├── exercises.json           #   训练动作库
│       ├── muscles.json             #   肌肉群数据
│       ├── problems.json            #   常见问题库
│       ├── rom_norms.json           #   ROM 关节活动度常模
│       ├── standard_actions.json    #   标准动作参数
│       └── thresholds.json          #   评测阈值
├── shared/                          # 共享工具（前后端服务共用）
│   ├── image_utils.py               #   base64 解码 + 帧缩放
│   └── scoring_utils.py             #   维度分数计算 + flag→维度映射
├── utils/                           # 工具
│   └── pose_postprocessor.py        #   关键点后处理（平滑/插值）
├── scripts/                         # 开发/测试脚本
│   ├── app.py                       #   独立姿态估计（CLI）
│   ├── process_video.py             #   视频批处理
│   └── start_backend.py             #   后端快捷启动
└── tests/                           # 测试
    ├── test_fms_video.py            #   FMS 视频离线测试
    └── test_ws.py                   #   WebSocket 协议测试
```

### 前端 — `frontend/src/`

```
├── main.tsx                         # ReactDOM 入口
├── App.tsx                          # 路由配置（14 条路由）
├── index.css                        # 全局样式
├── vite-env.d.ts                    # Vite 类型声明
├── pages/                           # 页面组件（每页 = 一个路由）
│   ├── LoginPage.tsx                #   /login              登录
│   ├── RegisterPage.tsx             #   /register           注册
│   ├── HomePage.tsx                 #   /home               首页仪表盘
│   ├── FMSScreeningPage.tsx         #   /fms                FMS 实时筛查
│   ├── FMSReportPage.tsx            #   /fms/report/:id     FMS 报告（雷达图+建议）
│   ├── AssessmentPage.tsx           #   /assessment         体态评估（三视角采集）
│   ├── AssessmentReportPage.tsx     #   /assessment/report  体态评估报告
│   ├── TrainingPage.tsx             #   /training           实时训练（7动作自选）
│   ├── TrainingReportPage.tsx       #   /training/report    训练报告
│   ├── PrescriptionTrainingPage.tsx #   /prescription-train 处方训练（多动作顺序）
│   ├── PrescriptionTrainingReportPage.tsx # /prescription-training/report  处方报告
│   ├── LearningPage.tsx             #   /learning           标准动作学习
│   ├── CheckinPage.tsx              #   /checkin            每日打卡
│   ├── ProfilePage.tsx              #   /profile            个人中心
│   ├── CoachPage.tsx                #   /coach              教练管理
│   └── AdminPage.tsx                #   /admin              系统管理
├── components/                      # 公共组件
│   ├── MainLayout.tsx               #   主布局（Header 导航 + Content + Footer）
│   ├── SkeletonOverlay.tsx          #   骨骼关键点 Canvas 叠加层
│   └── MovementDemo.tsx             #   标准动作演示播放器
├── services/
│   └── api.ts                       #   Axios 封装（authApi/fmsApi/assessmentApi/trainingApi...）
├── store/
│   └── auth.ts                      #   Zustand 认证状态（token + user）
├── types/
│   └── index.ts                     #   TypeScript 类型定义
├── config/
│   └── assessmentSteps.ts           #   体态评估步骤配置
└── utils/
    └── audio.ts                     #   提示音工具（倒计时/完成音效）
```

---

## 数据库表

| 表 | 对应 ORM | 说明 |
|----|----------|------|
| `user` | `User` | 用户（trainee/coach/admin） |
| `fms_record` | `FMSRecord` | FMS 筛查结果（5 维度分数） |
| `assessment_record` | `AssessmentRecord` | 体态评估结果（含多视角数据） |
| `prescription` | `Prescription` | 训练处方（关联 FMS 或评估） |
| `prescription_item` | `PrescriptionItem` | 处方内动作项 |
| `training_record` | `TrainingRecord` | 训练记录（关联处方或独立） |
| `check_in_card` | `CheckInCard` | 打卡记录 |
| `class_group` | `ClassGroup` | 教练班级 |

---

## 快速启动

### 环境要求

- Python 3.10+（conda 环境 `dl`）
- Node.js 18+
- MySQL 8.0

### 后端

```bash
d:
cd workbench\program3\code\pose-system\pose-system
conda activate dl
python run.py
```

### 前端

```bash
d:
cd workbench\program3\code\pose-system\pose-system\frontend
npm run dev
```

---

## 文档

| 文档 | 路径 |
|------|------|
| API 接口 | [docs/API.md](docs/API.md) |
| 更新日志 | [docs/CHANGELOG.md](docs/CHANGELOG.md) |
| v2 优化详情 | [docs/upgrades/2026-06-26-v2-module-optimization.md](docs/upgrades/2026-06-26-v2-module-optimization.md) |
| 概要设计 | [doc/概要设计/](doc/概要设计/) |
| 详细设计 | [doc/详细设计/](doc/详细设计/) |
