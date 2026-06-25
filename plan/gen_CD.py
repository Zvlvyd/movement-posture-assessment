
doc = make_doc(); set_heading_style(doc)
cover(doc, '开发任务书 — Person C（v3.0）', '后端API层', '负责: FastAPI + WebSocket + MySQL + JWT + 报告导出 + 管理后台')

doc.add_heading('一、职责范围（v3.0 扩展）', level=1)
add_note(doc, 'v3.0 新增：标准学习WS session、打卡API、班级统计API、PDF报告导出、管理员批量导入与系统配置。数据库从12张增加到14张。')
doc.add_paragraph()

doc.add_heading('二、v3.0 新增路由模块', level=1)
add_table(doc, ['路由文件', '新增端点', '说明'], [
    ['routers/learn.py', 'GET /learn/standard/{id}, POST /learn/session, WS /learn/ws/{id}', '单动作标准学习'],
    ['routers/checkin.py', 'POST /checkin, GET /checkin/{date}, GET /badges', '每日打卡+徽章查询'],
    ['routers/class_stats.py', 'GET /class/stats, GET /class/risks', '班级FMS统计(仅教练)'],
    ['routers/admin.py', '新增 POST /admin/import, PUT /admin/config, GET /admin/logs', '批量导入+系统配置+日志'],
    ['routers/fms.py', '新增 GET /fms/records/{id}/compare', '新旧FMS对比'],
    ['routers/prescription.py', '新增 GET /unlock-status, POST /unlock-request, POST /re-test', '解锁管理+复测升级'],
    ['routers/records.py', '新增 GET /records/{id}/export', '训练报告PDF导出'],
])

doc.add_heading('三、v3.0 新增 WebSocket Session 类型', level=1)
doc.add_paragraph('在 websocket_manager.py 中新增第四种 session 类型：')
add_code(doc,
    'session_type = "learn"    # 标准学习帧流\n'
    '\n'
    '# 前端发送: {type:"frame", session_id, frame_data, timestamp}\n'
    '# 后端返回: {\n'
    '#   "type":"learn_result",\n'
    '#   "angles": {"left_knee":95,...},              # 用户当前角度\n'
    '#   "standard_angles": {"left_knee":85,...},     # 标准动作角度\n'
    '#   "differences": {"left_knee":{"user":95,"standard":85,"diff":+10}},# 差异\n'
    '#   "feedback": "左膝弯度不足，请再下蹲10度",\n'
    '#   "score": 78,\n'
    '#   "max_diff_joint": "left_knee"\n'
    '# }'
)

doc.add_heading('四、v3.0 数据库新增表', level=1)
add_code(doc,
    'CREATE TABLE badges (\n'
    '    id BIGINT AUTO_INCREMENT PRIMARY KEY,\n'
    '    user_id BIGINT REFERENCES users(id),\n'
    '    badge_type VARCHAR(32) NOT NULL,  -- "week_streak"|"month_streak"\n'
    '    earned_at DATETIME DEFAULT NOW()\n'
    ');\n'
    '\n'
    'CREATE TABLE fms_comparisons (\n'
    '    id BIGINT AUTO_INCREMENT PRIMARY KEY,\n'
    '    user_id BIGINT REFERENCES users(id),\n'
    '    old_record_id BIGINT REFERENCES fms_records(id),\n'
    '    new_record_id BIGINT REFERENCES fms_records(id),\n'
    '    score_changes JSON,   -- {"balance":+5,"core":+10,...}\n'
    '    created_at DATETIME DEFAULT NOW()\n'
    ');\n'
    '\n'
    'CREATE TABLE class_groups (\n'
    '    id BIGINT AUTO_INCREMENT PRIMARY KEY,\n'
    '    name VARCHAR(64) NOT NULL,\n'
    '    coach_id BIGINT REFERENCES users(id),\n'
    '    student_ids JSON,     -- [1,2,3,...]\n'
    '    created_at DATETIME DEFAULT NOW()\n'
    ');\n'
    '\n'
    'CREATE TABLE system_logs (\n'
    '    id BIGINT AUTO_INCREMENT PRIMARY KEY,\n'
    '    level VARCHAR(16) DEFAULT "info",\n'
    '    module VARCHAR(64),\n'
    '    message TEXT,\n'
    '    created_at DATETIME DEFAULT NOW()\n'
    ');\n'
    '\n'
    'ALTER TABLE check_in_cards ADD streak_highest INT DEFAULT 0;\n'
    'ALTER TABLE users ADD class_group_id BIGINT;'
)

doc.add_heading('五、v3.0 新增服务模块', level=1)
add_table(doc, ['文件', '说明', '优先级'], [
    ['services/report_service.py', 'PDF报告生成(训练简报/FMS报告/班级汇总/学员档案), 使用python-docx或weasyprint', '高'],
    ['services/checkin_service.py', '打卡逻辑编排: 调用B的CheckinEngine + 判断徽章 + 生成卡片数据', '高'],
    ['services/class_stats_service.py', '班级统计编排: 查询班级FMS数据 -> 调用B的ClassStatsEngine', '高'],
    ['services/import_service.py', 'Excel批量导入解析: openpyxl读取 -> 批量建user -> 分配班级', '中'],
    ['services/log_service.py', '系统日志写入: loguru -> MySQL system_logs表', '中'],
])

doc.add_heading('六、管理员后台新功能', level=1)
add_table(doc, ['端点', '功能', '实现'], [
    ['POST /admin/import', '批量导入师生', '接收Excel文件 -> openpyxl解析 -> 批量INSERT + 自动建class_group'],
    ['PUT /admin/config', '系统配置', 'Body: {model:"yolo"|"mediapipe", fps_limit:15|30, sensitivity:"high"|"medium"|"low"}'],
    ['GET /admin/logs', '系统日志', '查询system_logs表, 支持 level/module/date 筛选, 分页'],
])

doc.add_page_break()

doc.add_heading('七、完整API端点汇总（33个）', level=1)
add_table(doc, ['方法', '路径', 'v3.0', '说明'], [
    ['POST', '/api/auth/register', '-', '注册'],
    ['POST', '/api/auth/login', '-', '登录'],
    ['POST', '/api/train/start', '-', '创建训练'],
    ['POST', '/api/train/{id}/stop', '-', '结束训练'],
    ['WS', '/api/train/ws/{id}', '-', '训练帧流'],
    ['POST', '/api/fms/start', '-', 'FMS筛查'],
    ['WS', '/api/fms/ws/{id}', '-', 'FMS帧流'],
    ['GET', '/api/fms/records', '-', 'FMS列表'],
    ['GET', '/api/fms/records/{id}', '-', 'FMS详情'],
    ['GET', '/api/fms/records/{id}/compare', '新增', '新旧对比'],
    ['POST', '/api/prescriptions/generate', '-', '生成处方'],
    ['GET', '/api/prescriptions/active', '-', '当前处方'],
    ['PUT', '/api/prescriptions/{id}/activate', '-', '切换处方'],
    ['POST', '/api/prescriptions/{id}/follow', '-', '处方跟练'],
    ['WS', '/api/prescriptions/ws/{id}', '-', '跟练帧流'],
    ['GET', '/api/prescriptions/unlock-status', '新增', '解锁进度'],
    ['POST', '/api/prescriptions/unlock-request', '新增', '提前解锁'],
    ['POST', '/api/prescriptions/re-test', '新增', '复测升级'],
    ['GET', '/api/records', '-', '训练记录'],
    ['GET', '/api/records/{id}', '-', '记录详情'],
    ['GET', '/api/records/{id}/export', '新增', '导出PDF'],
    ['GET', '/api/learn/standard/{id}', '新增', '标准动作数据'],
    ['POST', '/api/learn/session', '新增', '创建学习session'],
    ['WS', '/api/learn/ws/{id}', '新增', '学习帧流'],
    ['POST', '/api/checkin', '新增', '每日打卡'],
    ['GET', '/api/checkin/{date}', '-', '打卡数据'],
    ['GET', '/api/badges', '新增', '徽章列表'],
    ['GET', '/api/stats/overview', '-', '个人统计'],
    ['GET', '/api/stats/{user_id}', '-', '学员统计'],
    ['GET', '/api/class/stats', '新增', '班级FMS统计'],
    ['GET', '/api/class/risks', '新增', '班级风险预警'],
    ['POST', '/api/admin/import', '新增', '批量导入'],
    ['PUT', '/api/admin/config', '新增', '系统配置'],
    ['GET', '/api/admin/logs', '新增', '系统日志'],
])

doc.add_heading('八、验收标准（v3.0新增）', level=1)
add_table(doc, ['编号', '标准'], [
    ['C1-C8', '同 v2.0 标准'],
    ['C9', '学习WS session: 接收帧 -> 调用StandardLearner -> 返回差异数据'],
    ['C10', '打卡: 调用CheckinEngine -> 判断新徽章 -> 写入badges表'],
    ['C11', '解锁进度: 正确调用UnlockManager并返回进度数据'],
    ['C12', '班级统计: 查询class_group -> 聚合FMS -> 调用ClassStatsEngine'],
    ['C13', 'PDF导出: 训练/FMS/班级/档案 四种报告可下载'],
    ['C14', '批量导入: Excel解析 -> 批量建用户 -> 分配班级'],
    ['C15', '系统配置: 模型切换/FPS/灵敏度 写入配置表并生效'],
])

footer(doc)
doc.save('D:/workbench/program3/plan/任务书-PersonC-后端API层_v3.docx')
print('C v3 done')


doc = make_doc(); set_heading_style(doc)
cover(doc, '开发任务书 — Person D（v3.0）', '前端应用层', '负责: React 18页面 + Canvas + ECharts + WebSocket + TTS语音')

doc.add_heading('一、职责范围（v3.0 扩展）', level=1)
add_note(doc, 'v3.0 新增5个页面: 标准学习、解锁进度、每日打卡、班级FMS统计、系统设置。新增 TTS 语音播报。前端页面从15个增加到18个。')
doc.add_paragraph()

doc.add_heading('二、v3.0 新增页面', level=1)
add_table(doc, ['页面路由', '组件', '核心功能', '优先级'], [
    ['/learn/:action_id', 'StandardLearnerView', '标准视频播放(多视角)+Canvas骨架叠加+角度差异柱状图+慢动作回放+常见错误展开', '最高'],
    ['/prescription/unlock', 'UnlockProgress', '各维度进度条+锁定动作列表+解锁条件+复查提醒+提前解锁按钮', '高'],
    ['/checkin', 'CheckinPage', '今日打卡内容+连续天数+徽章展示+打卡卡片生成(Canvas)+二维码+分享', '高'],
    ['/admin/class-stats', 'ClassStatsPage', '班级雷达图+高风险学员表+对称异常表+共性弱点+导出PDF按钮', '高'],
    ['/admin/settings', 'SettingsPage', '模型切换开关+FPS滑块+灵敏度选择+日志列表+批量导入Excel', '中'],
])

doc.add_heading('三、v3.0 增强页面', level=1)
add_table(doc, ['页面', '增强内容'], [
    ['/fms/report/:id', '新增新旧雷达图对比(双雷达图叠加)+各维度进步箭头(↑+5)'],
    ['/history', '新增趋势分析标签: 近7天/30天/90天训练趋势折线图'],
    ['/history/:id', '新增导出PDF按钮 + 分享图片按钮'],
    ['/train', '新增基础模式语音播报(仅danger)+进阶模式逐条播报'],
])

doc.add_heading('四、v3.0 新组件', level=1)
add_table(doc, ['组件', '技术方案', '功能'], [
    ['StandardLearnerView', 'video元素+Canvas叠加+ECharts柱状图', '标准动作学习完整交互'],
    ['UnlockProgress', 'Ant Design Progress+List', '解锁进度展示'],
    ['CheckinCard', 'Canvas渲染+二维码(qrcode.js)', '打卡卡片生成+下载+分享'],
    ['ClassRadarChart', 'ECharts 雷达图+叠加', '班级均值 vs 个体值'],
    ['VoiceFeedback', 'Web Speech API(speechSynthesis)', 'TTS语音播报纠错文本'],
    ['BatchImportModal', 'Ant Design Upload+Table预览', 'Excel批量导入+预览'],
])

doc.add_heading('五、语音播报实现', level=2)
add_code(doc,
    '// utils/voice.ts\n'
    'export function speakFeedback(text: string, severity: "warning"|"error") {\n'
    '  if (!window.speechSynthesis) return;\n'
    '  const utterance = new SpeechSynthesisUtterance(text);\n'
    '  utterance.lang = "zh-CN";\n'
    '  utterance.rate = 0.9;  // 稍慢，确保清晰\n'
    '  utterance.pitch = severity === "error" ? 0.8 : 1.0;  // error=低沉\n'
    '  window.speechSynthesis.speak(utterance);\n'
    '}\n'
    '\n'
    '// 基础模式仅播报 severity==="error" 的文本\n'
    '// 进阶模式逐条播报所有纠错'
)

doc.add_page_break()

doc.add_heading('六、打卡卡片 Canvas 渲染', level=2)
add_code(doc,
    '// utils/checkinCard.ts - Canvas 渲染打卡卡片\n'
    'export function renderCheckinCard(ctx: CanvasRenderingContext2D, data: CheckinData) {\n'
    '  // 1. 背景渐变(运动主题配色)\n'
    '  // 2. 日期 + 用户昵称(左上)\n'
    '  // 3. 连续打卡天数(居中大字, CSS动画数字跳动)\n'
    '  // 4. 今日完成动作列表\n'
    '  // 5. 系统鼓励语(随机从预设库选取)\n'
    '  // 6. 二维码(右下, 邀请好友)\n'
    '  // 7. 徽章图标(如有新徽章)\n'
    '  return canvas.toDataURL("image/png");  // 可下载/分享\n'
    '}'
)

doc.add_heading('七、页面路由汇总（18个）', level=1)
add_code(doc,
    '/(根路径)\n'
    '|-- /login                      登录\n'
    '|-- /register                   注册\n'
    '|-- /home                       首页\n'
    '|-- /fms                        FMS筛查\n'
    '|-- /fms/report/:id             FMS报告(新旧对比) [v3增强]\n'
    '|-- /train                      训练 [v3增强:语音]\n'
    '|-- /learn/:action_id           标准学习 [v3新增]\n'
    '|-- /prescription               处方管理\n'
    '|-- /prescription/unlock        解锁进度 [v3新增]\n'
    '|-- /follow/:id                 处方跟练\n'
    '|-- /checkin                    每日打卡 [v3新增]\n'
    '|-- /history                    历史记录 [v3增强:趋势]\n'
    '|-- /history/:id                训练详情 [v3增强:导出]\n'
    '|-- /stats                      个人统计\n'
    '|-- /profile                    个人中心\n'
    '|-- /admin/students             学员管理\n'
    '|-- /admin/class-stats          班级统计 [v3新增]\n'
    '|-- /admin/library              动作库\n'
    '|-- /admin/settings             系统设置 [v3新增]'
)

doc.add_heading('八、验收标准（v3.0新增）', level=1)
add_table(doc, ['编号', '标准'], [
    ['D1-D10', '同 v2.0 标准'],
    ['D11', '标准学习: 视频播放+Canvas骨架+角度差异柱状图+慢动作回放'],
    ['D12', '解锁进度: 进度条+条件显示+提前解锁交互'],
    ['D13', '每日打卡: 打卡按钮+卡片Canvas生成+二维码+分享+徽章弹窗'],
    ['D14', '班级统计: 雷达图+风险表+对称异常表+共性弱点'],
    ['D15', '语音: TTS播报纠错, 基础/进阶不同强度'],
    ['D16', '系统设置: 模型切换+FPS滑块+日志列表+批量导入'],
    ['D17', 'PDF导出: 训练报告/FMS报告 下载按钮'],
    ['D18', '响应式: 18个页面在1920和1366分辨率均正常'],
])

footer(doc)
doc.save('D:/workbench/program3/plan/任务书-PersonD-前端应用层_v3.docx')
print('D v3 done')
