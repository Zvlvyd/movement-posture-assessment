# 运动姿态评估与纠错系统

Sports Posture Assessment and Correction System

## 项目简介

基于 YOLOv8 姿态估计和 FastAPI + React 的实时运动姿态评估与纠错系统。支持 FMS（功能性运动筛查）、体态评估、AI 训练计划生成、标准动作实时学习、教练班级管理、管理员系统管理等功能。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python FastAPI + Uvicorn |
| AI 模型 | Ultralytics YOLOv8-Pose (yolov8s-pose.pt / yolov8n-pose.pt) |
| 数据库 | MySQL (PyMySQL) + SQLAlchemy ORM + 自动迁移 |
| 认证 | JWT (python-jose) + bcrypt |
| 前端框架 | React 18 + TypeScript + Vite |
| UI 库 | Ant Design 5 + Recharts（图表） |
| 状态管理 | Zustand |
| 实时通信 | WebSocket |
| AI 处方 | DeepSeek API（可选） |

## 项目结构

```
pose-system/
├── backend/
│   ├── main.py              # FastAPI 入口 + 静态文件挂载
│   ├── routers/             # API 路由（薄层，仅参数解析 → 调用 service）
│   │   ├── admin.py             # 管理员 API（用户管理/仪表板/配置/日志/导出）
│   │   ├── coach.py             # 教练班级 API（班级/学员/训练计划管理）
│   │   ├── coach_actions.py     # 教练动作库 API（查看/编辑/创建/上传媒体）
│   │   ├── learning.py          # 标准学习 API + WebSocket
│   │   ├── prescription_v2.py   # AI 训练处方 API
│   │   ├── auth.py              # 认证 API
│   │   ├── fms.py               # FMS 筛查 API + 视频上传
│   │   └── assessment.py        # 体态评估 API
│   ├── services/            # 业务逻辑（厚层）
│   │   ├── admin_service.py              # 管理员服务（用户管理/仪表板/导出）
│   │   ├── coach_service.py              # 教练服务（班级/学员/计划管理）
│   │   ├── action_library_service.py     # 动作库服务（三源合并/CRUD/媒体上传）
│   │   ├── learning_service.py           # 标准学习服务（含 DB 媒体数据合并）
│   │   ├── auth_service.py               # 认证 + 权限守卫
│   │   ├── deepseek_service.py           # DeepSeek AI 集成
│   │   └── ...
│   └── database/            # 数据模型 + 种子数据
│       ├── models.py            # 核心 ORM 模型（User/ActionLibrary/ActionMedia/SystemConfig...）
│       ├── models_v2.py         # v2 处方模型（PrescriptionPlan/PrescriptionPlanItem）
│       ├── connection.py        # 数据库引擎 + 自动迁移（run_migrations）
│       └── seed.py              # 种子数据（动作库/系统配置/默认账户）
├── frontend/
│   └── src/
│       ├── pages/           # 页面组件
│       │   ├── admin/           # 管理员子页面
│       │   │   ├── DashboardTab.tsx        # 系统仪表板（图表）
│       │   │   ├── UserManagementTab.tsx   # 用户管理（搜索/筛选/批量）
│       │   │   ├── ConfigTab.tsx           # 系统配置（可编辑表格）
│       │   │   ├── LogsTab.tsx             # 操作日志
│       │   │   └── charts/                 # Recharts 图表组件
│       │   ├── coach/           # 教练子页面
│       │   │   └── ActionLibraryPage.tsx   # 动作库管理（筛选/编辑/上传）
│       │   ├── AdminPage.tsx
│       │   ├── CoachPage.tsx
│       │   ├── StudentDetailPage.tsx       # 学员详情（含 V2 计划管理）
│       │   ├── LearningPage.tsx            # 标准学习（示范 → 实时对比）
│       │   └── ...
│       ├── components/      # 共享组件
│       │   ├── MainLayout.tsx       # 侧边栏（角色差异化菜单）
│       │   ├── MediaUpload.tsx      # 媒体上传（拖拽/预览/删除）
│       │   ├── ScoreBar.tsx         # FMS 评分迷你进度条
│       │   ├── MovementDemo.tsx     # SVG 骨架动作示范
│       │   ├── TrainingSessionPanel.tsx
│       │   └── ...
│       ├── services/        # API 客户端
│       │   └── api.ts              # 所有 API 请求统一出口
│       ├── types/
│       │   └── index.ts            # TypeScript 类型定义
│       ├── store/
│       │   └── auth.ts             # Zustand 认证状态
│       ├── hooks/
│       │   ├── useRoleNavigate.ts  # 角色感知导航
│       │   └── useTrainingSession.ts
│       └── utils/
│           └── riskColor.ts        # 风险等级工具
├── models/                  # AI 模型 & 知识库
│   ├── engine.py            # YOLO 模型管理器（单例，支持 conf 参数）
│   ├── angle_calculator.py  # 关节角度计算器
│   └── prescription_v2/
│       └── action_library.json    # 55 个标准动作（10 个家族）
│   └── knowledge/
│       ├── standard_actions.json  # 16 个动作标准角度（8 类分类体系）
│       ├── problems.json          # 7 个体态问题定义（中文标签）
│       └── exercises.json         # 体态矫正练习库
├── uploads/
│   └── actions/             # 教练上传的动作示例媒体
├── config/
│   └── settings.py
├── CHANGELOG.md
├── diagnose_thumbnail.py    # 诊断 + 修复脚本
├── run.py
└── requirements.txt
```

## 快速开始

### 环境要求

- Python 3.10+ (conda 环境 `dl`)
- Node.js 18+
- MySQL 8.0+（或 SQLite 用于开发）
- 摄像头（用于实时学习 / FMS 筛查）

### 1. 配置数据库

```sql
CREATE DATABASE pose_correction CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

复制 `.env.example` 为 `.env`，按需修改。

### 2. 安装依赖

```bash
# Python 依赖
conda activate dl
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

### 3. 启动

```bash
# 后端（端口 8002，启动时自动预加载 YOLO + 迁移 DB + 种子数据）
conda activate dl
python run.py

# 前端（端口 5173，API 自动代理到 8002）
cd frontend
npm run dev
```

访问 `https://localhost:5173/`

### 4. 默认账号

| 角色 | 用户名 | 密码 | 说明 |
|------|--------|------|------|
| 管理员 | `admin` | `admin123` | 首次启动自动创建 |
| 教练 | `coach` | `coach123` | 首次启动自动创建 |
| 学员 | 自行注册 | — | 注册即获学员角色 |

## 用户角色

| 角色 | 核心功能 |
|------|----------|
| **学员** | 体态评估、FMS 筛查、AI 训练计划、标准动作学习（示范 → 实时对比）、每日打卡 |
| **教练** | 学员全部功能 + 班级管理（创建/添加/移除学员）、学员档案查看、删除学员训练计划、**标准动作库管理**（查看/编辑元数据/上传图片视频/创建自定义动作） |
| **管理员** | 教练全部功能 + 用户管理（搜索/筛选/角色变更/软删除/批量操作/CSV 导出）、**系统仪表板**（注册趋势/DAU/WAU/MAU/角色分布图表）、系统配置编辑、操作日志 |

## 核心功能

### FMS 功能性运动筛查
- 5 项标准测试：闭眼单腿站立、过头深蹲、肩关节活动度、平板支撑、弓步蹲
- 实时摄像头 YOLO 姿态检测 + 骨架可视化
- 视频上传模式（逐帧分析）+ 自动评分 + 雷达图报告
- **肩关节活动度**：肩宽自适应校准（像素→厘米），欧几里得距离度量，取最优 1/3 帧避免异常干扰
- **骨架标注视频**：视频上传处理后自动生成带关键点标注的渲染视频（`GET /api/fms/processed-video/{filename}`）
- **统一分析函数**：`build_fms_analysis()` 为 REST 和 WebSocket 提供一致的维度诊断和动作推荐

### 标准动作学习
- 55 个标准动作库（10 个家族），**16 个已配置标准角度实时对比**
- 8 类标准分类体系：上肢推 / 上肢拉 / 下肢蹲 / 下肢拉 / 核心抗伸展 / 核心抗侧屈 / 颈部矫正 / 拉伸
- 三阶段流程：浏览 → 示范（图片/视频/SVG 骨架） → 实时摄像头对比
- 逐帧关节角度差异分析（支持 left_knee/right_knee/left_hip/right_hip/left_shoulder/right_shoulder/left_elbow/right_elbow/trunk_tilt/neck_tilt 共 10 个关节角度）
- 自动完成检测（连续 30 帧得分 ≥ 85）
- 教练上传的图片/视频自动同步到动作示范页
- 支持正面/侧面/背面多视角标准角度切换

### 管理员端
- **用户管理**：搜索/筛选/分页、角色变更、软删除/恢复、批量操作（激活/停用/改角色）、CSV 导出
- **系统仪表板**：注册趋势折线图、角色分布饼图、DAU/WAU/MAU 柱状图、API 请求统计
- **系统配置**：可编辑表格（白名单保护，密钥等敏感配置不可通过 UI 修改）
- **操作日志**：搜索/筛选/导出 CSV

### 教练端
- **班级管理**：创建/编辑/删除班级、添加/移除学员
- **学员档案**：FMS 历史、体态评估、v1+v2 训练计划、打卡记录、徽章
- **训练计划管理**：查看/删除学员 PrescriptionPlan V2
- **动作库管理**：筛选（分类/家族/难度/部位）、卡片网格展示、详情 Modal（步骤时间线/要领/禁忌症）、编辑元数据、上传图片/视频/缩略图、创建自定义动作

### AI 训练处方
- 基于体态评估 + FMS 筛查结果自动生成个性化训练计划
- DeepSeek AI 生成（带本地规则引擎回退）
- 动作库自动匹配问题标签（ProblemTag → TagActionMapping）

### 其他
- 每日打卡 + 连续打卡徽章系统
- 体态评估（正/侧/背面多视角分析 + ROM + 不对称 + 肌肉紧张/薄弱）
- 月经周期配置（影响训练强度）

## 配置说明

`.env` 文件主要配置项：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_HOST` | 数据库主机 | localhost |
| `DB_PORT` | 数据库端口 | 3306 |
| `DB_NAME` | 数据库名 | pose_correction |
| `PORT` | 后端端口 | 8002 |
| `SECRET_KEY` | JWT 签名密钥 | — |
| `MODEL_PATH` | YOLO 模型路径 | yolov8s-pose.pt |
| `DEVICE` | 推理设备 | auto |
| `DEEPSEEK_API_KEY` | DeepSeek API Key（可选） | — |
| `DEEPSEEK_MODEL` | DeepSeek 模型 | deepseek-v4-pro |

## 诊断工具

```bash
# 诊断图片上传 → 标准学习数据流
python diagnose_thumbnail.py
```

该脚本依次检查：
1. DB 中目标动作记录 → 2. thumbnail_url 是否同步 → 3. 模拟 API 返回值 → 4. 文件系统文件
5. **自动修复**：将已有 ActionMedia 记录同步到 action.thumbnail_url/video_url

## 文件存储

| 类型 | 路径 | 访问 URL |
|------|------|----------|
| 系统内置动作媒体 | `frontend/public/media/actions/` | `/media/actions/...` |
| 教练上传的动作媒体 | `uploads/actions/` | `/media/uploads/actions/...` |
| 数据库路径 | `ActionMedia.file_path`（仅文件名） | 前端拼接 `/media/uploads/actions/` + 文件名 |

## 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)
