# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import datetime

today_str = datetime.date.today().strftime('%Y-%m-%d')

def make_doc():
    doc = Document()
    for s in doc.sections:
        s.top_margin = Cm(2.0); s.bottom_margin = Cm(2.0)
        s.left_margin = Cm(2.0); s.right_margin = Cm(2.0)
    return doc

def set_heading_style(doc):
    for lv in [1,2,3,4]:
        h = doc.styles['Heading ' + str(lv)]
        if lv == 1: h.font.size = Pt(18); h.font.color.rgb = RGBColor(0x1A,0x56,0xDB)
        elif lv == 2: h.font.size = Pt(14); h.font.color.rgb = RGBColor(0x2C,0x3E,0x50)
        elif lv == 3: h.font.size = Pt(12); h.font.color.rgb = RGBColor(0x34,0x49,0x5E)

def add_table(doc, headers, rows):
    t = doc.add_table(rows=1+len(rows), cols=len(headers))
    t.style = 'Table Grid'; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i,th in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = th
        for p in c.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs: r.bold = True; r.font.size = Pt(9)
        s = OxmlElement('w:shd'); s.set(qn('w:fill'),'1A56DB'); s.set(qn('w:val'),'clear')
        c._tc.get_or_add_tcPr().append(s)
        for p in c.paragraphs:
            for r in p.runs: r.font.color.rgb = RGBColor(0xFF,0xFF,0xFF)
    for ri,row in enumerate(rows):
        for ci,val in enumerate(row):
            c = t.rows[ri+1].cells[ci]; c.text = str(val)
            for p in c.paragraphs:
                for r in p.runs: r.font.size = Pt(9)
            if ri % 2 == 1:
                s = OxmlElement('w:shd'); s.set(qn('w:fill'),'EBF0FA'); s.set(qn('w:val'),'clear')
                c._tc.get_or_add_tcPr().append(s)
    doc.add_paragraph()
    return t

def add_note(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text); run.font.size = Pt(9); run.font.color.rgb = RGBColor(0xE6,0x7E,0x22)
    run.italic = True

def cover(doc, title, subtitle, desc):
    for _ in range(5): doc.add_paragraph()
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run('运动姿态评估与纠错系统'); r.font.size = Pt(22); r.font.color.rgb = RGBColor(0x1A,0x56,0xDB)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(title); r.font.size = Pt(18); r.font.bold = True; r.font.color.rgb = RGBColor(0x2C,0x3E,0x50)
    doc.add_paragraph()
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(subtitle); r.font.size = Pt(14); r.font.color.rgb = RGBColor(0x34,0x49,0x5E)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(desc + '    ' + today_str); r.font.size = Pt(10); r.font.color.rgb = RGBColor(0x95,0xA5,0xA6)
    doc.add_page_break()

def footer(doc):
    doc.add_paragraph()
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run('--- 文档结束 ---'); r.font.size = Pt(9); r.font.color.rgb = RGBColor(0x95,0xA5,0xA6); r.italic = True

print('Helpers ready')


# =================== Build Document ===================
doc = make_doc()
set_heading_style(doc)
cover(doc, '开发任务书 — 周计划', 'v1.0 四人协作版', '总工期6周 | W3联调 | W5集成测试 | W6验收')

# ── 总览 ──
doc.add_heading('一、项目总览', level=1)
add_table(doc, ['角色', '负责人层', '总工时(人天)', '周次', '核心交付物'], [
    ['Person A', '模型推理层', '~20人天', 'W1-W5', 'YOLO/MediaPipe引擎 + 7关节角度(精度<3°) + 帧率监控'],
    ['Person B', '业务引擎层', '~30人天', 'W1-W6', '9识别器 + FMS + 处方 + 标准学习 + 打卡 + 解锁 + 班级统计'],
    ['Person C', '后端API层', '~28人天', 'W1-W6', '14张表 + 33端点 + 4种WS + JWT + PDF + 管理后台'],
    ['Person D', '前端应用层', '~24人天', 'W2-W6', '18页面 + 6新组件 + TTS语音 + Canvas打卡卡片'],
])
doc.add_paragraph()
add_note(doc, '关键依赖链: A(角度输出) → B(业务JSON) → C(API封装) → D(前端渲染)。W3为前后端联调里程碑，W5为集成测试里程碑。')

# ── 里程碑 ──
doc.add_heading('二、里程碑与依赖关系', level=1)
add_table(doc, ['里程碑', '时间', '验收标准', '参与方'], [
    ['M1: 基础架构完成', 'W1结束', 'A:ModelEngine+AngleUtils可运行, B:BaseRecognizer+深蹲可demo, C:DB建表+项目骨架+Swagger可访问', 'A,B,C'],
    ['M2: 核心功能可用', 'W2结束', 'A:YOLO+PoseAnalyzer完成, B:3识别器+FMS完成, C:Auth+Train+FMS API完成, D:项目骨架+登录完成', 'A,B,C,D'],
    ['M3: 前后端联调通过', 'W3结束', 'A与B联调角度格式通过, C与D联调(Auth+Train+FMS)3个模块通过', '全体'],
    ['M4: v3.0新功能完成', 'W4结束', 'B:Learn+Checkin+Unlock完成, C:Prescription+Learn+Checkin+Admin完成, D:处方+标准学习页完成', 'B,C,D'],
    ['M5: 集成测试完成', 'W5结束', 'A:单元测试覆盖率>85%, B:Stats+Cycle+联调, C:Export+WS增强+性能优化, D:打卡+历史+统计页完成', '全体'],
    ['M6: 全量验收', 'W6结束', 'B:测试+修复, C:安全加固+部署, D:管理后台+响应式+E2E, 全部18条验收标准通过', '全体'],
])
doc.add_page_break()

# ═══════════════════════════════════
# Person A
# ═══════════════════════════════════
doc.add_heading('三、Person A — 模型推理层 (W1-W5, ~20人天)', level=1)
add_note(doc, '核心原则：只输出结构化数据，不涉及任何业务逻辑。所有下游模块的数据来源。v3.0 精度要求提升至 <3度。')

add_table(doc, ['周次', '文件/模块', '任务(函数级)', '工时', '交付验收标准'], [
    ['W1', 'models/model_engine.py', 'ModelEngine抽象基类: __init__(), load(), infer(), extract_keypoints(), draw_skeleton()', '1d', '抽象接口定义完整，Person B可用mock调用验证'],
    ['W1', 'models/angle_utils.py', 'calc_angle(), calc_vector_angle(), normalize_angle(), angle_between_lines()', '1d', '20组已知三点坐标→角度真值对比，误差<1°'],
    ['W2', 'models/yolo_pose_engine.py', '继承ModelEngine: infer(conf_threshold=0.5), _parse_results()→COCO17格式, get_fps()→最近100帧均值, MediaPipe预留', '2d', '推理>=25fps(GPU), 输出格式100%符合数据契约'],
    ['W2', 'models/pose_analyzer.py', 'analyze_frame()→7关节角度, _joint_angle(), _trunk_lean(), COCO_KP索引映射', '2d', '100组人工标注真值 vs 输出: MAE<3°, RMSE<4°, MaxAE<8°'],
    ['W3', 'utils/pose_postprocessor.py', '卡尔曼滤波平滑, 置信度过滤(<0.5丢弃), _track_ids基于IoU的ID跟踪', '1d', '连续30帧无抖动跳变，遮挡场景不崩溃'],
    ['W3', 'utils/visualization.py', 'draw_skeleton(骨骼连线+彩色关键点), draw_angles(角度标注), draw_fps(帧率显示)', '1d', '骨骼图17关键点清晰可辨，角度数值位置合理'],
    ['W3', '(联调B)', '与Person B联调角度输出格式: A→B数据契约 JSON schema校验', '1d', 'B的识别器能正确消费A的7角度数据，字段名/数值范围一致'],
    ['W4', 'models/mediapipe_engine.py', '继承ModelEngine: MediaPipe Pose推理实现(预留支持运行时切换)', '2d', '管理员可在后台切换YOLO/MediaPipe，切换后推理正常'],
    ['W4', '性能优化', '推理批处理优化, TensorRT加速(可选), 内存/显存管理', '2d', 'GPU推理>=30fps, CPU推理>=15fps, 显存占用<2GB'],
    ['W5', '单元测试', 'AngleUtils全覆盖, PoseAnalyzer精度验证脚本(100组标注), PostProcessor边界测试', '2d', 'pytest覆盖率>85%, 精度验证脚本输出MAE/RMSE/MaxAE报告'],
    ['W5', '文档+收尾', 'README接口文档(输入/输出格式说明), 部署环境依赖说明', '1d', 'Person B/C/D可独立集成A模块，无需额外沟通'],
])
doc.add_page_break()

# ═══════════════════════════════════
# Person B
# ═══════════════════════════════════
doc.add_heading('四、Person B — 业务引擎层 (W1-W6, ~30人天)', level=1)
add_note(doc, '最重的角色。v3.0新增5个模块: StandardLearner, CheckinEngine, UnlockManager, ClassStatsEngine, CycleManager。')

add_table(doc, ['周次', '文件/模块', '任务(函数级)', '工时', '交付验收标准'], [
    ['W1', 'recognizers/base_recognizer.py', 'BaseRecognizer: Stage枚举(idle→ready→down→bottom→up→complete→finished), __init__(config), update(angles, callback)→dict, is_complete(), get_progress()', '1d', 'FSM状态机骨架可运行, Stage枚举定义完整'],
    ['W1', 'recognizers/squat_recognizer.py', 'SquatRecognizer: FSM完整实现(6状态转移), 角度阈值表驱动, 膝内扣检测(|left-right|>15°)', '2d', '50组标注视频验证: 准确率>90%, 阶段识别无跳跃'],
    ['W1', 'recognizers/pushup_recognizer.py', 'PushupRecognizer: 俯卧撑FSM, 肘角阈值(160°→90°→160°), 腰部下塌检测', '1d', '50组标注视频验证: 准确率>90%'],
    ['W2', '3个识别器', 'LungeRecognizer(弓步蹲,左右分别), PlankRecognizer(计时,腰部角度), OverheadPressRecognizer(过头推举)', '2d', '各50组标注视频: 准确率>90%'],
    ['W2', 'fms/fms_engine.py', 'FMSEngine: score_balance()闭眼单腿, score_flexibility()过头深蹲, score_shoulder()肩活动度, score_core()平板支撑, score_symmetry()弓步蹲, aggregate()→雷达图+tag+locks', '2d', '5动作各10组人工评分对比: 偏差<5分, 问题标签识别准确'],
    ['W3', '4个识别器', 'DeadliftRecognizer, GluteBridgeRecognizer, LateralRaiseRecognizer, CrunchRecognizer', '2d', '各50组标注视频: 准确率>90%(共9个识别器全部完成)'],
    ['W3', 'prescription/prescription_engine.py', 'PrescriptionEngine: generate() Tag→Action映射(规则引擎), 4阶段处方(热身/强化/主训练/冷身), check_locks()锁定条件(核心<40/平衡<30/对称<50), upgrade_on_retest()复测升级', '2d', '5组FMS结果→处方人工评审合理性: 强化阶段tag匹配率100%, 锁定排除100%正确'],
    ['W4', 'standard_learner.py', 'StandardLearner: __init__(action_id,standard_kps), compare(person_data,view)→{diffs,score,feedback}, get_common_errors()常见错误库, get_final_score()累计评分', '2d', '3个标准动作对比: 差异反馈中文准确率>95%, 评分与人工一致性>0.85'],
    ['W4', 'checkin_engine.py', 'CheckinEngine: checkin(actions)→{streak,badges,encouragement}, get_streak()昨日查询→连续则+1否则reset=1, check_badges()7天/30天判定, 鼓励语预设库(20条)', '1d', '连续/中断场景: streak逻辑100%正确, 徽章7天week/30天month判定正确'],
    ['W4', 'unlock_manager.py', 'UnlockManager: get_progress(fms,locks)→各维度进度%, check_unlock(old,new)→已解锁列表, early_unlock_test()安全测试(需通过指定动作的简单版)', '1d', '5维度解锁/锁定逻辑覆盖: 核心<40/平衡<30/对称<50正确锁定, 提升>阈值正确解锁'],
    ['W5', 'class_stats.py', 'ClassStatsEngine: calc_class_avg()班级均值, risk_distribution()红/黄/绿分布, symmetry_issues()对称异常名单, common_weakness()共性弱点(全班均值最低维度)', '2d', '含20人模拟数据: 雷达图正确, 风险分布<=1%误差, 共性弱点识别正确'],
    ['W5', 'cycle_manager.py', 'CycleManager: get_phase()当前周期阶段, adjust_prescription(phase,rx)自动调整强度, auto_adjust()经期(1-7):intensity-2,卵泡期(8-14):+1,黄体期(15-28):正常', '1d', '28天周期模拟: 各阶段强度调整正确, 跳跃→拉伸替换正确'],
    ['W5', '(联调C)', '与Person C联调: B输出的业务JSON被C正确封装为API格式', '1d', 'C的POST /prescriptions/generate返回B的处方JSON, 字段无缺失'],
    ['W6', '单元测试', '每识别器>=20组测试帧(标准/边界/遮挡), FMS评分>=10组人工对比, StandardLearner 3动作各10组', '2d', 'pytest覆盖率>85%, 全部测试用例通过'],
    ['W6', '集成测试+修复', 'FMS端到端(5动作→雷达图→处方), 标准学习端到端(双骨架→差异→评分)', '2d', 'B模块集成到C后可跑通完整FMS→处方链路'],
])
doc.add_page_break()

# ═══════════════════════════════════
# Person C
# ═══════════════════════════════════
doc.add_heading('五、Person C — 后端API层 (W1-W6, ~28人天)', level=1)
add_note(doc, 'FastAPI + WebSocket + MySQL + Redis + MinIO + JWT + PDF导出 + 管理后台。14张表，33端点，4种WS Session。')

add_table(doc, ['周次', '文件/模块', '任务(函数级)', '工时', '交付验收标准'], [
    ['W1', '数据库DDL', '14张表完整CREATE TABLE + Alembic迁移脚本 + Redis配置(会话/黑名单)', '2d', 'MySQL中执行无误, 所有索引生效, 外键约束正确'],
    ['W1', '项目骨架', 'FastAPI app.py + CORS中间件 + 全局异常处理 + config.py(pydantic Settings) + 日志配置', '2d', '服务可启动, Swagger /docs可访问, 健康检查 /health返回200'],
    ['W2', 'auth/', 'jwt_handler.py: create_token(), verify_token(), refresh_token()(24h有效期+7天刷新)。dependencies.py: get_current_user()依赖注入。auth_router.py: /register(bcrypt), /login, /logout(Redis黑名单), /me', '1d', 'Postman测试: 注册→登录→携带Token访问受保护端点→过期Token被拒绝→刷新成功'],
    ['W2', 'routers/train_router.py', '/start(session_id生成), WS /ws/{sid}(帧流收发), /records(分页), /records/{id}(详情+角度图表)', '2d', 'WS发送base64帧→接收result JSON, record写入train_records表正确'],
    ['W2', 'routers/fms_router.py', '/start(test_actions可选5动作), WS /ws/{sid}(逐动作test_start/test_result/fms_complete), /records, /records/{id}(雷达图+lock数据)', '1d', '5动作逐项WS流程正常: test_start→send frame→recv test_result 循环→fms_complete'],
    ['W3', 'routers/prescription_router.py', '/generate(fms_record_id→B.generate()), /active, /{id}/follow+WS(phase切换), /{id}/progress(B.get_progress()), /{id}/unlock-request, /{id}/adjust(coach)', '2d', '处方生成→入库→跟练→解锁完整链路: 4阶段顺序正确, WS phase_change推送'],
    ['W3', 'routers/learn_router.py', '/start(加载标准数据), WS /ws/{sid}(逐帧compare→diffs+score+feedback)', '1d', 'WS返回逐帧learn_result: differences各字段user/standard/diff完整'],
    ['W3', '(联调D)', '与Person D联调 Auth+Train+FMS 三个模块', '1d', '前端可调通 /api/auth/login, /api/train/start, /api/fms/start 并接收WS消息'],
    ['W4', 'routers/checkin_router.py', 'POST /checkin(B.checkin()), GET /status(今日+streak), GET /calendar(月视图), GET /badges(徽章列表)', '1d', '打卡→streak+1→7天徽章: 逻辑正确, badge插入badges表'],
    ['W4', 'routers/actions_router.py', 'GET /library(分页+category筛选), POST /library(coach新增), PUT /library/{id}(coach编辑), GET /tags, POST /mapping(coach)', '1d', '动作库CRUD正常, 标签映射正确关联action_library'],
    ['W4', 'routers/admin_router.py', 'POST /classes(创建班级), GET /classes/{id}/stats(B.class_stats()), POST /classes/{id}/import(Excel解析+批量创建), GET /logs(分页+级别筛选), GET /dashboard(统计)', '2d', 'Excel导入: 列(username|password|gender)→批量注册, stats班级统计数值正确'],
    ['W5', 'utils/pdf_exporter.py', 'ReportLab: FMS雷达图PDF(含图表/评分/建议), 训练报告PDF(角度曲线+反馈), 打卡卡片图片导出', '2d', 'PDF含图表+中文, 格式与前端一致, 可正常打开'],
    ['W5', 'websocket/ws_manager.py', '心跳检测(15s间隔), 断线重连, 连接数统计, 4种session类型管理(train/fms/learn/prescription)', '1d', '100并发WS连接稳定, 断线自动重连(指数退避), session清理正确'],
    ['W5', '性能优化', 'SQLAlchemy连接池调优, 慢查询优化(索引+EXPLAIN), Redis缓存热点数据(动作库/标签映射), API响应时间优化', '1d', 'P95 REST响应<200ms, WS帧处理<100ms, DB单表查询<50ms'],
    ['W6', '集成测试', '33端点pytest+httpx各>=3case(正常/边界/异常), 4种WS session测试(连接/收发/断连重连)', '2d', '覆盖率>90%, 全部测试用例通过'],
    ['W6', '安全加固+部署', 'SQL注入防护, XSS过滤, CORS白名单, 速率限制(60/min), Dockerfile+requirements.txt', '2d', 'OWASP Top10基础检查通过, Docker compose一键启动成功'],
])
doc.add_page_break()

# ═══════════════════════════════════
# Person D
# ═══════════════════════════════════
doc.add_heading('六、Person D — 前端应用层 (W2-W6, ~24人天)', level=1)
add_note(doc, 'React 18 + Vite + Ant Design + ECharts + WebSocket + Web Speech API + Canvas。18页面，6新组件。')

add_table(doc, ['周次', '文件/模块', '任务(函数级)', '工时', '交付验收标准'], [
    ['W2', '项目骨架', 'React 18 + Vite + Ant Design + React Router v6 + src目录结构(pages/components/hooks/store/utils)', '1d', 'npm run dev启动成功, /login /register /home 路由可访问'],
    ['W2', '通用组件', 'WebSocketProvider(Context), useWebSocket Hook(连接/重连/消息分发), AuthGuard(路由守卫), Layout(侧边栏+顶栏)', '1d', '未登录自动跳转/login, WS连接/断线重连正常, 侧边栏导航正确'],
    ['W2', '登录/注册/首页', 'LoginPage(Ant Design Form+JWT存储), RegisterPage(角色选择), HomePage(快捷入口+连续天数+最近训练)', '2d', '含表单校验(用户名4-20字/密码6位+), JWT存入localStorage, 首页数据加载'],
    ['W3', 'FMS筛查页', 'FMSPage: MediaRecorder获取摄像头, Canvas抽帧→WS发送, 逐动作引导UI, 实时骨架叠加(SkeletonCanvas)', '2d', '5动作完整流程可跑通: 授权→开始→逐动作检测→进度条→完成'],
    ['W3', 'FMS报告页', 'FMSReportPage: ECharts雷达图(RadarChart), 新旧对比叠加(ComparisonRadar), 锁定建议(LockSuggestions), PDF导出按钮', '1d', '雷达图5维度正确渲染, 新旧对比箭头(↑+5)正确, 锁定建议展示原因'],
    ['W3', '训练页', 'TrainPage: video元素+Canvas骨骼叠加, ECharts实时角度折线图(AngleChart), VoiceFeedback组件, StageIndicator阶段显示', '2d', '实时骨架(>=20fps), 角度折线图实时更新, TTS播报(基础仅error, 进阶逐条)'],
    ['W4', '处方+解锁页', 'PrescriptionPage: 4阶段PhaseCard展示(热身/强化/主训练/冷身), 激活/切换按钮。UnlockPage: UnlockProgress组件(Ant Progress+条件文案+提前解锁按钮)', '2d', '处方4阶段卡片正确展示, 进度条百分比准确, 提前解锁按钮弹出安全测试'],
    ['W4', '处方跟练页', 'FollowPage: 同TrainPage结构但增加phase切换推送(热身→强化→主训练→冷身)', '1d', 'WS接收phase_change消息后正确切换动作列表和UI'],
    ['W4', '标准学习页', 'LearnPage: DualSkeleton(video双骨架叠加:用户+标准), DiffBarChart(ECharts差异柱状图), 逐帧回放控制', '2d', '双骨架颜色区分(用户蓝/标准绿), 差异柱状图正负值颜色(红/蓝)'],
    ['W5', '打卡页', 'CheckinPage: CheckinButton(打卡), StreakDisplay(连续天数动画), CheckinCard(Canvas渲染:渐变+天数+动作列表+二维码), BadgeModal(徽章弹窗)', '2d', '打卡后streak数字跳动动画, Canvas输出DataURL非空, 二维码可扫描'],
    ['W5', '历史+统计页', 'HistoryPage: ECharts趋势折线图(7/30/90天标签切换), HistoryDetailPage: 角度曲线+反馈汇总+导出PDF+分享按钮', '1d', '趋势图数据正确, 时间标签切换响应<500ms, 导出按钮触发下载'],
    ['W5', '个人中心', 'ProfilePage: 信息编辑(昵称/性别), 生理周期设置(cycle_length+last_period_date), 密码修改', '1d', '表单校验+保存后数据刷新, 周期设置后影响处方强度显示'],
    ['W6', '学员管理', 'AdminStudentsPage: Ant Design Table(搜索/排序/分页), BatchImportModal(Upload+Table预览+确认导入)', '1d', 'Excel导入: 选择文件→预览→确认→批量注册, 失败行提示原因'],
    ['W6', '班级统计+动作库', 'ClassStatsPage: ClassRadarChart(班级均值vs个体), RiskTable(红/黄/绿), SymmetryWarnings。AdminLibraryPage: Table(CRUD)', '1d', '班级雷达图+个体叠加正确, 风险分布表数值准确'],
    ['W6', '系统设置', 'SettingsPage: ModelSwitcher(YOLO/MediaPipe切换按钮), FPS滑块(15/25/30), LogList(日志列表+筛选), BatchImportModal复用', '0.5d', '切换模型后训练页推理正常, 日志列表分页+级别筛选正常'],
    ['W6', '响应式+测试', '18页面1920/1366分辨率适配, Jest+RTL关键组件测试(VoiceFeedback/UnlockProgress/CheckinCard)', '1d', '两分辨率无溢出/重叠, 6组件测试通过'],
    ['W6', '联调+E2E', '全量接口联调(33端点), Playwright E2E: 注册→FMS→处方→跟练→打卡完整旅程', '1d', '核心用户旅程通过Playwright, 无阻塞bug'],
])
doc.add_page_break()

# ═══════════════════════════════════
# 汇总
# ═══════════════════════════════════
doc.add_heading('七、工时汇总与风险', level=1)

add_table(doc, ['角色', '总人天', '周次范围', '缓冲时间', '主要风险'], [
    ['Person A', '20人天', 'W1-W5', '+1d(W2角度精度校验)', 'YOLO模型下载/兼容性; 角度精度<3°可能需额外调优'],
    ['Person B', '30人天', 'W1-W6', '+2d(W3识别器准确率)', '9个识别器调试工作量大; Tag→Action映射规则需教练确认; StandardLearner反馈准确率'],
    ['Person C', '28人天', 'W1-W6', '+2d(W5 PDF生成)', '14张表DDL变更管理; 4种WS session并发稳定性; PDF中文渲染'],
    ['Person D', '24人天', 'W2-W6', '+1d(W6 E2E测试)', 'Canvas/WebGL性能(低配设备); TTS浏览器兼容性; 18页面响应式工作量'],
    ['合计', '102人天', '6周', '+6d缓冲', '总计约108人天, 4人并行约5.4周, 6周工期充裕'],
])

doc.add_heading('八、关键依赖与并行策略', level=1)
add_table(doc, ['阶段', '依赖关系', '并行策略'], [
    ['W1-W2', 'A→B: B识别器需要A的角度输出格式(可先用mock)', 'A和B并行: A先完成ModelEngine+AngleUtils, B用mock数据开发识别器'],
    ['W2-W3', 'B→C: C需要B的业务JSON格式(可先对齐schema)', 'B和C并行: 先对齐JSON schema, B用mock引擎, C用mock数据开发API'],
    ['W3-W4', 'C→D: D需要C的API接口(可先对齐接口文档)', 'C和D并行: 基于API文档v3.0开发, W3联调关键3个模块'],
    ['W4-W5', '全体集成: 前后端联调 + B/C联调', 'D优先完成核心页面(FMS/训练), C优先完成核心API(Auth/Train/FMS)'],
    ['W5-W6', '测试+优化: 性能测试 → 修复 → 回归', 'A/D并行测试和修复, B/C并行集成测试'],
])

doc.add_heading('九、每日站会议题 (建议)', level=1)
doc.add_paragraph('1. 昨天完成了什么? (对应周计划哪个任务项)')
doc.add_paragraph('2. 今天计划做什么? (预计工时, 是否阻塞)')
doc.add_paragraph('3. 遇到什么问题? (技术难点/依赖方未就绪/需求变化)')
doc.add_paragraph('4. 接口对齐: A↔B角度格式, B↔C业务JSON, C↔D API格式是否有变化?')

footer(doc)

# =================== SAVE ===================
output_path = 'D:/workbench/program3/plan/任务书-周计划_v1.0.docx'
doc.save(output_path)
print('SUCCESS: Weekly Plan saved to ' + output_path)
