# v2 模块优化集成 — 2026-06-26

## 概述

从上游版本合入 FMS 筛查、前端展示、实时训练、处方训练四大模块的算法与 UI 优化。
在保留现有模块化架构（config/、shared/、ModelManager、BaseWebSocketHandler、多视角评估管线）的基础上，选择性合入逻辑优化。

---

## 新增功能

### 1. 处方训练（全新模块）

- **PrescriptionTrainingPage** — 多动作顺序训练流程
  - 处方选择（Dropdown 加载可用处方）
  - 按处方计划顺序执行多个动作
  - 每动作独立 WebSocket 连接，实时骨骼绘制 + 引导
  - 完成计数 & 错误历史收集
  - 完成当前动作后手动进入下一个
  - 支持中途停止（已完成动作结果保留）

- **PrescriptionTrainingReportPage** — 处方训练报告
  - 每动作独立评分分解（Vertical Steps 展示）
  - 统计卡片：平均分、总时长、完成动作数、总次数
  - 处方执行进度条
  - 全动作错误聚合 + 改善建议

**路由：** `/prescription-training` → `/prescription-training/report/:id`  
**导航：** 侧边栏「处方训练」（OrderedListOutlined，trainee 角色可见）

### 2. 训练报告（新页面）

- **TrainingReportPage** — 单次训练完整报告
  - 统计卡片：综合评分、训练时长、完成次数
  - 颜色编码成绩进度条（优秀绿 / 良好蓝 / 一般橙 / 需改进红）
  - 训练信息描述表（模式、动作、时间、次数）
  - 错误历史列表
  - 自适应改善建议

**路由：** `/training/report/:id`

### 3. 实时训练增强

- **TrainingPage 重写**：从处方依赖式 → 自包含动作选择式
  - 7 动作自由选择（深蹲/弓步蹲/俯卧撑/平板支撑/肩部推举/开合跳/硬拉）
  - 完成计数（检测 FSM complete 状态自动 +1）
  - 错误历史追踪（去重，最多保留 10 条）
  - 模式区分反馈面板：
    - 基础模式：安全/风险标签 + 按严重度分色警告（高红/中黄/低蓝）
    - 进阶模式：评分 + 质量标签 + 进度条 + 扣分列表（含扣分数值）
  - 结束训练自动跳转报告页

### 4. FMS 筛查增强

- **FMSScreeningPage**：测试指令添加评分标准（如"站立越久分数越高，满分60秒"）
- **FMSReportPage** 新增 3 个 UI 区块：
  - 各维度评分详情 — 颜色编码 Progress 条（>=80 优秀绿 / >=60 良好橙 / >=40 待改善 / <40 较差红）
  - 风险预警 Alert — 高/中/低三种样式，含具体建议
  - 个性化训练建议 — 蓝色圆形编号 + 描述

### 5. 新动作支持

- **jumping_jack（开合跳）** — FSM：standing → jumping_up → open → closing → complete
- **deadlift（硬拉）** — FSM：standing → lowering → bottom → lifting → complete
- 新增 `create_jumping_jack_fsm()` / `create_deadlift_fsm()` + context 映射 + guidance 文案

---

## 算法优化

### FMS 肩部评估（3 处方法增强）

| 方法 | 旧逻辑 | 新逻辑 |
|------|--------|--------|
| `_eval_shoulder` | 仅左手腕、`lw[1] < ls[1] + 50`、纯水平距离 | 双手检测（left_behind OR right_behind）、`lw[1] > ls[1] + 30`、加权距离 `vert*0.7 + horiz*0.3` |
| `_eval_shoulder_video` | 同上 | 同上 |
| `_eval_shoulder_single` | 同上 | 同上 |

### FMS 评分引擎增强

- `score_balance(duration_sec, sway_amplitude=0)` — 晃动惩罚：`min(30, sway * 2)`
- `score_core(duration_sec, hip_drop_angle=0)` — 臀降惩罚：`min(30, (angle-5) * 3)`
- `get_recommendations(scores)` — 新增方法，<40 高风险建议 / 40-60 改善建议
- 所有方法添加完整 docstring + 类型注解

### FMS 视频合并增强

`VideoFMSService.combine_results()` 现在生成：
- `radar_data` — 含 `dimensions`（中文标签）、`chart_data`、`suggestions`
- `problem_tags` — 基于分数阈值的自动问题标记（high/medium severity）
- 维度中文标签映射（平衡控制/下肢柔韧性/肩关节活动度/核心稳定性/左右对称性）

---

## 架构变更

### 数据库 Schema

| 表 | 变更 | 原因 |
|----|------|------|
| `training_record.prescription_id` | `INTEGER NOT NULL` → `INTEGER NULL` | 支持自由训练（不关联处方） |

### API Schema

| Schema | 变更 |
|--------|------|
| `TrainingStartRequest.prescription_id` | `int` → `Optional[int] = None` |
| `TrainingRecordResponse.prescription_id` | `int` → `Optional[int] = None` |

### 服务层

- `TrainingService.start_session()` — `prescription_id` 为 None/0 时跳过处方查询
- `TrainingWebSocketHandler._guidance_for_state()` — 新增 jumping_jack + deadlift 引导

### 全局存储

- `backend/services/fms_service.py` — 新增模块级 `_single_test_results_global` 字典，替代实例级 `self._single_test_results`，支持跨请求视频上传结果持久化

---

## 修改文件清单

### 后端（6 个）

| 文件 | 操作 | 说明 |
|------|------|------|
| `models/fms/scoring.py` | 增强 | +摇摆/臀降惩罚 + get_recommendations() + 类型注解 |
| `backend/services/fms_service.py` | 增强 | 全局存储 + 肩部算法 + 指令丰富 + combine_results() |
| `backend/services/training_service.py` | 增强 | prescription_id nullable + 2 新动作引导 |
| `backend/database/models.py` | Schema | TrainingRecord.prescription_id nullable=True |
| `backend/schemas/business.py` | Schema | TrainingStartRequest/Response prescription_id Optional |
| `models/action_recognizer/squat_fsm.py` | 增强 | +jumping_jack FSM + deadlift FSM + context |

### 前端（8 个）

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/pages/TrainingPage.tsx` | 重写 | 7 动作自选 + 计数 + 错误 + 反馈面板 + 报告导航 |
| `frontend/src/pages/TrainingReportPage.tsx` | **新建** | 训练统计报告页 |
| `frontend/src/pages/PrescriptionTrainingPage.tsx` | **新建** | 处方多动作训练页 |
| `frontend/src/pages/PrescriptionTrainingReportPage.tsx` | **新建** | 处方训练报告页 |
| `frontend/src/pages/FMSScreeningPage.tsx` | 增强 | 评分标准指令 + 摄像头优化 |
| `frontend/src/pages/FMSReportPage.tsx` | 增强 | 进度条 + 风险预警 + 编号建议 |
| `frontend/src/App.tsx` | 路由 | +3 条新路由 |
| `frontend/src/components/MainLayout.tsx` | 导航 | +「处方训练」菜单项 |

### 数据库

- MySQL `pose_correction.training_record` — `ALTER TABLE MODIFY prescription_id INTEGER NULL`

---

## 保留不受影响的高级功能

以下当前项目的模块化架构功能完整保留，未被降级：

| 模块 | 说明 |
|------|------|
| `models/engine.py` | ModelManager 线程安全单例 |
| `backend/services/base.py` | BaseWebSocketHandler 共享基类 |
| `models/assessment/multi_view_analyzer.py` | 三视角姿态分析 |
| `models/assessment/velocity_analyzer.py` | 速度不对称检测 |
| `models/assessment/fusion_engine.py` | 静态+ROM+速度多证据融合 |
| `models/assessment/verification_mapper.py` | 问题→验证动作映射 |
| `models/assessment/multi_view_session.py` | 多视角会话存储 |
| `backend/services/assessment_service.py` | VerificationWebSocketHandler + 三视角采集 |
| `backend/routers/multi_view_assessment.py` | 多视角 REST 端点 |
| `shared/image_utils.py` | 共享图像解码工具 |
| `shared/scoring_utils.py` | 共享评分工具 |
| `config/settings.py` | 模块化配置（MySQL 默认） |

---

## 前后端协议变更

### `/api/training/start` 请求体

```json
// 旧：prescription_id 必填
{ "prescription_id": 1, "mode": "basic" }

// 新：prescription_id 可选（null = 自由训练）
{ "prescription_id": null, "mode": "basic" }
```

### `/api/fms/upload-video-combine` 响应体新增字段

```json
{
  "radar_data": {
    "dimensions": [{"dimension": "balance", "label": "平衡控制", "score": 75}],
    "chart_data": {"labels": ["平衡控制"], "values": [75]},
    "suggestions": ["平衡能力较弱，建议增加..."]
  },
  "problem_tags": [{"name": "平衡控制", "description": "...", "severity": "medium"}]
}
```
