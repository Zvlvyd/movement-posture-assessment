# 更新日志

## 2026-07-01 — 标准动作库数据标准化 & 教练端 UI 修复

### 数据标准化：标准动作角度库重构

**`models/knowledge/standard_actions.json` — 完全重写（v2.0）**
- 动作数量：5 → **16 个**标准角度动作
- 命名统一：与 `action_library.json` 对齐（"深蹲"→"标准深蹲"、"俯卧撑"→"标准俯卧撑"等）
- 分类体系统一：从 3 类（下肢/上肢/核心）扩展为 **8 类标准分类**：
  - `上肢推`（俯卧撑、肩部推举）
  - `上肢拉`（Y/T/W 字举、反向平板）
  - `下肢蹲`（深蹲、弓步蹲、保加利亚分腿蹲）
  - `下肢拉`（臀桥、单腿臀桥、单腿罗马尼亚硬拉）
  - `核心抗伸展`（平板支撑、死虫式、鸟狗式、登山者）
  - `核心抗侧屈`（侧平板）
  - `颈部矫正`（收下巴、靠墙天使）
  - `拉伸`（猫牛式）
- 每个动作补充 `family` 和 `family_name` 字段，与 `action_library.json` 10 个家族对齐
- 新增 11 个动作的标准角度定义：臀桥、单腿臀桥、鸟狗式、死虫式、标准侧平板、保加利亚分腿蹲、单腿罗马尼亚硬拉、靠墙天使、猫牛式、登山者（慢速控制）、反向平板

### 数据标准化：体态问题标签中文化

**`backend/database/seed.py`**
- `ProblemTag` 种子数据修复：`name` 从英文 key（`head_forward_posture`）改为中文显示名（`头前倾`）
- 自动迁移已有旧数据：检测英文命名记录并重命名为中文
- 描述字段调整为 `[英文key] 成因说明` 格式

### 新功能：TagActionMapping 自动种子

**`backend/database/seed.py`**
- 新增 TagActionMapping 种子逻辑：从 `action_library.json` 的 `problem_mapping` 自动创建动作→体态问题关联
- 按 `relevance_score` 过滤（仅映射相关性 > 0 的动作-问题对）
- 幂等设计：已存在的映射不重复创建
- 覆盖 55 个动作 × 7 个体态问题的完整关联网络

### 数据标准化：练习分类统一

**`backend/database/seed.py`**
- exercises.json 种子分类修正：`体态-stretch` → `拉伸`、`体态-strength` → `体态矫正`
- 与 action_library.json 分类体系保持一致

### 修复：教练端导航菜单高亮错误

**`frontend/src/components/MainLayout.tsx`**
- 修复 `selectedKey` 计算逻辑：`"/" + pathname.split("/")[1]` → 优先完整路径匹配
- 访问 `/coach/actions` 时正确高亮「动作库管理」而非「教练工作台」
- 无直接菜单项的路由（如 `/coach/student/42`）回退到父级菜单高亮

### 向后兼容

**`backend/services/learning_service.py`**
- `UnifiedActionLoader` 新增 `_name_aliases` 别名映射（深蹲→标准深蹲、俯卧撑→标准俯卧撑、平板支撑→标准平板支撑）
- `get_standard_data()`、`get_merged_action()`、`get_by_name()`、`get_views()` 全部支持别名解析
- 确保旧名称请求和书签不会报错

---

## 2026-07-01 — FMS 筛查 & 体态评估逻辑优化（从 program3 合并）

### 优化：FMS 肩关节活动度评估算法升级

**`backend/services/fms_service.py`**
- 检测阈值降低：`30px → 20px`（更灵敏地检测手在背后姿态）
- 距离度量升级：加权像素距离（`vert*0.7 + horiz*0.3`） → 基于肩宽校准的厘米级欧几里得距离（`np.linalg.norm`）
- 肩宽标定：`px_to_cm = 38.0 / max(shoulder_width_px, 1)`（假设平均肩宽 38cm，像素→厘米映射）
- 最佳距离选择：全量平均 → 取最优 1/3（`sorted(dists)[:max(3, len(dists)//3)]`），排除异常帧干扰
- 回退距离：`100px → 60.0cm`
- 变量命名规范化：`behind` → `any_behind`

**`models/fms/scoring.py`**
- `score_upper_limb()` 公式修正：`(1.0 - distance_cm / 20.0)` → `(1.0 - distance_cm / 200.0)`（配合厘米级距离输入）
- 标签更新：`"背后触肩距"` → `"背后双手距"`
- **注意**：公式与算法变更必须同步部署，否则评分异常

### 新增：FMS 分析集中函数 `build_fms_analysis()`

**`backend/services/fms_service.py`**
- 新增模块级函数 `build_fms_analysis(score_map: dict) -> dict`
- 集中管理 FMS 五个维度的标签、详情、建议、问题描述
- 从动作库 JSON 按关键词匹配推荐动作（每个维度 3 个最佳匹配）
- 消除 REST（`get_record_detail`）和 WebSocket（`_send_final_result`）两处 ~55 行重复的维度元数据代码
- `get_record_detail()` 返回值新增 `problem_detail`、`recommended_actions` 等富文本字段
- `_send_final_result()` 简化为单行 `analysis = build_fms_analysis(score_map)` 调用

### 新增：骨架标注视频实时渲染

**`backend/services/fms_service.py`**
- `process_single_test_video()` 新增骨架视频渲染：边处理边输出带关键点标注的视频
- `cv2.VideoWriter` 输出 mp4v/avc1 编码，分辨率 ≤960px 等宽缩放
- ~10fps 骨架更新速率（`render_skip = max(1, int(fps / 10))`），无骨架帧复用最近有效数据
- 测试完成后**不中断**渲染，持续输出完整视频（`_rendering_done` 标志位）
- 返回 `processed_video_url` 字段（文件 >1000 字节才返回有效 URL）
- 视频结束处理新增肩关节测试（test_index == 2）自动计分

**`backend/routers/fms.py`**
- 新增 `GET /api/fms/processed-video/{filename}` 端点
- 安全校验：仅允许 `processed_` 前缀文件，拦截 `..` 路径遍历

**`frontend/src/pages/FMSReportPage.tsx`**
- 维度评分卡片新增低分高亮（分数 < 50 橙色背景 + 边框）
- 新增 `⚠️ 问题分析` 区域（展示 `problem_detail` 字段）
- 新增 `🎯 推荐训练动作` 标签（展示 `recommended_actions`，含难度等级）
- 测试指标前添加 `📊` 前缀，训练建议标签统一为「训练建议」
- 标题"综合评分" → "功能性动作评分"

**`frontend/src/pages/fms/FMSDashboard.tsx`**
- 列标题"总分" → "功能性动作评分"，宽度 60 → 100

### 优化：YOLO 模型 WebSocket 预加载

**`models/engine.py`**
- `ModelManager` 新增 `preload()` 公开方法，供 WebSocket 连接时提前加载模型

**`backend/services/fms_service.py`**
- `RealtimeFMSService.handle_session()` "start" 处理器中调用 `model_manager.preload()`

**`backend/services/assessment_service.py`**
- `RealtimeAssessmentService.handle_session()` "start" 处理器中调用 `model_manager.preload()`
- `VerificationWebSocketHandler.handle()` "start" 处理器中调用 `model_manager.preload()`

### 配置变更

**`config/settings.py`**
- `DEEPSEEK_MODEL` 默认值：`deepseek-v4-flash` → `deepseek-v4-pro`

### 代码质量

### 修复：FMS 动作切换后骨架冻结

**`backend/services/fms_service.py`**
- `handle_session()` 帧处理逻辑修复：`awaiting_user` 状态不再完全跳过帧处理，改为提取关键点并以 `fms_status: "observing"` 发送给前端，仅跳过 FMS 评分评估
- **原因**：原逻辑在 `awaiting_user` 状态直接 `continue` 跳过全部处理，前端收不到新骨架数据，摄像头画面停留在上一动作的骨架直到点击"准备好了"

### 代码质量

- 导入整理：`fms_service.py` 新增 `os` 模块导入
- 三处肩关节评估函数（`_eval_shoulder` / `_eval_shoulder_video` / `_eval_shoulder_single`）算法统一
- 移除未使用的 `le`/`re` elbow 变量（已不参与新算法计算）

### 修复：FMS 报告查看失败

**`backend/schemas/business.py`**
- `FMSResultResponse` 模型新增 `model_config = {"from_attributes": True, "extra": "allow"}`
- 所有评分字段改为 `Optional[float]`（兼容数据库 NULL 值）
- 新增字段：`scores`、`recommendations`、`posture_problems`、`completed_count`、`skipped_count`
- **原因**：Pydantic v2 默认禁止 `setattr` 设置未定义字段，`get_record_detail()` 中 `setattr(result, "scores", ...)` 直接抛出 `ValueError` 导致所有报告查看失败

---

## 2026-07-01 — 标准学习模块完善 & 追踪优化

### 新功能：标准学习模块增强（从 program3 合并）

**后端 `backend/services/learning_service.py`**
- 新增 `get_merged_action()` 方法：合并 `action_library.json` 和 `standard_actions.json` 两个数据源
- `get_by_name()` 添加回退逻辑：支持仅存在于 `standard_actions.json` 的动作
- `list_learnable_actions()` 双数据源合并去重，返回完整 `common_errors` 字典 + `video_url`
- `get_action_detail()` 使用 `get_merged_action()` 查询
- 新增自动完成功能：连续 30 帧得分 ≥ 85 自动触发学习完成
- 新增人体检测验证：至少 10 个关键点置信度 ≥ 0.15 才进入学习阶段
- 新增 Session 阶段跟踪：`waiting_for_body` → `body_confirmed` → `learning`
- 新增 `_save_learning_record()` 辅助方法：提取为独立方法，手动/自动完成共用
- comparison 消息新增 `user_keypoints`、`user_confidences`、`session_phase`、`frame_width`、`frame_height` 字段
- 新增 `body_confirmed` 消息类型：人体确认后通知前端

**前端 `frontend/src/pages/LearningPage.tsx`**
- 新增 `"demo"` 演示模式：先看动作示范再进入实时学习
- 集成 `MovementDemo` 组件（SVG 骨架示范）
- 合并 learnable-only 动作到列表（来自 `standard_actions.json` 但不在 DB 中的动作）

**前端 `frontend/src/components/TrainingSessionPanel.tsx`**
- 集成 `SkeletonOverlay` 骨架叠加层
- 新增 Session 阶段徽章（等待检测 / 已确认 / 分析中）
- 新增自动完成庆祝模态框
- 新增摄像头恢复 useEffect

**前端 `frontend/src/hooks/useTrainingSession.ts`**
- 新增 `autoCompleted`、`userKeypoints`、`userConfidences`、`frameWidth`、`frameHeight`、`sessionPhase` 状态
- 新增 `confirmAutoComplete` 动作
- 新增 `body_confirmed` WebSocket 消息处理
- 错误时自动清理摄像头和 WebSocket 资源

**前端 `frontend/src/types/index.ts`**
- 新增 `BodyConfirmed` 接口
- `LearningComparison` 添加 `user_keypoints`、`user_confidences`、`session_phase`、`frame_width`、`frame_height`
- `LearningComplete` 添加 `auto_triggered`
- `LearnableAction` / `LearnableActionDetail` 添加 `video_url`、`thumbnail_url`

### 修复：YOLO 模型预加载

**`backend/main.py`**
- 启动时预加载 YOLO 模型（`on_startup` 事件），避免首次打开摄像头等待 3-10 秒
- 禁用 Ultralytics 在线同步检查（`sync: false, hub: false`）

### 修复：人体追踪稳定性优化

**`models/angle_calculator.py`**
- `get_kp()` 置信度阈值 `0.3 → 0.15`，与 body detection 阈值对齐

**`models/engine.py`**
- `get_keypoints()` / `get_multi_keypoints()` 新增 `conf` 参数，支持自定义 YOLO 检测置信度
- `get_keypoints_from_b64()` 传递 `conf` 参数

**`backend/services/base.py`**
- `extract_keypoints()` / `extract_keypoints_from_b64()` / `extract_multi_keypoints()` / `extract_keypoints_from_msg()` 全部新增 `conf` 参数

**`backend/services/learning_service.py`**
- 新增 `YOLO_CONF_THRESHOLD = 0.15`（低于 Ultralytics 默认 0.25，提高部分遮挡检出率）
- 帧处理使用 `extract_keypoints_from_msg(msg, conf=0.15)`

**前端**
- `useTrainingSession.ts`：帧间隔 `150ms → 200ms`（与 FMS 对齐 5fps），JPEG 质量 `0.7 → 0.6`
- `SkeletonOverlay.tsx`：新增置信度过滤（`MIN_CONFIDENCE = 0.15`），低置信度关键点不绘制

### 修复：骨架坐标偏移

**后端 `backend/services/learning_service.py`**
- comparison 消息新增 `frame_width`、`frame_height`（YOLO 推理时的实际帧尺寸）

**前端 `frontend/src/components/SkeletonOverlay.tsx`**
- 新增 `frameWidth` / `frameHeight` props
- 计算 `scaleX = canvasW / frameW`、`scaleY = canvasH / frameH`
- 所有关键点绘制前按比例缩放，消除坐标空间不匹配导致的偏移

### 修复：`_compare_angles()` 默认值

**`backend/services/learning_service.py`**
- 未知关节默认值修正：`optimal: 0 → 90`、`min: 0`、`max: 0 → 180`

### 修复：`_generate_summary()` 模板兼容

**`backend/services/learning_service.py`**
- 摘要模板替换兼容 `{value}°` 和 `{value}` 两种格式

### 配置更新

**`.env`**
- `DB_PASSWORD` 更新为 `Zly20050708`

---

## 2026-07-01 — 管理员端 & 教练端大规模功能改造

### 数据库变更

**`backend/database/models.py`**
- `User` 表新增字段：`last_login_at`、`last_active_at`、`deleted_at`（软删除）
- `ActionLibrary` 表新增字段：`steps`、`cues`、`contraindications`、`family`、`family_name`、`is_custom`、`created_by`、`updated_at`；`target_body_parts` 从 `String(200)` 改为 `Text`
- 新增 `ActionMedia` 表：存储动作的图片/视频示例
- 新增 `SystemConfig` 表：系统运行时配置

**`backend/database/connection.py`**
- 新增 `run_migrations()` 自动迁移函数：检测已有表中缺失的列并自动 ALTER TABLE 补充

**`backend/database/seed.py`**
- `seed_action_library()` 重写：从 `action_library.json` 加载 55+ 动作到 DB，自动补充已有记录缺失字段，只插入不存在的记录保证幂等
- 新增 `seed_system_config()`：初始化系统配置默认值

### 新功能：管理员端

**后端 `backend/services/admin_service.py` — 完全重写**
- `list_users()`：支持 role/status/search 筛选 + 分页 + 包含已删除
- 新增 `soft_delete_user()` / `restore_user()`：软删除机制
- 新增 `get_user_detail()`：用户完整档案（FMS/评估/处方/打卡统计）
- 新增 `get_dashboard_stats()`：系统仪表板（总用户/DAU/WAU/MAU/注册趋势/API 统计/错误率）
- 新增 `get_storage_info()`：存储空间使用统计
- 新增 `update_system_config()`：运行时编辑配置（白名单保护）
- 新增 `export_users_csv()` / `export_logs_csv()`：CSV 导出
- 新增 `batch_operation()`：批量激活/停用/改角色

**后端 `backend/routers/admin.py` — 完全重写**
- 新增 10 个端点：用户详情/软删除/恢复/仪表板/配置编辑/存储/导出/批量操作

**前端 `frontend/src/pages/AdminPage.tsx` — 重构为 4 Tab**
- Tab 1 用户管理：搜索/筛选/分页/软删除/恢复/批量操作/导出（`UserManagementTab.tsx`）
- Tab 2 系统仪表板：用户增长趋势图/角色分布饼图/DAU/WAU/MAU/API 统计（`DashboardTab.tsx`）
- Tab 3 系统配置：可编辑表格，白名单保护（`ConfigTab.tsx`）
- Tab 4 操作日志：搜索/筛选/导出（`LogsTab.tsx`）
- 新增图表组件：`RegistrationTrend`、`RoleDistribution`、`ActiveUsersChart`（基于 Recharts）

### 新功能：教练端班级管理增强

**后端 `backend/services/coach_service.py`**
- 新增 `remove_student_from_class()`：从班级移除学员
- 新增 `update_class()` / `delete_class()`：编辑/删除班级
- 新增 `get_student_prescription_plans()` / `delete_student_prescription_plan()`：查看/删除学员 v2 训练计划
- 新增 `_verify_coach_access()`：权限验证辅助函数

**后端 `backend/routers/coach.py`**
- 新增 7 个端点：移除学员/编辑班级/删除班级/学员计划列表/计划详情/删除计划

**前端 `frontend/src/pages/CoachPage.tsx`**
- 学员进度表新增「移除」按钮（Popconfirm 确认）
- 班级详情视图新增「编辑班级」「删除班级」按钮
- 新增编辑班级 Modal

**前端 `frontend/src/pages/StudentDetailPage.tsx`**
- 新增「训练计划 V2」Tab：展示 PrescriptionPlan 列表 + 展开详情 + 删除按钮

### 新功能：教练端标准动作库管理

**后端 `backend/services/action_library_service.py` — 新建独立服务**
- `get_merged_action_library()`：三源合并（DB + action_library.json + standard_actions.json），支持分页筛选
- `get_action_detail_unified()`：统一动作详情（支持 int DB id 或 str JSON id）
- `update_action_metadata()`：编辑动作元数据
- `create_custom_action()`：教练自定义动作
- `upload_action_media()`：上传图片/视频/缩略图，自动更新 thumbnail_url/video_url
- `delete_action_media()`：删除媒体文件及物理文件
- `_merge_action()`：DB > JSON 优先级的字段合并引擎

**后端 `backend/routers/coach_actions.py` — 新建路由**
- 6 个端点：动作列表/详情/更新/创建/上传媒体/删除媒体
- 文件验证：扩展名白名单 + 大小限制（图片 10MB / 视频 100MB）
- 自动重命名：`{action_id}_{media_type}_{uuid8}.{ext}`

**后端 `backend/main.py`**
- 挂载 `/media/uploads/actions` → `uploads/actions/` 静态文件服务
- 注册 `coach_actions` 路由

**前端 `frontend/src/pages/coach/ActionLibraryPage.tsx` — 新建**
- 左侧筛选面板：搜索/分类/家族/难度/目标部位
- 右侧卡片网格：缩略图/名称/标签/来源标记（系统 vs 自定义）
- 动作详情 Modal：基本信息/步骤时间线/要领标签/禁忌症/标准角度（只读预览 + 编辑模式）
- 媒体管理 Panel：缩略图/示例图片/示例视频三个 Tab，集成 MediaUpload
- 新建自定义动作 Modal

**前端 `frontend/src/components/MediaUpload.tsx` — 新建**
- Ant Design Upload 封装：拖拽/进度条/图片预览/视频预览
- 上传前验证：文件类型 + 大小限制
- 删除确认 Modal

**前端 `frontend/src/components/ScoreBar.tsx` — 新建共享组件**
- FMS 评分迷你进度条（提取自 CoachPage 和 StudentDetailPage 的重复代码）

**前端 `frontend/src/utils/riskColor.ts` — 新建共享工具**
- 风险等级颜色映射（提取自多个页面的重复定义）

### 新功能：侧边栏角色差异化

**`frontend/src/components/MainLayout.tsx`**
- 菜单按角色区分：学员/教练/管理员三种菜单
- 教练菜单 = 学员菜单 + 教练工作台 + 动作库管理
- 管理员菜单 = 教练菜单 + 系统管理
- 头像下拉菜单简化为仅「个人中心」+「退出登录」

### 新功能：标准学习关联动作库媒体

**后端 `backend/services/learning_service.py`**
- `LearningService` 新增 `db` 参数，新增 `_get_db_override()`：查询 DB 中教练编辑的媒体和描述
- `list_learnable_actions()` / `get_action_detail()` 使用 DB > JSON 优先级合并数据
- 返回值新增 `media` 列表字段（包含所有上传的图片/视频）

**后端 `backend/routers/learning.py`**
- `/learnable` 和 `/learnable/{name}` 端点传入 DB session

**前端 `frontend/src/pages/LearningPage.tsx`**
- Demo 页展示逻辑升级：优先使用 `media` 数组中的图片/视频 → `thumbnail_url` → SVG 占位
- 图片/视频加载失败时自动回退到 SVG 骨架图（`mediaFailed` 状态）

**前端 `frontend/vite.config.ts`**
- 新增 `/media/uploads` 代理规则，转发到后端 8002 端口

### 修复与优化

- **修复**：`target_body_parts` 列类型 `String(200)` → `Text`（防止 JSON 截断）
- **修复**：`image` 类型上传也自动更新 `thumbnail_url`（之前仅 `thumbnail` 类型）
- **修复**：Demo 页图片加载失败时静默隐藏 → 回退 SVG 占位图
- **修复**：编辑按钮竞态（等 API 返回再打开编辑表单）
- **修复**：卡片高度不一致（Col 包裹 + flexbox + 固定最小高度）
- **架构**：动作库功能从 coach_service.py（~1007 行）拆分为独立的 `action_library_service.py`（~450 行）
- **消除重复**：ScoreBar 组件、riskColor 工具提取为共享文件
- **清理**：移除未使用的导入、修正 async/def 不一致

### 文件存储

| 类型 | 路径 | 访问方式 |
|------|------|----------|
| 系统内置动作媒体 | `frontend/public/media/actions/` | Vite 直接提供 |
| 教练上传的动作媒体 | `uploads/actions/` | FastAPI StaticFiles → `/media/uploads/actions/` |
| 数据库路径 | `ActionMedia.file_path`（仅文件名） | 前端拼接完整 URL |

### 新增文件清单

```
backend/services/action_library_service.py  # 动作库管理服务
backend/routers/coach_actions.py            # 动作库 API 路由
frontend/src/pages/admin/UserManagementTab.tsx
frontend/src/pages/admin/DashboardTab.tsx
frontend/src/pages/admin/ConfigTab.tsx
frontend/src/pages/admin/LogsTab.tsx
frontend/src/pages/admin/charts/RegistrationTrend.tsx
frontend/src/pages/admin/charts/RoleDistribution.tsx
frontend/src/pages/admin/charts/ActiveUsersChart.tsx
frontend/src/pages/coach/ActionLibraryPage.tsx  # 动作库管理页面
frontend/src/components/MediaUpload.tsx          # 媒体上传组件
frontend/src/components/ScoreBar.tsx             # 共享评分条
frontend/src/utils/riskColor.ts                  # 共享风险等级
diagnose_thumbnail.py                            # 图片上传诊断+修复脚本
