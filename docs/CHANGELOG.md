# 修改日志

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