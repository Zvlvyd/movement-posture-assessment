# 运动姿态评估与纠错系统 — 集成文档

## 快速启动

```powershell
# 1. 进入项目目录
cd "D:\workbench\program3\code\运动姿态评估与纠错系统\运动姿态评估与纠错系统"

# 2. 启动后端 (端口 8002)
C:\Users\ALW\.conda\envs\dl\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8002

# 3. 启动前端 (端口 5173)
cd frontend
npm run dev
```

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI (Python) |
| 数据库 | MySQL (pymysql + SQLAlchemy) |
| 姿态检测 | YOLOv8-pose (ultralytics) |
| 前端框架 | React + TypeScript |
| UI 库 | Ant Design |
| 图表 | Recharts |
| 构建工具 | Vite |

## 文档

- [API 接口文档](./API.md) — 全部 REST + WebSocket 端点
- [修改日志](./CHANGELOG.md) — 版本变更记录

## 目录结构

```
运动姿态评估与纠错系统/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置（数据库/模型/CORS）
│   ├── routers/             # 路由层
│   │   ├── assessment.py    # 体态评估 API + WebSocket
│   │   ├── fms.py           # FMS 筛查 API + WebSocket（兼容保留）
│   │   ├── auth.py          # 认证
│   │   ├── prescription.py  # 训练处方
│   │   ├── training.py      # 训练记录
│   │   ├── learning.py      # 学习模块
│   │   ├── records.py       # 统计
│   │   ├── checkin.py       # 打卡
│   │   ├── coach.py         # 教练端
│   │   └── admin.py         # 管理端
│   ├── services/            # 业务逻辑层
│   │   ├── assessment_service.py  # 体态评估服务
│   │   ├── fms_service.py         # FMS 服务
│   │   └── ...
│   ├── database/
│   │   ├── models.py        # ORM 模型
│   │   └── connection.py    # 数据库连接
│   └── schemas/
│       └── business.py      # Pydantic 请求/响应模型
├── models/                  # 领域模型
│   ├── assessment/          # 体态评估引擎
│   │   ├── rom_tracker.py
│   │   ├── scoring.py
│   │   └── ...
│   ├── fms/                 # FMS 评分引擎（兼容层）
│   │   ├── scoring.py
│   │   ├── radar_report.py
│   │   └── problem_tagger.py
│   ├── posture_analyzer.py  # 静态体态分析
│   └── angle_calculator.py  # 关节角度计算
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── AssessmentPage.tsx      # 体态评估页
│       │   ├── AssessmentReportPage.tsx # 评估报告页
│       │   ├── FMSScreeningPage.tsx    # FMS 筛查页
│       │   └── ...
│       ├── store/           # Zustand 状态管理
│       └── api.ts           # Axios 请求封装
└── docs/                    # 本文档目录
    ├── README.md
    ├── API.md
    └── CHANGELOG.md
```

## 接入其他前端系统

1. **认证**：先调用 `POST /api/auth/login` 获取 JWT token
2. **请求头**：所有后续请求带 `Authorization: Bearer <token>`
3. **REST 接口**：标准 JSON 请求/响应，详见 [API.md](./API.md)
4. **WebSocket**：连接 `ws://<host>:8002/api/assessment/ws?token=<jwt>`，协议见 API.md
5. **CORS**：在 `backend/config.py` 的 `CORS_ORIGINS` 中添加新前端的域名