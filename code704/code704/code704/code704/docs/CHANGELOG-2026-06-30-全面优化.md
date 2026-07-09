# 全面优化变更日志

**日期：** 2026-06-30  
**范围：** 六维评估驱动的全面优化（功能正确性 / 安全性 / 产品逻辑 / 用户体验 / 代码质量 / 模块化）  
**修改文件数：** 25+ 修改，9 新建，2 配置更新

---

## Phase 1: 严重 Bug 修复 + 安全漏洞修补

### 运行时 Bug 修复 (4 个)

| Bug | 文件 | 变更 |
|-----|------|------|
| C1 IndexError | `backend/services/assessment_service.py:473` | `kp_array[0,:,2].mean()` → `kp_confs.mean()`（形状 (17,2) 无第三维） |
| C2 AttributeError ×2 | `backend/services/learning_service.py:222`<br>`backend/routers/learning.py:78` | `loader.get_action(name)` → `loader.get_by_name(name)` |
| C3 竞态条件 | `backend/services/fms_service.py:60` | 为 `_single_test_results_global` 添加 `threading.Lock`，保护所有读写 |
| C4 FSM 默认值 | `models/action_recognizer/squat_fsm.py` | `cond_complete` 默认值 90.0→180.0；全部 7 个 FSM 默认值统一为 180.0；`get_fsm_context` 中 `or` 改为显式 `None` 检查 |

### 安全漏洞修复 (3 严重 + 速率限制 + 文件上传)

| 漏洞 | 文件 | 变更 |
|------|------|------|
| S1 硬编码 SECRET_KEY | `config/settings.py:74` | 移除默认值，启动时 `validate()` 检查 |
| S2 硬编码 DB_PASSWORD | `config/settings.py:61` | 移除默认值，启动时 `validate()` 检查 |
| S3 默认密码 | `config/settings.py:80-82`<br>`backend/database/seed.py` | 移除硬编码密码；未设置时自动生成随机密码并打印 |
| 速率限制 | `backend/middleware/rate_limit.py`（新建）<br>`backend/main.py` | 每 IP 每分钟 5 次登录尝试限制 |
| 文件上传安全 | `backend/routers/fms.py` | 100MB 限制、MIME 白名单、扩展名白名单、bare except→OSError+日志 |

### 新增配置验证

- `config/settings.py` — `Settings.validate()` 方法，启动时检查 SECRET_KEY 和 DB_PASSWORD
- `backend/main.py:43` — 启动时调用 `settings.validate()`
- `config/settings.py` — 添加 `ENABLE_TEST_ENDPOINTS` 特性开关

---

## Phase 2: 高危安全加固

| 加固项 | 文件 | 变更 |
|--------|------|------|
| JWT 令牌撤销 | `backend/database/models.py` | User 表添加 `token_version` 列 (INT, default=0) |
| | `backend/services/auth_service.py` | `create_access_token` 嵌入 `tv` 声明；`get_current_user` 校验 `token_version` |
| | `backend/routers/auth.py` | `change_password` 递增 `token_version`（旧令牌立即失效） |
| Cookie 认证 | `backend/services/auth_service.py` | `set_token_cookie()` / `clear_token_cookie()` — httpOnly, SameSite=Strict |
| | `backend/routers/auth.py` | login 端点设置 cookie |
| 测试端点门控 | `backend/routers/prescription_v2.py` | 3 个 mock 端点添加 `_require_test_endpoints` 依赖（默认 404） |
| 会话容量限制 | `models/assessment/multi_view_session.py` | `MultiViewSessionStore` 添加 `MAX_SESSIONS=100` + 淘汰机制 |
| 日期解析修复 | `backend/routers/auth.py` | `except:` → `except ValueError:` + 400 错误返回 |

---

## Phase 3: 用户体验全面优化

### 全局保护
| 文件 | 变更 |
|------|------|
| `frontend/src/components/ErrorBoundary.tsx`（新建） | React 错误边界 — 捕获未处理异常，显示"出错了"+ 重试/返回首页 |
| `frontend/src/App.tsx` | 包裹 `<ErrorBoundary>`；PrivateRoute 添加初始化加载态；粒度化 Zustand 选择器 |

### 状态补全
| 页面 | 变更 |
|------|------|
| `App.tsx PrivateRoute` | token 存在但 user 为 null 时显示 Spin 加载 |
| `PrescriptionTrainingPage.tsx` | 加载失败 → Result 组件 + 重试按钮；空计划 → Empty + 引导按钮；未知 mode → 回退到计划列表 |
| `LoginPage.tsx` | 区分 5 种错误类型（401/403/429/网络/服务器） |
| `FMSScreeningPage.tsx` | 零值分数不再被假值检查吞掉；摄像头初始化超时提示；JSON.parse 包裹 try/catch；帧捕获添加最大重试次数 |

### 可访问性
| 组件 | 变更 |
|------|------|
| `MainLayout.tsx` | 侧边栏折叠按钮 `<div>` → `<button>` + `aria-label`；`<Menu>` 添加 `aria-label="主导航"` |
| `MathCaptcha.tsx` | 输入框添加 `aria-label` + `inputMode="numeric"`；刷新按钮 `aria-label` |
| `MainLayout.tsx` | 移除 WebKit-only 渐变文字 → 纯色（Firefox 兼容） |

### 移动端响应式
| 位置 | 变更 |
|------|------|
| `LoginPage.tsx` | `width:400` → `maxWidth:400, width:'100%'` |
| `MainLayout.tsx` | Content padding: `24px` → `clamp(12px, 3vw, 24px)` |
| 全局 | 容器添加 `padding: clamp(12px, 3vw, 24px)` |

### WebSocket 安全
| 文件 | 变更 |
|------|------|
| `FMSScreeningPage.tsx:271` | token → `encodeURIComponent(token)` + null 守卫 |
| `AssessmentPage.tsx:238` | token → `encodeURIComponent(token)`（已有 null 守卫） |

---

## Phase 4: 代码质量重构

### 算法修复 (6 个)
| Bug | 文件 | 变更 |
|-----|------|------|
| FMS 柔韧性超限 | `models/fms/scoring.py:48` | `depth+trunk+arm` → `min(100, depth+trunk+arm)`，修复 120/100 溢出 |
| 高级评分缺 max_angle | `models/scoring.py:33-42` | 添加过伸惩罚（`left/right > max_angle`） |
| safe_kp 像素检查 | `models/posture_analyzer.py:40-55` | 优先使用置信度列（第 3 列），阈值 0.3 |
| 对称性评分 dict 兼容 | `models/assessment/scoring.py:231-244` | `isinstance(finding, dict)` 分支处理 |
| DeepSeek 无重试 | `models/prescription_v2/deepseek_prescription.py` | 3 次重试 + 指数退避（1s/2s/4s）；捕获 ConnectError/NetworkError/Timeout 等全部 httpx 异常 |
| DeepSeek Key 检查过晚 | `models/prescription_v2/deepseek_prescription.py` | 提前到 `generate()` 顶部，避免构建大量上下文后才发现 |

### TypeScript 类型安全
| 文件 | 变更 |
|------|------|
| `frontend/src/types/index.ts` | 全量重写：13+ 接口消除 `any`；`UserRole` 联合类型；`CommonError` 共享类型；新增 `RadarChartData`/`PostureProblem`/`ROMAnalysisItem`/`AsymmetryFinding`/`MuscleAnalysis`/`PlanMeta`/`KeyCheck` 接口 |

### Python 代码质量
| 文件 | 变更 |
|------|------|
| `backend/routers/auth.py` | 导入全部提升至文件顶部；`datetime.utcnow()` → `datetime.now(timezone.utc)` |
| `backend/routers/fms.py` | 裸 `except:` → `except OSError:` + logger.warning |
| `backend/services/auth_service.py` | `datetime.utcnow()` → `datetime.now(timezone.utc)` |

### 前端代码质量
| 文件 | 变更 |
|------|------|
| `frontend/src/store/auth.ts` | `JSON.parse` 包裹 try/catch（防 localStorage 损坏）；失败时清理 localStorage；添加 loading 状态 |
| `frontend/src/pages/FMSScreeningPage.tsx` | 移除 10 个 console.log；帧捕获添加 `MAX_CAPTURE_RETRIES=25` |
| `frontend/src/pages/PrescriptionTrainingPage.tsx` | 事件处理器添加 `useCallback` |

---

## Phase 5: 测试覆盖

| 文件 | 内容 |
|------|------|
| `tests/test_angle_calculator.py`（新建） | 5 个测试类：直角/直线/零向量/垂直角度/全角度计算/对称性 |
| `tests/test_fsm.py`（新建） | 8 个测试类：全部 7 个 FSM 完整周期 + 不完整不计次 + 回环防重复 + 上下文回退 |
| `tests/test_scoring.py`（新建） | 3 个测试类：DualModeScorer 基础/高级 + FMSScoringEngine 5 维评分 + 上限/过伸验证 |

---

## Phase 6: 模块化清理

| 项目 | 文件 | 变更 |
|------|------|------|
| 知识库类型化 | `models/knowledge/__init__.py`（新建）<br>`models/knowledge/loader.py`（新建） | `KnowledgeBase` 类：`get_exercise/get_muscle/get_problem/get_rom_norm/get_threshold` 类型化访问 |
| 提升惰性导入 | `backend/services/fms_service.py` | `PostureAnalyzer`、`settings` → 模块级导入（解除 3 处惰性导入） |
| 移除 passlib | `shared/security.py` | 直接使用 `bcrypt.hashpw/checkpw`，移除 `passlib` 依赖 |
| 依赖更新 | `requirements.txt` | `passlib[bcrypt]>=1.7.4` → `bcrypt>=3.2.0` |

---

## 配置变更

| 文件 | 变更 |
|------|------|
| `.env` | 添加 `SECRET_KEY`（随机生成）、`DB_PASSWORD`、管理员/教练密码；新增 `ENABLE_TEST_ENDPOINTS` 注释 |
| `.env.example` | 重写：标记必填项，移除硬编码示例值，添加 openssl 生成命令提示 |

---

## 数据库变更

| 表 | 变更 | SQL |
|----|------|-----|
| `user` | 新增列 | `ALTER TABLE user ADD COLUMN token_version INT NOT NULL DEFAULT 0` |

---

## 回滚注意事项

- 如需回滚 `token_version`：`ALTER TABLE user DROP COLUMN token_version`；恢复 `models.py` 和 `auth_service.py`
- 如需恢复 passlib：`pip install passlib[bcrypt]>=1.7.4`；恢复 `shared/security.py` 原始版本
- SECRET_KEY 轮换会使所有现有令牌失效（用户需重新登录）
