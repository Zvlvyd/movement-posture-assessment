# 运动姿态评估与纠错系统 (Sports Posture Assessment and Correction System)

基于 YOLO-Pose 人体关键点检测的实时运动姿态评估与纠错系统，提供 FMS 功能性运动能力筛查、AI 训练处方生成、实时训练纠错等功能。

## 技术栈

| 层 | 技术 |
|------|------|
| **前端** | React 18 + TypeScript + Vite + Ant Design + Recharts |
| **后端** | Python FastAPI + SQLAlchemy ORM |
| **数据库** | MySQL 8.0（开发环境也可用 SQLite） |
| **姿态检测** | YOLOv8-Pose (Ultralytics) |
| **实时通信** | WebSocket（视频帧传输 + 关键点回流） |
| **认证** | JWT (python-jose) |

## 系统架构

```
┌─────────────────┐     WebSocket (base64 frames)     ┌──────────────────┐
│  React Frontend │ ────────────────────────────────> │  FastAPI Backend │
│  (Port 5173)    │ <────────────────────────────────  │  (Port 8002)     │
│                 │     JSON (keypoints + overlay)     │                  │
│  ┌───────────┐  │                                    │  ┌────────────┐  │
│  │ Camera    │  │                                    │  │ YOLO-Pose  │  │
│  │ Canvas    │  │                                    │  │ Engine     │  │
│  │ Overlay   │  │                                    │  └────────────┘  │
│  └───────────┘  │                                    │  ┌────────────┐  │
└─────────────────┘                                    │  │ Angle Calc │  │
                                                       │  └────────────┘  │
                                                       │  ┌────────────┐  │
                                                       │  │ FMS Engine │  │
                                                       │  └────────────┘  │
                                                       │  ┌────────────┐  │
                                                       │  │ Prescrip.  │  │
                                                       │  │ Engine     │  │
                                                       │  └────────────┘  │
                                                       └──────────────────┘
```

## 快速启动

### 前置条件

- Python 3.10+（推荐 conda 环境 `dl`）
- Node.js 18+
- MySQL 8.0（可选，开发环境自动降级 SQLite）

### 后端启动

```bash
# 进入项目目录
cd code/运动姿态评估与纠错系统/运动姿态评估与纠错系统

# 激活 conda 环境（如使用 conda）
conda activate dl

# 安装依赖（首次）
pip install -r requirements.txt

# 设置数据库 MySQL（可选，跳过则自动使用 SQLite）
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS pose_correction DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 启动后端（自动创建表结构，端口 8002）
python run.py
```

后端启动后访问：http://localhost:8002/docs （API 文档）

### 前端启动

```bash
# 进入前端目录
cd code/运动姿态评估与纠错系统/运动姿态评估与纠错系统/frontend

# 安装依赖（首次）
npm install

# 启动开发服务器（默认端口 5173，被占用则自动递增）
npm run dev
```

前端启动后访问：http://localhost:5173 （Vite 自动热更新，修改代码即时生效）

### 一键启动（同时打开前后端）

打开**两个终端窗口**分别执行：

**终端 1 — 后端：**
```bash
cd d:/workbench/program3/code/运动姿态评估与纠错系统/运动姿态评估与纠错系统
conda activate dl
python run.py
```

**终端 2 — 前端：**
```bash
cd d:/workbench/program3/code/运动姿态评估与纠错系统/运动姿态评估与纠错系统/frontend
npm install
npm run dev
```

## 功能模块

### 1. 用户管理
- 注册 / 登录（JWT Token）
- 个人信息管理
- 角色权限（训练者 / 教练 / 管理员）

### 2. FMS 功能性运动能力筛查
- **实时摄像头检测**：通过 WebSocket 将视频帧传输到后端
- **YOLO-Pose 关键点检测**：服务端运行 YOLO 模型，提取 17 个人体关键点
- **5 项测试**：
  - 闭眼单腿站立（平衡能力）
  - 徒手过头深蹲（下肢灵活性）
  - 肩关节活动度（上肢柔韧性）
  - 平板支撑（核心耐力）
  - 弓步蹲对称（双侧对称性）
- **自动评分**：基于关键点角度计算 + 评分算法
- **雷达图报告**：5 维可视化和问题标签
- **训练建议**：根据评估结果自动生成针对性训练方案

### 3. AI 训练处方
- 基于 FMS 筛查结果自动生成个性化处方
- 四阶段编排：热身 → 强化激活 → 主训练 → 冷身
- 难度分级和渐进解锁
- 月经周期适配（女性用户）

### 4. 实时训练与姿态纠错
- WebSocket 实时视频帧传输
- 双模式评分：
  - 基础模式：仅检测危险动作（膝关节内扣、躯干过度前倾）
  - 进阶模式：全关节角度偏差检测，0-100 分
- FSM 状态机动作识别（深蹲 / 弓步 / 俯卧撑）
- 骨架 overlay 可视化
- 语音播报纠错提示（预留）

### 5. 打卡激励系统
- 每日打卡 + 连续天数记录
- 徽章系统（7天 / 30天 / 100次训练里程碑）

### 6. 教练管理
- 班级管理（创建班级 + 添加学员）
- 学员训练数据查看

### 7. 系统管理
- 用户权限管理（角色分配、状态管理）
- 系统配置查看
- 操作日志查询

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 用户注册 |
| POST | /api/auth/login | 用户登录 |
| GET | /api/auth/me | 当前用户信息 |
| POST | /api/fms/screen | FMS 筛查提交（手动） |
| WS | /api/fms/ws | FMS 筛查 WebSocket（实时） |
| GET | /api/fms/records | 筛查记录列表 |
| POST | /api/prescription/generate/{fms_id} | 生成训练处方 |
| GET | /api/prescription | 处方列表 |
| POST | /api/training/start | 开始训练会话 |
| WS | /api/training/ws | 训练 WebSocket（实时） |
| POST | /api/checkin | 每日打卡 |
| GET | /api/records/stats | 训练统计 |
| GET | /api/learning/actions | 动作库列表 |
| GET | /api/coach/students | 学员列表（教练） |
| GET | /api/admin/users | 用户管理（管理员） |

## 数据库设计

系统包含 13 张核心表：

- **user** — 用户（训练者 / 教练 / 管理员）
- **fms_record** — FMS 筛查记录（5 维评分 + 综合评分 + 风险等级）
- **prescription** — 训练处方（阶段、状态、难度）
- **prescription_item** — 处方明细（动作、组数、次数）
- **action_library** — 标准动作库
- **problem_tag** — 问题标签
- **tag_action_mapping** — 标签-动作映射
- **training_record** — 训练记录
- **check_in_card** — 打卡记录
- **badge** — 徽章
- **user_cycle_config** — 生理周期配置
- **class_group** — 班级
- **system_log** — 系统日志

## 算法模块

### 关节角度计算
输入 17 个 COCO 关键点坐标，计算 7 个核心关节角度：
- 膝关节角度（左 / 右）
- 髋关节角度（左 / 右）
- 肩关节角度（左 / 右）
- 躯干倾斜角度
- 颈部角度

### FSM 动作识别
有限状态机建模，以深蹲为例：
`站立 → 下降 → 最低点 → 上升 → 回到站立`

### FMS 评分算法
- 闭眼单腿站立：>30秒 = 100分，每减1秒减3分
- 过头深蹲：深度评分x0.5 + 躯干控制x0.3 + 手臂保持x0.2
- 肩关节活动度：100 - 双手距离(cm) x 2
- 平板支撑：时长 / 60 x 100
- 弓步蹲对称：100 - 左右差异 x 2

### AI 处方推荐
规则引擎：问题标签 → 动作库匹配 → 难度排序 → 四阶段组装

## 项目结构

```
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py             # 配置管理
│   ├── database/
│   │   ├── connection.py     # 数据库连接
│   │   └── models.py         # ORM 模型（13 张表）
│   ├── routers/              # API 路由
│   ├── schemas/              # Pydantic 模型
│   └── services/             # 业务逻辑
├── frontend/
│   ├── src/
│   │   ├── pages/            # 页面组件（12 个）
│   │   ├── components/       # 公共组件
│   │   ├── services/         # API 封装
│   │   ├── store/            # 状态管理
│   │   └── types/            # TypeScript 类型
│   └── package.json
├── models/
│   ├── yolo_pose_engine.py   # YOLO-Pose 推理引擎
│   ├── angle_calculator.py   # 关节角度计算
│   ├── scoring.py            # 双模式评分
│   ├── action_recognizer/    # FSM 动作识别
│   ├── fms/                  # FMS 评分引擎
│   └── prescription/         # 处方推荐引擎
└── utils/
    └── pose_postprocessor.py # 姿态后处理
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DB_TYPE | mysql | 数据库类型（mysql / sqlite） |
| DB_HOST | localhost | 数据库主机 |
| DB_PORT | 3306 | 数据库端口 |
| DB_USER | root | 数据库用户 |
| DB_PASSWORD | Zly20050708 | 数据库密码 |
| DB_NAME | pose_correction | 数据库名 |
| SECRET_KEY | (内置密钥) | JWT 密钥 |
| MODEL_PATH | yolov8n-pose.pt | YOLO 模型路径 |
| DEVICE | auto | 推理设备（auto / cpu / cuda） |
| PORT | 8002 | 服务端口 |