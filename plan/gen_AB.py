
doc = make_doc(); set_heading_style(doc)
cover(doc, '开发任务书 — Person A（v3.0）', '模型推理层', '负责: YOLO-Pose引擎 + 姿态分析 + 数据输出')

doc.add_heading('一、职责范围', level=1)
add_note(doc, '核心原则：你只负责输出结构化数据，不涉及任何业务逻辑。v3.0 无新增模块，但需要关注管理员可切换 MediaPipe 模式的需求。')
doc.add_paragraph('你的代码是整个项目的数据来源。所有下游模块（B、C、D）都依赖你输出的关键点数据和角度数据。v3.0 新增的标准学习模块需要你提供高精度的角度计算用于逐帧对比。')

doc.add_heading('二、文件清单（v3.0 无新增文件，但有精度要求提升）', level=1)
add_table(doc, ['文件', '状态', 'v3.0要求'], [
    ['models/yolo_pose_engine.py', '已有', '性能稳定即可, 补充帧率统计接口 get_fps()'],
    ['models/model_engine.py', '新增', '抽象基类: infer/extract/draw + load(model_path) 支持运行时切换模型'],
    ['models/pose_analyzer.py', '新增', '角度精度需 <3度(标准学习需要逐帧精确对比)'],
    ['models/angle_utils.py', '新增', 'calc_angle/calc_vector_angle 纯函数'],
    ['utils/pose_postprocessor.py', '已有', '无变化'],
    ['utils/visualization.py', '新增', 'draw_skeleton/draw_angles 辅助函数'],
])

doc.add_heading('三、核心数据契约（与v2.0相同）', level=1)
doc.add_paragraph('关键点数据格式和 PoseAnalyzer 输出格式不变，参见 v2.0 文档。以下为新增要求：')

doc.add_heading('3.1 角度精度要求', level=2)
add_note(doc, 'v3.0 新增单动作标准学习功能，需要逐帧对比用户动作与标准动作的关节角度。角度计算误差必须 <3度，否则差异柱状图会明显失真。')
doc.add_paragraph('建议：人工标注100组关键点，手动计算角度真值，与 PoseAnalyzer 输出对比，确保误差在容忍范围内。')

doc.add_heading('3.2 帧率统计接口（新增）', level=2)
add_code(doc,
    '# yolo_pose_engine.py 需新增:\n'
    'class YOLOPoseEngine:\n'
    '    def get_fps(self) -> float:\n'
    '        """返回最近N帧的平均推理帧率"""\n'
    '        ...'
)
doc.add_paragraph('管理员后台需要展示模型推理性能，Person C 会调用此接口。')

doc.add_heading('四、验收标准', level=1)
add_table(doc, ['编号', '标准'], [
    ['A1', '关键点输出格式100%符合数据契约'],
    ['A2', '17个关键点检测准确率 >= 95%'],
    ['A3', '推理速度 >= 25fps (GPU)'],
    ['A4', '角度计算误差 < 3度（v3.0精度提升）'],
    ['A5', 'PoseAnalyzer 对所有动作类型返回完整15个角度字段'],
    ['A6', 'ModelEngine 抽象接口支持运行时模型切换（YOLO/MediaPipe）'],
    ['A7', '遮挡/截断处理不崩溃'],
    ['A8', '提供 get_fps() 接口供管理员监控'],
])

footer(doc)
doc.save('D:/workbench/program3/plan/任务书-PersonA-模型推理层.docx')
print('A v3 done')


doc = make_doc(); set_heading_style(doc)
cover(doc, '开发任务书 — Person B（v3.0）', '业务引擎层', '负责: 动作识别 + FMS + 评分 + 处方 + 标准学习 + 打卡 + 班级统计')

doc.add_heading('一、职责范围（v3.0 大幅扩展）', level=1)
add_note(doc, 'v3.0 新增5个模块：标准学习引擎、打卡激励引擎、解锁进度管理、班级统计引擎、周期性复测升级。你负责的模块从17个文件增加到22+个文件。')
doc.add_paragraph()

doc.add_heading('二、v3.0 新增文件', level=1)
add_table(doc, ['文件', '类名', '优先级', '说明'], [
    ['models/standard_learner.py', 'StandardLearner', '最高', '逐帧对比用户与标准动作，计算各关节角度差异，生成精细化反馈'],
    ['models/checkin_engine.py', 'CheckinEngine', '高', '连续天数计算+徽章判定(7天/30天)+中断清零+鼓励语生成'],
    ['models/unlock_manager.py', 'UnlockManager', '高', '各维度进度条+解锁条件判定+提前解锁安全测试逻辑'],
    ['models/class_stats.py', 'ClassStatsEngine', '高', '班级雷达图(平均)+风险分布+对称异常名单+共性弱点'],
    ['models/fms/fms_engine.py', 'FMSEngine', '修改', '新增 compare_reports() 新旧对比方法'],
    ['models/prescription/prescription_engine.py', 'PrescriptionEngine', '修改', '新增 upgrade_on_retest() 复测自动升级方法'],
])

doc.add_paragraph()
doc.add_paragraph('已有17个文件（9个动作识别器+6个引擎+2个管理器）保持不变，仅需增强 fms_engine 和 prescription_engine。')

doc.add_page_break()

doc.add_heading('三、v3.0 新模块接口定义', level=1)

doc.add_heading('3.1 StandardLearner（标准学习引擎）', level=2)
add_code(doc,
    '# models/standard_learner.py\n'
    'class StandardLearner:\n'
    '    def __init__(self, action_id: int, standard_keypoints: list[dict]):\n'
    '        """加载标准动作关键点数据（正面/侧面/背面）"""\n'
    '        ...\n'
    '    \n'
    '    def compare(self, person_data: dict, view: str = "front") -> dict:\n'
    '        """\n'
    '        输入: Person A 的角度数据\n'
    '        view: "front"|"side"|"back"\n'
    '        返回: {\n'
    '            "differences": {\n'
    '                "left_knee": {"user":95,"standard":85,"diff":+10},\n'
    '                "right_elbow": {"user":170,"standard":160,"diff":+10},\n'
    '                ...\n'
    '            },\n'
    '            "max_diff_joint": "left_knee",\n'
    '            "feedback": "左膝弯度不足，请再下蹲10度\",\n'
    '            "score": 78,   # 当前帧的标准度\n'
    '            "overall_score": 82  # 累计标准度\n'
    '        }\n'
    '        """\n'
    '        ...\n'
    '    \n'
    '    def get_common_errors(self) -> list[dict]:\n'
    '        """返回该动作的常见错误列表"""\n'
    '        ...\n'
    '    \n'
    '    def get_final_score(self) -> dict:\n'
    '        """学习结束后返回: {total_score, per_joint_scores, suggestions}"""\n'
    '        ...'
)

doc.add_heading('3.2 CheckinEngine（打卡激励引擎）', level=2)
add_code(doc,
    '# models/checkin_engine.py\n'
    'class CheckinEngine:\n'
    '    def __init__(self, user_id: int):\n'
    '        self.user_id = user_id\n'
    '        self.streak = 0           # 当前连续天数\n'
    '        self.streak_highest = 0   # 历史最高\n'
    '        self.badges = []          # 已获得徽章\n'
    '    \n'
    '    def checkin(self, actions_completed: list[str]) -> dict:\n'
    '        """\n'
    '        每日打卡\n'
    '        返回: {\n'
    '            "date": "2026-06-23",\n'
    '            "streak": 8,\n'
    '            "streak_highest": 15,\n'
    '            "actions": ["深蹲x15","俯卧撑x10"],\n'
    '            "encouragement": "连续打卡8天！坚持就是胜利！",\n'
    '            "new_badge": "week_streak"|"month_streak"|null,\n'
    '            "badges": ["week_streak"]\n'
    '        }\n'
    '        """\n'
    '        ...'
)

doc.add_heading('3.3 UnlockManager（解锁进度管理）', level=2)
add_code(doc,
    '# models/unlock_manager.py\n'
    'class UnlockManager:\n'
    '    def get_progress(self, fms_report: dict, locked_actions: list) -> dict:\n'
    '        """\n'
    '        返回各维度的解锁进度:\n'
    '        {\n'
    '            "core": {"current":45,"target":65,"progress":0.69,"actions_locked":["负重深蹲"]},\n'
    '            "balance": {"current":72,"target":50,"progress":1.0,"unlocked":true}\n'
    '        }\n'
    '        """\n'
    '        ...\n'
    '    \n'
    '    def check_unlock(self, old_fms: dict, new_fms: dict, locked: list) -> list:\n'
    '        """复测后检查哪些动作应解锁，返回已解锁列表"""\n'
    '        ...\n'
    '    \n'
    '    def early_unlock_test(self, action_name: str) -> dict:\n'
    '        """提前解锁安全测试: 返回 {passed: bool, test_results: {...}}"""\n'
    '        ...'
)

doc.add_heading('3.4 ClassStatsEngine（班级统计引擎）', level=2)
add_code(doc,
    '# models/class_stats.py\n'
    'class ClassStatsEngine:\n'
    '    def __init__(self, student_fms_records: list[dict]):\n'
    '        """传入班级所有学员的最新FMS记录"""\n'
    '        ...\n'
    '    \n'
    '    def get_radar(self) -> dict:\n'
    '        """班级平均5维雷达图数据"""\n'
    '        ...\n'
    '    \n'
    '    def get_risk_students(self) -> list:\n'
    '        """高风险学员列表(任一维度<40) + 受限维度说明"""\n'
    '        ...\n'
    '    \n'
    '    def get_asymmetry_students(self) -> list:\n'
    '        """左右对称性异常学员(symmetry<50)"""\n'
    '        ...\n'
    '    \n'
    '    def get_common_weakness(self) -> list[str]:\n'
    '        """班级共性弱点: 出现频率最高的3个问题标签"""\n'
    '        ...'
)

doc.add_page_break()

doc.add_heading('四、验收标准（v3.0 新增部分）', level=1)
add_table(doc, ['编号', '标准', 'v3.0'], [
    ['B1-B7', '同 v2.0 标准', '-'],
    ['B8', 'StandardLearner 逐帧对比准确，角度差异计算正确', '新增'],
    ['B9', 'CheckinEngine 连续天数+徽章判定逻辑正确', '新增'],
    ['B10', 'UnlockManager 进度计算+解锁判定+安全测试通过', '新增'],
    ['B11', 'ClassStatsEngine 雷达图+风险预警+共性弱点正确', '新增'],
    ['B12', 'FMSEngine.compare_reports() 新旧对比正确', '新增'],
    ['B13', 'PrescriptionEngine.upgrade_on_retest() 复测升级正确', '新增'],
])

footer(doc)
doc.save('D:/workbench/program3/plan/任务书-PersonB-业务引擎层.docx')
print('B v3 done')
