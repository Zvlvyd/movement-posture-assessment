# 运动姿态评估与纠错系统

基于 YOLO-Pose 人体关键点检测的实时运动姿态评估与纠错系统。

## 功能模块

- **FMS 功能性运动能力筛查** — 5维度评估（平衡/灵活/上肢/核心/对称）
- **AI 智能训练处方** — 基于评估结果的个性化训练方案
- **实时训练与姿态纠错** — WebSocket 实时视频帧 + 骨架叠加
- **双模式训练** — 基础模式（安全报警）/ 进阶模式（效果考核）
- **标准动作学习** — 摄像头实时对比标准动作 + 精细化反馈
- **每日打卡与激励** — 连续打卡 + 徽章系统
- **教练/教师管理** — 班级管理 + 学员FMS档案
- **系统管理** — 用户权限 + 系统配置

## 技术栈

| 层 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Vite + Ant Design |
| 后端 | Python FastAPI + SQLAlchemy ORM |
| 数据库 | MySQL 8.0 / SQLite |
| 姿态检测 | YOLOv8-Pose (Ultralytics) |
| 实时通信 | WebSocket |

## 快速启动

### 环境要求

- Python 3.10+（推荐 conda 环境）
- Node.js 18+
- MySQL 8.0（可选，支持 SQLite）

### 后端

```bash
cd code/运动姿态评估与纠错系统/运动姿态评估与纠错系统
pip install -r requirements.txt
python run.py
```

### 前端

```bash
cd code/运动姿态评估与纠错系统/运动姿态评估与纠错系统/frontend
npm install
npm run dev
```

## 项目结构

```
├── code/                       # 应用代码
│   └── 运动姿态评估与纠错系统/
│       ├── backend/            # FastAPI 后端
│       │   ├── routers/        # API 路由
│       │   ├── services/       # 业务逻辑
│       │   ├── schemas/        # Pydantic 模型
│       │   └── database/       # 数据库连接与ORM
│       ├── frontend/           # React 前端
│       │   └── src/
│       │       ├── pages/      # 页面组件
│       │       ├── components/ # 公共组件
│       │       └── services/   # API 封装
│       ├── models/             # 算法模型
│       │   ├── assessment/     # 评估引擎
│       │   ├── fms/            # FMS 评分
│       │   ├── prescription/   # 处方推荐
│       │   └── knowledge/      # 知识库
│       └── utils/              # 工具函数
├── doc/                        # 设计文档
│   ├── 概要设计/
│   └── 详细设计/
├── docs/                       # 项目文档
├── plan/                       # 计划文档
└── keypoints.json              # COCO 关键点配置
```

## 文档

- [API 接口文档](docs/API.md)
- [更新日志](docs/CHANGELOG.md)
- [概要设计文档](doc/概要设计/)
- [详细设计文档](doc/详细设计/)
