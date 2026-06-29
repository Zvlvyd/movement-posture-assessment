# 运动姿态评估与纠错系统 (Sports Posture Assessment and Correction System)

基于 YOLO-Pose 人体关键点检测的实时运动姿态评估与纠错系统，提供 FMS 功能性运动能力筛查、AI 训练处方生成、实时训练纠错等功能。

## 功能模块

| 模块 | 路由 | 说明 |
|------|------|------|
| **首页** | `/home` | 极简 Hero，一键跳转计划训练 |
| **体态评估** | `/assessment` | 多视角摄像头采集 → AI 分析报告（体态问题诊断） |
| **FMS 筛查** | `/fms` | 7 项功能性运动能力测试（深蹲/跨栏/直线弓步/肩部灵活性/主动直腿抬高/躯干稳定俯卧撑/旋转稳定性） |
| **AI 处方** | `/prescription` | 基于评估结果智能生成训练计划（58 动作 × 10 家族） |
| **计划训练** | `/training` | 实时摄像头训练纠错（骨骼关键点 + 角度差异反馈） |
| **标准学习** | `/learning` | 58 动作标准动作库，5 动作已配置逐帧实时对比标准角度 |
| **每日打卡** | `/checkin` | 训练记录与进度追踪 |
| **个人中心** | `/profile` | 用户信息管理 |
| **教练管理** | `/coach` | 学员档案查看与管理（教练/管理员） |
| **系统管理** | `/admin` | 用户管理（管理员） |

## 技术栈

| 层 | 技术 |
|------|------|
| **前端** | React 18 + TypeScript + Vite + Ant Design + Recharts |
| **后端** | Python FastAPI + SQLAlchemy ORM |
| **数据库** | MySQL 8.0（开发环境也可用 SQLite） |
| **姿态检测** | YOLOv8-Pose (Ultralytics) |
| **实时通信** | WebSocket（视频帧传输 + 关键点回流） |
| **认证** | JWT (python-jose) |
| **AI 报告** | DeepSeek API（deepseek-v4-pro） |

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
│  ┌───────────┐  │                                    │  │ Assessment │  │
│  │ AI Report │  │  HTTPS (REST)                      │  │ Pipeline   │  │
│  │ Section   │──┼────────────────────────────────────┼──│ (体态+ROM)  │  │
│  └───────────┘  │                                    │  └────────────┘  │
└─────────────────┘                                    │  ┌────────────┐  │
                                                       │  │ DeepSeek   │  │
                                                       │  │ Service    │──┼─── DeepSeek API
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
# 切到 D 盘并进入后端目录
d:
cd workbench/program3/code/pose-system/pose-system

# 激活 conda 环境
conda activate dl

# 安装依赖（首次）
pip install -r requirements.txt

# （可选）创建 MySQL 数据库，跳过则自动使用 SQLite
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS pose_correction DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 启动（端口 8002，自动创建表结构）
python run.py
```

> 启动后访问 http://localhost:8002/docs 查看 API 文档

### 前端启动

```bash
# 切到 D 盘并进入前端目录
d:
cd workbench/program3/code/pose-system/pose-system/frontend

# 安装依赖（首次）
npm install

# 启动开发服务器
npm run dev
```

> Vite 默认端口 5173，被占用自动递增（5174、5175...），看终端输出确认实际地址

### 一键启动（两个终端分别执行）

**终端 1 — 后端：**
```bash
d:
cd workbench/program3/code/pose-system/pose-system
conda activate dl
python run.py
```

**终端 2 — 前端：**
```bash
d:
cd workbench/program3/code/pose-system/pose-system/frontend
npm install
npm run dev
```

## 功能模块

### 1. 用户管理
- 注册 / 登录（JWT Token），登录页含数学验证码
- 登录后按角色自动跳转：管理员 → 系统管理、教练 → 教练管理、学员 → 首页
- 首次启动自动创建默认账号：

| 角色 | 用户名 | 密码 | 说明 |
|------|--------|------|------|
| 管理员 | `admin` | `admin123` | 可通过环境变量覆盖 |
| 教练 | `coach` | `coach123` | 可通过环境变量覆盖 |

- 个人信息管理
- 角色权限（学员 / 教练 / 管理员），管理员可在系统管理中分配角色

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

### 3. 体态评估 × FMS 智能处方系统（v2 · 新增）

基于标准动作库 + 体态评估 + FMS 筛查的新一代处方生成模块，支持 DeepSeek AI 与本地规则双引擎。

#### 标准动作库
- **58 个徒手动作**（囚徒健身/徒手体操体系），9 大家族，**零器械**
- 每个动作家族包含 **难度递进变体**（regression → standard → progression）
- 每个动作定义：`difficulty`(1-5)、`intensity`(LOW/MEDIUM/HIGH)、目标肌群、FMS 禁忌阈值、体态问题关联权重
- 动作家族：俯卧撑(6) / 深蹲(6) / 髋铰链(5) / 上肢拉(5) / 核心抗伸展(6) / 核心抗侧屈(4) / 颈部矫正(4) / 拉伸(10) / 活动度(8) / 平衡(4)
- 素材命名规则：`{action_id}.{jpg|mp4}` → `backend/static/actions/`

#### 处方生成双引擎

| 引擎 | 说明 | 触发 |
|------|------|------|
| **DeepSeek AI** | 读取模板 + 体态评估 + FMS 数据 + 动作库 → 输出结构化处方 JSON | 默认 |
| **本地规则引擎** | EligibilityChecker + VolumeCalculator + PrescriptionBuilder | DeepSeek 不可用时自动回退 |

#### 决策流程

```
体态评估（AssessmentRecord）
  └─ 检测到的问题 (flags) → 决定「选哪些动作类型」(problem_mapping)
                              │
FMS 筛查（FMSRecord）          │
  └─ 5维分数 → 决定「能否做」(contraindications) + 「做多少」(volume)
                              │
                              ▼
                    动作库筛选 → 处方组装 → 存储
```

#### 核心模块

| 模块 | 文件 | 功能 |
|------|------|------|
| `StandardActionLibrary` | `models/prescription_v2/action_library.py` | 动作库加载与 7 种查询 |
| `EligibilityChecker` | `models/prescription_v2/eligibility_checker.py` | FMS → safe/caution/unsafe |
| `VolumeCalculator` | `models/prescription_v2/volume_calculator.py` | FMS + 强度 → sets/reps/duration |
| `PrescriptionBuilder` | `models/prescription_v2/prescription_builder.py` | 本地规则引擎（回退方案） |
| `TemplateEngine` | `models/prescription_v2/template_engine.py` | 提示词模板加载与渲染 |
| `DeepSeekPrescription` | `models/prescription_v2/deepseek_prescription.py` | AI 调用 + JSON 解析验证 |

#### 测试面板

- 路径：`https://localhost:5173/test-prescription`
- 四个标签页：体态评估模拟 → FMS 筛查模拟 → 动作库浏览 → 处方生成
- 体态评估/FMS 模拟数据可**一键写入数据库**创建真实记录 ID
- 支持 DeepSeek/本地引擎切换、训练水平设定、处方激活桥接

### 4. AI 训练处方（v1 · 保留）
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

### 5. 体态评估
- 多视角静态分析（正面 / 侧面 / 背面照片）
- 关节活动度（ROM）实时追踪（5 项引导动作）
- 不对称性分析（左右侧差异百分比）
- 肌肉紧张/薄弱分析
- 5 维能力雷达图 + 综合评分 + 风险等级
- 周期性复检提醒（14 天）

### 6. AI 智能分析报告
- 基于 DeepSeek API 生成专业体态评估报告
- 报告结构：总体评估 → 各维度分析 → 体态问题解读 → 改善建议 → 总结
- 报告缓存在记录中，支持重新生成
- 纯前端模块 `AiReportSection`，可嵌入任意评估结果页

### 7. 教练管理
- 班级管理（创建班级 + 按名称选择班级添加学员）
- 学员用户名模糊搜索（选择班级后自动补全）
- 点击学员名进入完整档案页（FMS + 体态评估 + 训练处方 + 训练记录 + 徽章）
- 班级详情统计：FMS 评分分布、训练趋势图、7日/30日训练量
- 学员进度追踪：风险等级标记、打卡天数、活跃度
- 管理员同样可访问教练管理页面

### 8. 打卡激励系统
- 每日打卡 + 连续天数记录
- 徽章系统（7天 / 30天 / 100次训练里程碑）

### 9. 系统管理
- 用户权限管理（角色分配、状态管理）
- 系统配置查看
- 操作日志查询

## API 端点

### 认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 用户注册（默认角色：学员） |
| POST | /api/auth/login | 用户登录（返回 JWT + 角色） |
| GET | /api/auth/me | 当前用户信息 |
| PUT | /api/auth/me | 更新个人信息 |
| PUT | /api/auth/change-password | 修改密码 |

### FMS 筛查
| 方法 | 路径 | 说明 |
|------|------|------|
| WS | /api/fms/ws | FMS 筛查 WebSocket（实时） |
| GET | /api/fms/records | 筛查记录列表 |
| GET | /api/fms/report/{id} | 筛查报告详情 |

### 训练与处方
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/prescription/generate/{fms_id} | 生成训练处方（v1） |
| GET | /api/prescription | 处方列表（v1） |
| POST | /api/prescription-v2/generate | **生成训练处方（v2 · DeepSeek + 本地双引擎）** |
| GET | /api/prescription-v2/plans | **处方计划列表（v2）** |
| GET | /api/prescription-v2/plans/{id} | **处方计划详情（v2）** |
| POST | /api/prescription-v2/plans/{id}/activate | **激活计划 + 桥接旧训练页面（v2）** |
| GET | /api/prescription-v2/actions | **标准动作库（v2 · 58 个徒手动作）** |
| POST | /api/prescription-v2/test/mock-assessment | **[测试] 创建模拟体态评估记录** |
| POST | /api/prescription-v2/test/mock-fms | **[测试] 创建模拟 FMS 记录** |
| POST | /api/prescription-v2/test/mock-both | **[测试] 一次性创建两个模拟记录** |
| POST | /api/training/start | 开始训练会话 |
| WS | /api/training/ws | 训练 WebSocket（实时） |
| POST | /api/checkin | 每日打卡 |
| GET | /api/records/stats | 训练统计 |
| GET | /api/learning/actions | 动作库列表 |

### 体态评估
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/assessment/submit | 提交关键点数据，运行评估管道 |
| GET | /api/assessment/records | 评估记录列表 |
| GET | /api/assessment/records/{id} | 评估详情（含体态问题/ROM/肌肉分析） |
| WS | /api/assessment/ws | 实时评估 WebSocket |
| POST | /api/assessment/records/{id}/generate-report | DeepSeek AI 生成分析报告 |
| GET | /api/assessment/re-test-status | 检查是否需周期性复检 |

### 教练管理（教练 / 管理员）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/coach/summary | 教练仪表盘概览 |
| GET | /api/coach/classes | 班级列表 |
| POST | /api/coach/classes | 创建班级 |
| GET | /api/coach/students | 学员列表 |
| POST | /api/coach/classes/{id}/students | 添加学员到班级 |
| GET | /api/coach/classes/{id}/stats | 班级详细统计 |
| GET | /api/coach/classes/{id}/trend | 班级训练趋势 |
| GET | /api/coach/available-trainees | 按用户名搜索学员 |
| GET | /api/coach/students/{id}/profile | 学员完整档案 |

### 系统管理（管理员）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/admin/users | 用户列表 |
| PUT | /api/admin/users/{id}/role | 修改用户角色 |
| PUT | /api/admin/users/{id}/status | 启用/禁用用户 |
| GET | /api/admin/config | 系统配置 |
| GET | /api/admin/logs | 操作日志 |

## 数据库设计

系统包含 16 张核心表：

- **user** — 用户（学员 / 教练 / 管理员）
- **fms_record** — FMS 筛查记录（5 维评分 + 综合评分 + 风险等级）
- **assessment_record** — 体态评估记录（5 维评分 + 体态数据 + ROM + 肌肉分析 + AI 报告）
- **prescription** — 训练处方 v1（阶段、状态、难度）
- **prescription_item** — 处方明细 v1（动作、组数、次数）
- **prescription_plan** — **训练处方 v2（计划名称、策略、生成方式、AI 原始响应）**
- **prescription_plan_item** — **处方明细 v2（动作 ID、阶段、组数、次数、备注、替代标记）**
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
│   │   ├── models.py         # ORM 模型（14 张表）
│   │   ├── models_v2.py      # **处方 v2 ORM 模型（2 张新表）**
│   │   └── seed.py           # 种子数据（动作库 + 默认账号）
│   ├── routers/              # API 路由（12 个模块，含 prescription_v2）
│   ├── schemas/              # Pydantic 模型（含 prescription_v2）
│   └── services/             # 业务逻辑（含 deepseek_service + prescription_v2_service）
├── frontend/
│   ├── src/
│   │   ├── pages/            # 页面组件（17 个，含 TestPrescriptionPage）
│   │   ├── components/       # 公共组件（MathCaptcha / AiReportSection 等）
│   │   ├── hooks/            # 自定义 Hook（useRoleNavigate 等）
│   │   ├── services/         # API 封装（Axios）
│   │   ├── store/            # 状态管理（Zustand）
│   │   └── types/            # TypeScript 类型
│   └── package.json
├── models/
│   ├── engine.py             # YOLO 模型管理器（单例）
│   ├── yolo_pose_engine.py   # YOLO-Pose 推理引擎
│   ├── angle_calculator.py   # 关节角度计算
│   ├── posture_analyzer.py   # 静态体态分析
│   ├── scoring.py            # 双模式评分
│   ├── action_recognizer/    # FSM 动作识别
│   ├── assessment/           # 体态评估管道（ROM/不对称/融合/报告）
│   ├── fms/                  # FMS 评分引擎
│   ├── prescription/         # 处方推荐引擎 v1
│   ├── prescription_v2/      # **处方生成模块 v2（新增）**
│   │   ├── action_library.json  # 标准动作库（58 个徒手动作）
│   │   ├── action_library.py    # 动作库加载器
│   │   ├── eligibility_checker.py # FMS → 动作可行性判断
│   │   ├── volume_calculator.py   # FMS → 训练量计算
│   │   ├── prescription_builder.py # 本地规则引擎
│   │   ├── template_engine.py     # 提示词模板引擎
│   │   ├── deepseek_prescription.py # DeepSeek AI 处方生成
│   │   └── templates/         # 提示词模板（system + plan）
│   └── knowledge/            # 知识库（JSON）
├── config/
│   ├── settings.py           # 全局配置
│   └── constants.py          # 常量定义
└── utils/
    └── pose_postprocessor.py # 姿态后处理
```

## 环境变量

### 数据库
| 变量 | 默认值 | 说明 |
|------|--------|------|
| DB_TYPE | mysql | 数据库类型（mysql / sqlite） |
| DB_HOST | localhost | 数据库主机 |
| DB_PORT | 3306 | 数据库端口 |
| DB_USER | root | 数据库用户 |
| DB_PASSWORD | — | 数据库密码 |
| DB_NAME | pose_correction | 数据库名 |

### 认证
| 变量 | 默认值 | 说明 |
|------|--------|------|
| SECRET_KEY | (内置密钥) | JWT 签名密钥 |
| DEFAULT_ADMIN_USERNAME | admin | 默认管理员用户名 |
| DEFAULT_ADMIN_PASSWORD | admin123 | 默认管理员密码 |
| DEFAULT_COACH_USERNAME | coach | 默认教练用户名 |
| DEFAULT_COACH_PASSWORD | coach123 | 默认教练密码 |

> 种子账号仅在数据库中不存在时创建（幂等），生产环境请通过环境变量修改默认密码。

### AI 报告
| 变量 | 默认值 | 说明 |
|------|--------|------|
| DEEPSEEK_API_KEY | — | DeepSeek API 密钥（必填） |
| DEEPSEEK_BASE_URL | https://api.deepseek.com | API 地址（OpenAI 兼容） |
| DEEPSEEK_MODEL | deepseek-v4-pro | 模型名称 |

### 模型与服务
| 变量 | 默认值 | 说明 |
|------|--------|------|
| MODEL_PATH | yolov8s-pose.pt | YOLO 模型路径 |
| HIGH_PRECISION_MODEL_PATH | yolov8s-pose.pt | 高精度模型路径 |
| DEVICE | auto | 推理设备（auto / cpu / cuda） |
| HOST | 0.0.0.0 | 服务监听地址 |
| PORT | 8002 | 服务端口 |