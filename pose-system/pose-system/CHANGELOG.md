# 运动姿态评估与纠错系统 — 变更日志

> 会话日期：2026-07-03  
> 分支：班级邀请码 + 计划审批工作流 + 消息通讯  
> 基于：`d:\workbench\program\code_701_2 (1)\code_701_2\code\pose-system\pose-system`

---

## 功能概述

本次迭代包含四大模块：

1. **班级邀请码机制** — 教练创建班级自动生成邀请码，学员通过邀请码自主加入
2. **AI 训练计划修改与审批流程** — 有班级的学员修改计划需教练审批，无班级学员直接生效
3. **消息通讯系统** — 学员与教练之间的非实时消息，支持围绕计划变更的上下文对话
4. **UI 增强** — 侧边栏未读/待审批红色气泡角标、计划编辑支持增删动作

---

## 后端变更

### 一、数据库模型新增

#### 1.1 `backend/database/models.py` — 修改

**ClassGroup 新增字段：**
```python
invite_code = Column(String(10), unique=True, nullable=True, index=True, comment="班级邀请码")
```
- 位置：ClassGroup 模型（~L244），在 `description` 后、`created_at` 前
- 用于存储 8 位唯一邀请码（大写字母+数字）

**新增模型 PlanChangeRequest：**
```python
class PlanChangeRequest(Base):
    __tablename__ = 'plan_change_request'
    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey('prescription_plan.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    coach_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    status = Column(String(20), default='pending')       # pending/approved/rejected/adjusted
    original_snapshot = Column(Text)                      # JSON: 修改前快照
    proposed_items = Column(Text)                          # JSON: 学员提交版本
    coach_items = Column(Text, nullable=True)              # JSON: 教练调整后版本
    coach_notes = Column(Text)                             # 教练留言
    student_notes = Column(Text)                           # 学员留言（修改原因）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```
- 位置：SystemLog 之后、文件末尾
- 关系：`student` -> User (student_id), `coach` -> User (coach_id)

**新增模型 Message：**
```python
class Message(Base):
    __tablename__ = 'message'
    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    receiver_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    related_type = Column(String(20), nullable=True)       # 'change_request' 等
    related_id = Column(Integer, nullable=True)             # 关联实体 ID
    created_at = Column(DateTime, default=datetime.utcnow)
```
- 关系：`sender` -> User (sender_id), `receiver` -> User (receiver_id)

#### 1.2 `backend/database/connection.py` — 修改

**run_migrations() 新增迁移逻辑：**

1. class_group 表 invite_code 列迁移：
   - 新增 `VARCHAR(10)` 列
   - 为已有班级自动生成 8 位邀请码（secrets.choice）
   - 创建唯一索引 `idx_class_group_invite_code`

2. plan_change_request 表创建：
   - CREATE TABLE IF NOT EXISTS（含所有列 + 外键约束）
   - 兼容 MySQL AUTO_INCREMENT 语法

3. message 表创建：
   - CREATE TABLE IF NOT EXISTS（含所有列 + 外键约束）
   - 兼容 MySQL AUTO_INCREMENT 语法

---

### 二、新增后端服务

#### 2.1 `backend/services/student_class_service.py` — **新建**

学员班级操作业务逻辑，215 行：

| 函数 | 说明 |
|------|------|
| `_generate_invite_code()` | 生成 8 位随机大写字母+数字 |
| `_generate_unique_invite_code(db)` | 带碰撞重试的唯一邀请码生成（最多10次） |
| `_serialize_class_for_student(group)` | 序列化班级为学员视角字典（含教练信息+学员人数） |
| `join_class_by_code(db, student, invite_code)` | 通过邀请码加入班级；验证码有效性、防重复加入 |
| `list_my_classes(db, student)` | 列出学员已加入的班级（通过 class_group_student 关联表 JOIN） |
| `get_my_class_detail(db, student, class_id)` | 获取班级详情（含权限校验） |
| `leave_class(db, student, class_id)` | 退出班级 |

#### 2.2 `backend/services/plan_edit_service.py` — **新建**

计划修改与审批业务逻辑，310 行：

| 函数 | 说明 |
|------|------|
| `_check_in_class(db, student)` | 检查学员是否在班级中，返回教练对象（无班级返回 None） |
| `_snapshot_items(plan)` | 创建计划项 JSON 快照 |
| `_apply_items(db, plan, items_data)` | 替换计划全部项（先删后建，status->draft） |
| `edit_plan(db, student, plan_id, data)` | 计划编辑入口；在班级则创建审批请求，无班级直接生效 |
| `submit_change_request(db, student, plan_id, notes)` | 显式提交审批（自动发消息通知教练） |
| `list_my_change_requests(db, student)` | 学员查看自己的变更请求列表 |
| `list_coach_change_requests(db, coach, status)` | 教练查看待审批列表（默认 pending） |
| `get_change_request_detail(db, coach, cr_id)` | 教练查看单个请求详情 |
| `approve_change_request(db, coach, cr_id)` | 通过 — 直接应用学员提交的 proposed_items |
| `adjust_change_request(db, coach, cr_id, items, notes)` | 调整后通过 — 应用教练修改后的 items |
| `reject_change_request(db, coach, cr_id, notes)` | 拒绝 — 通知学员原因 |
| `_serialize_cr(cr)` | 序列化变更请求为字典 |

**审批逻辑决策树：**
```
edit_plan()
  → _check_in_class() == None → 直接 apply → status='applied'
  → _check_in_class() == coach → 创建 PlanChangeRequest(status='pending')
                                   → 自动创建 Message 通知教练
                                   → status='pending'
```

#### 2.3 `backend/services/message_service.py` — **新建**

消息通讯业务逻辑，130 行：

| 函数 | 说明 |
|------|------|
| `send_message(db, sender, receiver_id, content, related_type, related_id)` | 发送消息 |
| `list_conversations(db, user, page, page_size)` | 会话列表（聚合每个对话伙伴+最新消息+未读数） |
| `get_messages_with(db, user, partner_id, page, page_size)` | 获取与某用户的对话（自动标记对方消息已读） |
| `get_unread_count(db, user)` | 总未读消息数 |
| `mark_read(db, user, message_id)` | 标记单条消息已读 |

#### 2.4 `backend/services/coach_service.py` — 修改

| 函数 | 变更 |
|------|------|
| `_generate_unique_invite_code(db)` | **新增** — 邀请码生成工具函数（已从 student_class_service 复用） |
| `create_class(db, coach, name, description)` | 调用 `_generate_unique_invite_code` 自动生成邀请码 |
| `list_classes(db, coach)` | 返回字典新增 `invite_code` 字段 |
| `regenerate_invite_code(db, coach, class_id)` | **新增** — 重新生成邀请码（旧码失效） |
| `get_student_prescription_plans(db, student_id, coach)` | 返回数据新增 `items` 数组（含 completions + latest_score），不再只返回 item_count |
| `get_student_profile(db, student_id, coach)` | **移除** `prescriptions` 字段（V1 旧版训练处方已废除） |

---

### 三、新增/修改路由

#### 3.1 `backend/routers/student_class.py` — **新建**

前缀：`/api/class`

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/join` | 通过邀请码加入班级 | trainee |
| GET | `/my-classes` | 查看我已加入的班级 | trainee |
| GET | `/my-classes/{class_id}` | 查看班级详情 | trainee |
| DELETE | `/my-classes/{class_id}/leave` | 退出班级 | trainee |

#### 3.2 `backend/routers/message.py` — **新建**

前缀：`/api/messages`

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `` | 获取会话列表 | all auth |
| GET | `/unread-count` | 获取未读消息数 | all auth |
| GET | `/with/{partner_id}` | 获取与某用户的对话 | all auth |
| POST | `` | 发送消息（query: receiver_id, content） | all auth |
| PUT | `/{message_id}/read` | 标记已读 | all auth |

#### 3.3 `backend/routers/prescription_v2.py` — 修改

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| PUT | `/plans/{plan_id}` | 修改计划（body: _PlanEditBody） | all auth |
| POST | `/plans/{plan_id}/submit-change` | 显式提交审批 | all auth |
| GET | `/change-requests` | 查看自己的变更请求 | all auth |

内部新增 Pydantic 模型：
```python
class _PlanEditBody(BaseModel):
    plan_name: Optional[str] = None
    overall_strategy: Optional[str] = None
    items: Optional[list] = None
    student_notes: Optional[str] = None
```

#### 3.4 `backend/routers/coach.py` — 修改

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/classes/{class_id}/regenerate-code` | 重新生成邀请码 | coach/admin |
| GET | `/change-requests` | 查看待审批的变更请求 | coach/admin |
| GET | `/change-requests/{cr_id}` | 查看变更请求详情 | coach/admin |
| PUT | `/change-requests/{cr_id}/approve` | 通过审批 | coach/admin |
| PUT | `/change-requests/{cr_id}/adjust` | 调整后通过（body: items + coach_notes） | coach/admin |
| PUT | `/change-requests/{cr_id}/reject` | 拒绝（body: coach_notes） | coach/admin |

#### 3.5 `backend/main.py` — 修改

- 新增导入：`from backend.routers.student_class import router as student_class_router`
- 新增导入：`from backend.routers.message import router as message_router`
- 新增注册：`app.include_router(student_class_router)`
- 新增注册：`app.include_router(message_router)`

---

### 四、新增 Schema

#### 4.1 `backend/schemas/student_class.py` — **新建**

```python
JoinClassRequest, CoachBriefResponse, MyClassResponse,
MyClassListResponse, JoinClassResponse, LeaveClassResponse, RegenerateCodeResponse
```

#### 4.2 `backend/schemas/plan_edit.py` — **新建**

```python
PlanItemEdit, PlanEditRequest, PlanSubmitRequest,
ChangeRequestResponse, ChangeRequestListResponse,
CoachApproveRequest, CoachAdjustRequest, CoachRejectRequest
```

---

## 前端变更

### 一、类型定义

#### 1.1 `frontend/src/types/index.ts` — 修改

新增类型（在原文件末尾追加）：
```typescript
// 班级相关
CoachBrief, MyClassInfo, MyClassListResponse, JoinClassResponse

// 消息相关
Conversation, ConversationListResponse, MessageItem, MessageWithResponse

// 计划变更相关
ChangeRequestItem, ChangeRequestListResponse
```

---

### 二、API 模块

#### 2.1 `frontend/src/services/api.ts` — 修改

**新增 `studentClassApi` 模块：**
```typescript
join(invite_code), myClasses(), classDetail(id), leaveClass(id)
```

**新增 `messageApi` 模块：**
```typescript
conversations(page), unreadCount(), getWith(partnerId),
send(receiverId, content), markRead(messageId)
```

**新增 `planEditApi` 模块：**
```typescript
edit(planId, data), submitChange(planId, notes), myChangeRequests()
```

**`coachApi` 新增方法：**
```typescript
regenerateCode(classId),
listChangeRequests(status), getChangeRequest(crId),
approveChangeRequest(crId), adjustChangeRequest(crId, items, notes),
rejectChangeRequest(crId, notes)
```

---

### 三、新建页面

#### 3.1 `frontend/src/pages/MyClassesPage.tsx` — **新建**（240 行）

学员「我的班级」页面：
- **空状态**：Empty 组件 + "加入班级，获取更专业指导" + 加入按钮
- **加入弹窗**：Modal + Input（自动转大写、8 位、monospace 字体）+ 错误提示
- **已加入列表**：Card 列表，展示班级名、教练信息（用户名+手机）、学员人数、邀请码 Tag
- **操作**：复制邀请码、退出班级（Popconfirm 二次确认）

#### 3.2 `frontend/src/pages/MessagesPage.tsx` — **新建**（210 行）

消息中心页面：
- **左侧对话列表**（320px 固定宽度）：Avatar + 角色标签 + 最新消息预览 + 未读 Badge
- **右侧消息详情**：气泡样式对话（我方蓝色靠右、对方灰色靠左）+ 时间戳
- **发送区域**：Input.TextArea（Enter 发送、Shift+Enter 换行）+ 发送按钮
- **自动轮询**：每 30 秒刷新未读计数
- **点击对话**：自动标记对方消息为已读

#### 3.3 `frontend/src/pages/coach/PlanReviewPage.tsx` — **新建**（240 行）

教练计划审批页面：

**列表视图：**
- Table：学员名、计划名、状态 Tag（pending=橙/approved=绿/rejected=红/adjusted=蓝）、时间
- 点击行 → 进入详情

**详情视图：**
- 学员留言展示（黄色背景卡）
- 左右对比：「修改前」原始快照 vs 「修改后」计划项
- 教练调整：InputNumber 内联编辑（sets/reps/duration_seconds 可改）
- 教练留言输入区
- 三个操作按钮：通过 / 调整后通过 / 拒绝
- 拒绝弹窗：必填原因 TextArea
- 已处理请求：显示教练留言（红色背景表示拒绝、蓝色背景表示调整）

---

### 四、页面修改

#### 4.1 `frontend/src/pages/PrescriptionPage.tsx` — 修改

**新增功能：计划编辑弹窗**

- 历史计划表新增「编辑」按钮（操作列从 3 个按钮扩展为 4 个）
- 编辑 Modal（width=900）：
  - 计划名称 Input
  - 修改原因 TextArea（提示：有班级将提交审批）
  - 计划动作表格（可编辑）：
    - 组数、次数、时长、难度：InputNumber 内联编辑
    - 强度：Select 下拉
    - **新增**：删除按钮（红色 DeleteOutlined，每行末尾）
  - **新增**：表格上方「+ 添加动作」搜索下拉框
    - 数据源：actionLib（需先在动作库 tab 加载）
    - 已添加的动作自动过滤，避免重复
    - 选中动作后按默认值（default_sets/reps/duration_seconds/difficulty/intensity）插入
- 保存逻辑：
  - 无班级 → PUT 直接更新 → message.success("计划已更新")
  - 有班级 → PUT 创建审批请求 → message.success("已提交教练审批")

**Import 变更：**
- 新增 `Input`（原缺失导致页面报错 "Input is not defined"）
- 新增 `PlusOutlined, DeleteOutlined`
- 新增 `planEditApi` from services/api

#### 4.2 `frontend/src/pages/StudentDetailPage.tsx` — 修改

**删除 V1 训练处方 tab：**
- 移除 "训练处方 (N)" tab 及全部渲染代码（V1 `Prescription` 展示）
- 移除 `RxItem`、`Prescription` 接口定义
- 移除 `MedicineBoxOutlined` 图标导入
- 移除 `phaseLabel`、`statusLabel` 辅助映射

**增强 V2 训练计划 tab：**
- 重命名：`训练计划 V2` → `训练计划`
- 新增总体进度条：`completions / totalSets 组已完成`
- 表格新增列：
  - `#`（order_index 序号）
  - `完成`（completions/sets，已完成显示绿色）
  - `最新得分`（颜色编码 Tag）
  - 阶段列改为 Tag 形式
- 计划卡片 Extra 区域新增「训练进度 X/Y 组」文字

#### 4.3 `frontend/src/pages/CoachPage.tsx` — 修改

**班级卡片邀请码展示：**
- 卡片 body 新增邀请码区域（浅灰背景、圆角 8px）：
  - Tag 显示邀请码（monospace、letter-spacing: 2、可点击复制）
  - 复制按钮（CopyOutlined）
  - 刷新按钮（SyncOutlined + Popconfirm 确认）

**班级详情邀请码横幅：**
- Stats row 前新增蓝色背景 Card
- 大头像邀请码 Tag + 复制/刷新按钮 + 引导文案

**新增功能函数：**
- `handleCopyCode(code, e)` — navigator.clipboard.writeText + message.success
- `handleRegenerateCode(classId, e)` — 调用 coachApi.regenerateCode + 刷新

**Import 变更：**
- 新增 `CopyOutlined, SyncOutlined`

#### 4.4 `frontend/src/pages/ProfilePage.tsx` — 修改

- 个人信息卡片 Extra 区域新增「我的班级」按钮（仅 trainee 角色显示）
- 新增导入：`TeamOutlined`, `useNavigate`

#### 4.5 `frontend/src/components/MainLayout.tsx` — 修改

**侧边栏菜单变更：**
- TRAINEE_MENU 新增 `{ key: "/my-classes", icon: <TeamOutlined />, label: "我的班级" }`
- TRAINEE_MENU 新增 `{ key: "/messages", icon: <BellOutlined />, label: "消息" }`
- COACH_MENU 新增 `{ key: "/coach/plan-review", icon: <AuditOutlined />, label: "计划审批" }`

**红色气泡角标：**
- 新增 state：`unreadMsgs`、`pendingApprovals`
- useEffect 挂载时立即拉取 + 每 5 秒轮询 `messageApi.unreadCount()` 和 `coachApi.listChangeRequests('pending')`
- 使用 `useMemo` 动态重建菜单项 label，通过 `<Badge count={n} />` 包裹显示红色数字角标
- 仅 coach/admin 角色查询待审批数

**架构变更：**
- 菜单从静态常量改为 `useMemo` 动态计算（依赖 user.role、unreadMsgs、pendingApprovals）
- MenuItem.label 类型从 `string` 改为 `React.ReactNode`

**Import 变更：**
- 新增 `useEffect, useMemo`
- 新增 `Badge`
- 新增 `BellOutlined, AuditOutlined`
- 新增 `messageApi` from services/api（静态导入）+ `coachApi` 动态 import（按需加载）

#### 4.6 `frontend/src/App.tsx` — 修改

新增路由：
```tsx
<Route path="my-classes" element={<MyClassesPage />} />
<Route path="messages" element={<MessagesPage />} />
<Route path="coach/plan-review" element={
  <PrivateRoute roles={["coach", "admin"]}><PlanReviewPage /></PrivateRoute>
} />
```

新增导入：
```tsx
import MyClassesPage from "./pages/MyClassesPage";
import MessagesPage from "./pages/MessagesPage";
import PlanReviewPage from "./pages/coach/PlanReviewPage";
```

---

## 完整文件清单

| 文件 | 操作 | 行数 |
|------|------|------|
| `backend/database/models.py` | 修改 | +55 |
| `backend/database/connection.py` | 修改 | +42 |
| `backend/services/student_class_service.py` | **新建** | 215 |
| `backend/services/plan_edit_service.py` | **新建** | 310 |
| `backend/services/message_service.py` | **新建** | 130 |
| `backend/services/coach_service.py` | 修改 | +60 |
| `backend/routers/student_class.py` | **新建** | 59 |
| `backend/routers/message.py` | **新建** | 49 |
| `backend/routers/prescription_v2.py` | 修改 | +40 |
| `backend/routers/coach.py` | 修改 | +55 |
| `backend/schemas/student_class.py` | **新建** | 39 |
| `backend/schemas/plan_edit.py` | **新建** | 58 |
| `backend/main.py` | 修改 | +3 |
| `frontend/src/types/index.ts` | 修改 | +55 |
| `frontend/src/services/api.ts` | 修改 | +45 |
| `frontend/src/pages/MyClassesPage.tsx` | **新建** | 240 |
| `frontend/src/pages/MessagesPage.tsx` | **新建** | 210 |
| `frontend/src/pages/coach/PlanReviewPage.tsx` | **新建** | 240 |
| `frontend/src/pages/PrescriptionPage.tsx` | 修改 | +80 |
| `frontend/src/pages/StudentDetailPage.tsx` | 修改 | -50 / +60 |
| `frontend/src/pages/CoachPage.tsx` | 修改 | +60 |
| `frontend/src/pages/ProfilePage.tsx` | 修改 | +5 |
| `frontend/src/components/MainLayout.tsx` | 修改 | +50 |
| `frontend/src/App.tsx` | 修改 | +5 |

**统计：** 新建 8 个文件 · 修改 16 个文件 · 净增约 1800 行代码

---

## API 端点全景

本次新增 **20 个 API 端点**：

### 班级相关 (5)
| 方法 | 路径 |
|------|------|
| POST | `/api/class/join` |
| GET | `/api/class/my-classes` |
| GET | `/api/class/my-classes/{id}` |
| DELETE | `/api/class/my-classes/{id}/leave` |
| POST | `/api/coach/classes/{id}/regenerate-code` |

### 计划审批 (8)
| 方法 | 路径 |
|------|------|
| PUT | `/api/prescription-v2/plans/{id}` |
| POST | `/api/prescription-v2/plans/{id}/submit-change` |
| GET | `/api/prescription-v2/change-requests` |
| GET | `/api/coach/change-requests` |
| GET | `/api/coach/change-requests/{id}` |
| PUT | `/api/coach/change-requests/{id}/approve` |
| PUT | `/api/coach/change-requests/{id}/adjust` |
| PUT | `/api/coach/change-requests/{id}/reject` |

### 消息 (5)
| 方法 | 路径 |
|------|------|
| GET | `/api/messages` |
| GET | `/api/messages/unread-count` |
| GET | `/api/messages/with/{partner_id}` |
| POST | `/api/messages` |
| PUT | `/api/messages/{id}/read` |

### 修复 (2)
- `GET /api/coach/students/{id}/plans` — 返回数据增加 items 数组（含 completions + latest_score）
- `GET /api/coach/students/{id}/profile` — 移除 V1 prescriptions 字段

---

## 已知问题与注意事项

1. **POST `/api/messages` 使用 Query 参数**（receiver_id + content），非 JSON body。中文内容在 curl 测试中需 URL 编码，前端 axios 不受影响。

2. **动作库需先加载**：编辑计划时「添加动作」下拉框依赖动作库数据。用户需先在 AI 训练计划页面的「动作库」tab 点击「加载」按钮。后续可改为自动加载。

3. **V1 Prescription 表保留**：虽然前端已移除 V1 训练处方展示，但后端 V1 表仍存在。V2 计划激活时会创建 bridge Prescription 记录以保持向后兼容。

4. **CoachPage 中的 `import { coachApi }` 为静态导入**：MainLayout.tsx 中的 coachApi 改用动态 `import()` 以按需加载教练专属功能（减少 trainee 角色的初始包大小）。

5. **热重载缓存**：后端 `.py` 文件修改后 uvicorn hot-reload 可能不及时（尤其是 `main.py` 改动）。如遇 405 Method Not Allowed，重启后端 `python run.py` 即可。
