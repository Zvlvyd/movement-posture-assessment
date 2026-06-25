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

# Copy helpers from gen_helpers.py
exec(compile(open('D:/workbench/program3/plan/gen_helpers.py', encoding='utf-8').read(), 'gen_helpers.py', 'exec'))

# =================== Build Document ===================
doc = make_doc()
set_heading_style(doc)
cover(doc, '详细设计文档', 'v1.0 深度版', '基于 YOLO-Pose 的运动姿态评估与纠错系统')

# ── 修订说明 ──
doc.add_heading('修订说明', level=1)
doc.add_paragraph('本文档基于概要设计 v3.0 和 API 接口文档 v3.0 深化，覆盖四层架构的完整类设计、时序流程、数据库 DDL、状态机定义、前端组件树、错误码、测试策略和部署配置。')
doc.add_paragraph('适用读者：全体开发人员（Person A/B/C/D）、架构师、项目管理者。')

doc.add_heading('参考文档', level=2)
for d in ['03-运动姿态评估与纠错系统-需求说明书 v1.0','概要设计计划文档 v3.0','API接口文档 v3.0','任务书-PersonA/B/C/D（v3.0）']:
    doc.add_paragraph('· ' + d, style='List Bullet')

doc.add_heading('术语表', level=2)
add_table(doc, ['缩写', '全称', '说明'], [
    ['FMS', 'Functional Movement Screen', '功能性动作筛查，5个动作评估'],
    ['FSM', 'Finite State Machine', '有限状态机，用于动作阶段识别'],
    ['YOLO', 'You Only Look Once', '实时目标检测算法'],
    ['COCO', 'Common Objects in Context', '17关键点标注格式'],
    ['WS', 'WebSocket', '全双工通信协议，用于实时帧流'],
    ['TTS', 'Text to Speech', '文本转语音，Web Speech API'],
    ['JWT', 'JSON Web Token', '无状态认证令牌'],
    ['ROI', 'Region of Interest', '关键点感兴趣区域'],
])
doc.add_page_break()

print('Section 0 done')
# premature save removed



# ═══════════════════════════════════
# 第一章：模块详细设计
# ═══════════════════════════════════
doc.add_heading('一、模块详细设计', level=1)
add_note(doc, '本章按四层架构逐模块展开，每个类/模块给出：职责、属性、公开方法签名、依赖关系、关键算法伪代码。')

# --- Person A (模型推理层) ---
doc.add_heading('1.1 Person A — 模型推理层', level=2)
doc.add_paragraph('职责：接收原始图像帧，输出17关键点坐标和7个关节角度。不涉及任何业务逻辑。所有下游模块（B/C/D）的数据来源。')

doc.add_heading('1.1.1 文件清单与依赖关系', level=3)
add_table(doc, ['文件', '类名', '职责', '依赖', 'v3.0状态'], [
    ['models/model_engine.py', 'ModelEngine', '抽象基类: infer/extract/draw/load', '无', '新增'],
    ['models/yolo_pose_engine.py', 'YOLOPoseEngine', 'YOLOv8-Pose推理+get_fps()', 'ModelEngine, ultralytics', '已有，补充get_fps()'],
    ['models/mediapipe_engine.py', 'MediaPipeEngine', 'MediaPipe Pose预留', 'ModelEngine, mediapipe', '新增(预留)'],
    ['models/pose_analyzer.py', 'PoseAnalyzer', '关键点→7关节角度, 精度<3°', 'angle_utils, numpy', '新增'],
    ['models/angle_utils.py', '(纯函数)', 'calc_angle/vector_angle/normalize', 'numpy', '新增'],
    ['utils/pose_postprocessor.py', 'PosePostProcessor', '卡尔曼滤波+置信度过滤+ID跟踪', 'numpy, filterpy', '已有'],
    ['utils/visualization.py', '(纯函数)', 'draw_skeleton+角度标注+FPS显示', 'cv2, numpy', '新增'],
])

doc.add_heading('1.1.2 ModelEngine 抽象基类', level=3)
add_code(doc, '# models/model_engine.py\
from abc import ABC, abstractmethod\
import numpy as np\
\
class ModelEngine(ABC):\
    def __init__(self, device="auto"):\
        self.device = device\
    \
    @abstractmethod\
    def load(self, model_path: str) -> None: ...\
    \
    @abstractmethod\
    def infer(self, frame: np.ndarray) -> list[dict]:\
        """返回: [{keypoints:[[x,y,conf]*17], bbox, conf}]"""\
    \
    @abstractmethod\
    def extract_keypoints(self, results) -> list[dict]: ...\
    \
    @abstractmethod\
    def draw_skeleton(self, frame, persons) -> np.ndarray: ...\
    \
    @abstractmethod\
    def get_fps(self) -> float:\
        """返回最近N帧平均推理帧率"""')

doc.add_heading('1.1.3 YOLOPoseEngine', level=3)
add_code(doc, '# models/yolo_pose_engine.py\
class YOLOPoseEngine(ModelEngine):\
    def __init__(self, model_path="yolov8n-pose.pt", device="auto",\
                 conf_threshold=0.5):\
        super().__init__(device=device)\
        self._fps_history = []  # 最近100帧耗时\
        self.load(model_path)\
    \
    def load(self, model_path):\
        from ultralytics import YOLO\
        self.model = YOLO(model_path)\
        self.model.to(self.device)\
    \
    def infer(self, frame):\
        import time; t0 = time.perf_counter()\
        results = self.model(frame, verbose=False)\
        elapsed = (time.perf_counter()-t0)*1000\
        self._fps_history.append(elapsed)\
        if len(self._fps_history) > 100: self._fps_history.pop(0)\
        return self._parse_results(results[0])\
    \
    def get_fps(self):\
        if not self._fps_history: return 0.0\
        avg_ms = sum(self._fps_history) / len(self._fps_history)\
        return 1000.0 / avg_ms')

doc.add_heading('1.1.4 PoseAnalyzer — 角度计算核心', level=3)
add_note(doc, '精度要求 <3度，是标准学习模块的基础。需人工标注100组关键点验证。')
add_code(doc, '# models/pose_analyzer.py\
import numpy as np\
from .angle_utils import calc_angle\
\
class PoseAnalyzer:\
    # COCO 17关键点索引\
    KP = {nose:0,left_eye:1,right_eye:2,left_ear:3,right_ear:4,\
          left_shoulder:5,right_shoulder:6,left_elbow:7,right_elbow:8,\
          left_wrist:9,right_wrist:10,left_hip:11,right_hip:12,\
          left_knee:13,right_knee:14,left_ankle:15,right_ankle:16}\
    \
    def analyze_frame(self, keypoints) -> dict:\
        """返回: {angles:{left_knee,right_knee,left_hip,right_hip,\
                  left_shoulder,right_shoulder,trunk}, confidence:{...}}"""\
        kp = keypoints\
        angles = {}\
        angles["left_knee"] = calc_angle(kp[11],kp[13],kp[15])\
        angles["right_knee"] = calc_angle(kp[12],kp[14],kp[16])\
        angles["left_hip"] = calc_angle(kp[5],kp[11],kp[13])\
        angles["right_hip"] = calc_angle(kp[6],kp[12],kp[14])\
        angles["left_shoulder"] = calc_angle(kp[7],kp[5],kp[11])\
        angles["right_shoulder"] = calc_angle(kp[8],kp[6],kp[12])\
        # 躯干前倾: hip中点-shoulder中点 vs 垂直线\
        angles["trunk"] = self._trunk_lean(kp)\
        return {"angles":angles,"timestamp":__import__("time").time()}\
    \
    def _trunk_lean(self, kp) -> float:\
        mid_hip = ((kp[11][0]+kp[12][0])/2, (kp[11][1]+kp[12][1])/2)\
        mid_shld = ((kp[5][0]+kp[6][0])/2, (kp[5][1]+kp[6][1])/2)\
        return calc_angle(mid_hip, mid_shld, (mid_shld[0],mid_shld[1]-100))')

doc.add_heading('1.1.5 AngleUtils 纯函数', level=3)
add_code(doc, '# models/angle_utils.py\
import math\
\
def calc_angle(A, B, C) -> float:\
    """三点角度 ∠ABC (B为顶点), 返回0~180度"""\
    BA = (A[0]-B[0], A[1]-B[1])\
    BC = (C[0]-B[0], C[1]-B[1])\
    dot = BA[0]*BC[0] + BA[1]*BC[1]    mag_BA = math.sqrt(BA[0]**2+BA[1]**2)\
    mag_BC = math.sqrt(BC[0]**2+BC[1]**2)\
    if mag_BA*mag_BC == 0: return 0.0\
    cos = max(-1.0, min(1.0, dot/(mag_BA*mag_BC)))\
    return math.degrees(math.acos(cos))\
\
def calc_vector_angle(v1, v2) -> float:\
    """两个向量夹角(0~180)""" ...\
def normalize_angle(a) -> float:\
    return max(0.0, min(180.0, a))')

doc.add_page_break()
print('Person A done')


# --- Person B (业务引擎层) ---
doc.add_heading('1.2 Person B — 业务引擎层 (22+文件)', level=2)
doc.add_paragraph('职责：消费 Person A 的角度数据，执行动作识别、FMS评分、处方生成、标准学习、打卡激励、解锁管理、班级统计等全部业务逻辑。')

doc.add_heading('1.2.1 文件清单', level=3)
add_table(doc, ['文件', '类名', '优先级', '说明'], [
    ['recognizers/base_recognizer.py', 'BaseRecognizer', '最高', 'FSM状态机基类(Stage枚举)'],
    ['recognizers/squat_recognizer.py', 'SquatRecognizer', '最高', '深蹲: idle→down→bottom→up→complete'],
    ['recognizers/pushup_recognizer.py', 'PushupRecognizer', '最高', '俯卧撑FSM识别'],
    ['recognizers/lunge_recognizer.py', 'LungeRecognizer', '高', '弓步蹲(左右分别)'],
    ['recognizers/plank_recognizer.py', 'PlankRecognizer', '高', '平板支撑(计时)'],
    ['recognizers/overhead_press.py', 'OverheadPressRecognizer', '高', '过头推举'],
    ['recognizers/deadlift_recognizer.py', 'DeadliftRecognizer', '中', '硬拉'],
    ['recognizers/glute_bridge.py', 'GluteBridgeRecognizer', '中', '臀桥'],
    ['recognizers/lateral_raise.py', 'LateralRaiseRecognizer', '中', '侧平举'],
    ['recognizers/crunch_recognizer.py', 'CrunchRecognizer', '中', '卷腹'],
    ['fms/fms_engine.py', 'FMSEngine', '最高', '5动作评分+雷达图+问题标签+新旧对比'],
    ['prescription/prescription_engine.py', 'PrescriptionEngine', '最高', '规则引擎: Tag→4阶段处方+锁定+复测升级'],
    ['standard_learner.py', 'StandardLearner', '最高', '逐帧对比: 差异+评分+反馈'],
    ['checkin_engine.py', 'CheckinEngine', '高', '连续天数+徽章(7/30天)+鼓励语'],
    ['unlock_manager.py', 'UnlockManager', '高', '进度条+解锁判定+提前解锁安全测试'],
    ['class_stats.py', 'ClassStatsEngine', '高', '班级雷达图+风险分布+共性弱点'],
    ['cycle_manager.py', 'CycleManager', '中', '生理周期适配+自动调整强度'],
])

doc.add_heading('1.2.2 BaseRecognizer — FSM状态机基类', level=3)
add_code(doc, '# models/recognizers/base_recognizer.py\
from enum import Enum\
\
class Stage(Enum):\
    IDLE="idle"\
    READY="ready"        # 检测到关键点,准备就绪\
    DOWN="down"           # 离心阶段\
    BOTTOM="bottom"       # 底部保持\
    UP="up"               # 向心阶段\
    COMPLETE="complete"   # 单次完成\
    FINISHED="finished"   # 全部完成\
\
class BaseRecognizer:\
    def __init__(self, config):\
        self.stage = Stage.IDLE\
        self.rep_count = 0\
        self.angles_history = []\
    \
    def update(self, angles: dict, score_callback=None) -> dict:\
        """核心更新方法, 由子类重写\
        返回: {stage, rep_count, is_complete, feedback, risk_level, score}"""\
        raise NotImplementedError()\
    def is_complete(self) -> bool: return self.rep_count >= self.target\
    def get_progress(self) -> float: return self.rep_count / self.target')

doc.add_heading('1.2.3 SquatRecognizer FSM 完整定义 (深蹲示例)', level=3)
add_code(doc, '# 深蹲 FSM 状态转移表:\
#   idle    → hip>160° → ready ("准备就绪, 请下蹲")\
#   ready   → hip<150° → down  ("匀速下蹲")\
#   down    → knee<90° → bottom ("到达底部, 检查膝内扣")\
#   bottom  → hip>120° → up    ("向上站起")\
#   up      → hip>160° → complete → rep_count++ ("完成第N次")\
#   complete → auto → ready (继续下一rep)\
#   rep_count>=target → FINISHED ("深蹲完成, 共N次")\
\
# 评分逻辑 (basic模式):\
#   膝内扣检测: |left_knee - right_knee| > 15° → risk=yellow\
#   深度不足: knee_bottom > 100° → risk=yellow\
#   advanced模式额外检查: 躯干前倾>30° → risk=red')

doc.add_heading('1.2.4 FMSEngine — 功能性动作筛查引擎', level=3)
add_code(doc, '# models/fms/fms_engine.py\
class FMSEngine:\
    DIMENSIONS = ["balance","flexibility","shoulder","core","symmetry"]\
    \
    def score_balance(self, keypoints_seq, duration) -> dict:\
        """闭眼单腿站立: score = max(0,100-sway*2) * min(duration/30,1.0)"""\
    def score_flexibility(self, keypoints_seq) -> dict:\
        """过头深蹲: 评估髋/膝/踝联动灵活性"""\
    def score_shoulder(self, kp_left, kp_right) -> dict:\
        """肩活动度: 左右各3次"""\
    def score_core(self, keypoints_seq, duration) -> dict:\
        """平板支撑: 至力竭, 评估核心稳定性"""\
    def score_symmetry(self, kp_left, kp_right) -> dict:\
        """弓步蹲: 左右各3次, 评估对称性"""\
    \
    def aggregate(self) -> dict:\
        """汇总→雷达图+问题标签+锁定建议\
        锁定条件: 核心<40 / 平衡<30 / 对称<50"""\
    def compare_reports(self, old_id, new_id) -> dict:\
        """v3.0: 新旧FMS报告对比"""')

doc.add_heading('1.2.5 PrescriptionEngine — 处方生成引擎', level=3)
add_code(doc, '# models/prescription/prescription_engine.py\
class PrescriptionEngine:\
    PHASES = ["warmup","strengthen","main","cooldown"]\
    \
    def generate(self, fms_result, user_id) -> dict:\
        """基于FMS结果生成个性化4阶段处方\
        1) warmup: 通用动态拉伸\
        2) strengthen: Tag→Action映射(难度升序)\
        3) main: 基础动作(排除锁定)\
        4) cooldown: 静态拉伸"""\
    \
    def upgrade_on_retest(self, old_fms, new_fms, current_rx) -> dict:\
        """v3.0: 复测后自动升级处方, 解锁动作可加入主训练"""')

doc.add_heading('1.2.6 StandardLearner / CheckinEngine / UnlockManager', level=3)
add_table(doc, ['引擎', '核心方法签名', '关键逻辑'], [
    ['StandardLearner', 'compare(person_data, view)→dict', '逐帧对比7关节角度→输出差异(user/standard/diff)→累计评分→生成中文反馈("左膝弯度不足，请再下蹲10度")'],
    ['CheckinEngine', 'checkin(actions)→dict', '查询昨日打卡→连续则streak+1否则reset=1→streak==7→week_streak徽章→streak==30→month_streak'],
    ['UnlockManager', 'get_progress(fms,locks)→dict', '进度=(当前-阈值)/(目标-阈值) → check_unlock: 新旧FMS对比→维度提升>阈值→解锁对应动作'],
    ['ClassStatsEngine', 'calc_class_avg(users)→dict', '遍历班级FMSEngine最新记录→5维度均值→风险分布(红<40/黄40-70/绿>70)→共性弱点'],
    ['CycleManager', 'auto_adjust(phase,rx)→dict', '经期(1-7): intensity-2,替换跳跃→拉伸。卵泡期(8-14): intensity+1。黄体期(15-28): 正常'],
])

doc.add_page_break()
print('Person B done')


# --- Person C (后端API层) ---
doc.add_heading('1.3 Person C — 后端API层 (14张表, 33端点, 4种WS)', level=2)
doc.add_paragraph('职责：FastAPI服务、33个REST端点、4种WebSocket Session、JWT认证、MySQL/Redis/MinIO数据管理、PDF报告生成、管理后台。')

doc.add_heading('1.3.1 项目目录结构', level=3)
add_code(doc, 'backend/\
├── app.py                  # FastAPI入口+中间件注册\
├── config.py               # pydantic Settings配置管理\
├── auth/\
│   ├── jwt_handler.py      # JWT签发/验证/刷新(bcrypt+24h有效期)\
│   └── dependencies.py     # Depends(get_current_user)\
├── routers/\
│   ├── auth_router.py      # /api/auth/* (注册/登录/登出/me)\
│   ├── train_router.py     # /api/train/* + WS帧流\
│   ├── fms_router.py       # /api/fms/* + WS逐动作测试\
│   ├── prescription_router.py  # /api/prescriptions/* + WS跟练\
│   ├── learn_router.py     # /api/learn/* + WS逐帧对比\
│   ├── checkin_router.py   # /api/checkin/* (打卡/状态/日历/徽章)\
│   ├── actions_router.py   # /api/actions/* (CRUD+标签+映射)\
│   ├── admin_router.py     # /api/admin/* (班级/日志/仪表盘)\
│   └── profile_router.py   # /api/profile/* + /api/history/*\
├── services/               # 业务服务层(注入Person B引擎)\
├── models/db_models.py     # SQLAlchemy ORM 14表定义\
├── websocket/\
│   ├── ws_manager.py       # 统一WS管理(4种session+心跳+统计)\
│   └── ws_handlers.py      # 各类型消息处理器\
├── utils/error_codes.py    # 错误码枚举\
├── utils/pdf_exporter.py   # ReportLab PDF生成\
└── migrations/             # Alembic迁移脚本')

doc.add_heading('1.3.2 WebSocketManager — 4种Session统一管理', level=3)
add_code(doc, '# websocket/ws_manager.py\
class WebSocketManager:\
    def __init__(self):\
        self.sessions = {}  # {sid: {ws, type, user_id, connected_at}}\
    \
    async def connect(self, ws, sid, stype, uid):\
        await ws.accept()\
        self.sessions[sid] = {"ws":ws, "type":stype, "user_id":uid}\
    \
    async def send_result(self, sid, data):\
        """向指定session发送JSON结果"""\
    \
    async def disconnect(self, sid): ...\
    \
    def get_stats(self) -> dict:\
        """{train:5, fms:2, learn:3, prescription:1}"""')

doc.add_heading('1.3.3 33个REST端点汇总', level=3)
add_table(doc, ['模块', '方法', '路径', '认证', '说明'], [
    ['Auth', 'POST', '/api/auth/register', '无', '注册(username,password,role,gender)'],
    ['Auth', 'POST', '/api/auth/login', '无', '登录→JWT token(24h)'],
    ['Auth', 'POST', '/api/auth/logout', 'Bearer', '登出→Redis黑名单'],
    ['Auth', 'GET', '/api/auth/me', 'Bearer', '当前用户信息'],
    ['Train', 'POST', '/api/train/start', 'Bearer', '启动训练→session_id'],
    ['Train', 'WS', '/api/train/ws/{sid}', 'token', '实时帧流(send frame/recv result)'],
    ['Train', 'GET', '/api/train/records', 'Bearer', '训练记录列表(分页)'],
    ['Train', 'GET', '/api/train/records/{id}', 'Bearer', '训练详情+角度图表'],
    ['FMS', 'POST', '/api/fms/start', 'Bearer', '启动FMS筛查(5动作可选)'],
    ['FMS', 'WS', '/api/fms/ws/{sid}', 'token', 'FMS逐动作帧流'],
    ['FMS', 'GET', '/api/fms/records', 'Bearer', 'FMS记录列表'],
    ['FMS', 'GET', '/api/fms/records/{id}', 'Bearer', 'FMS详情+雷达图+锁定建议'],
    ['FMS', 'GET', '/api/fms/records/{id}/export', 'Bearer', '导出FMS报告PDF'],
    ['Prescription', 'POST', '/api/prescriptions/generate', 'Bearer', '基于FMS生成处方'],
    ['Prescription', 'GET', '/api/prescriptions/active', 'Bearer', '当前激活处方'],
    ['Prescription', 'PUT', '/api/prescriptions/{id}/activate', 'Bearer', '切换激活处方'],
    ['Prescription', 'GET', '/api/prescriptions/{id}/reason', 'Bearer', '处方推荐理由'],
    ['Prescription', 'POST', '/api/prescriptions/{id}/follow', 'Bearer', '开始跟练'],
    ['Prescription', 'WS', '/api/prescriptions/ws/{sid}', 'token', '跟练帧流(含phase切换)'],
    ['Prescription', 'GET', '/api/prescriptions/{id}/progress', 'Bearer', '解锁进度'],
    ['Prescription', 'POST', '/api/prescriptions/{id}/unlock-request', 'Bearer', '提前解锁申请'],
    ['Prescription', 'PUT', '/api/prescriptions/{id}/adjust', 'Bearer(coach)', '教练调整处方'],
    ['Learn', 'POST', '/api/learn/start', 'Bearer', '启动标准学习'],
    ['Learn', 'WS', '/api/learn/ws/{sid}', 'token', '逐帧对比(双骨架+差异)'],
    ['Checkin', 'POST', '/api/checkin', 'Bearer', '每日打卡'],
    ['Checkin', 'GET', '/api/checkin/status', 'Bearer', '打卡状态(streak)'],
    ['Checkin', 'GET', '/api/checkin/calendar', 'Bearer', '打卡月历'],
    ['Checkin', 'GET', '/api/checkin/badges', 'Bearer', '已获徽章列表'],
    ['Actions', 'GET', '/api/actions/library', 'Bearer', '动作库(分页+分类)'],
    ['Actions', 'POST', '/api/actions/library', 'Bearer(coach)', '新增动作'],
    ['Actions', 'PUT', '/api/actions/library/{id}', 'Bearer(coach)', '编辑动作'],
    ['Actions', 'GET', '/api/actions/tags', 'Bearer', '标签字典'],
    ['Actions', 'POST', '/api/actions/mapping', 'Bearer(coach)', '标签→动作映射'],
    ['Profile', 'GET', '/api/profile', 'Bearer', '个人中心'],
    ['Profile', 'PUT', '/api/profile', 'Bearer', '更新个人信息'],
    ['Profile', 'PUT', '/api/profile/cycle', 'Bearer', '设置生理周期'],
    ['History', 'GET', '/api/history', 'Bearer', '训练历史(含趋势)'],
    ['History', 'GET', '/api/history/{id}', 'Bearer', '训练详情'],
    ['Admin', 'POST', '/api/admin/classes', 'Bearer(coach)', '创建班级'],
    ['Admin', 'GET', '/api/admin/classes/{id}/stats', 'Bearer(coach)', '班级统计'],
    ['Admin', 'POST', '/api/admin/classes/{id}/import', 'Bearer(coach)', '批量导入学员(Excel)'],
    ['Admin', 'GET', '/api/admin/logs', 'Bearer(admin)', '系统日志'],
    ['Admin', 'GET', '/api/admin/dashboard', 'Bearer(admin)', '管理仪表盘'],
])

doc.add_page_break()

# --- Person D (前端应用层) ---
doc.add_heading('1.4 Person D — 前端应用层 (18页面, 6新组件)', level=2)
doc.add_paragraph('职责：React 18 SPA、Canvas骨骼渲染、ECharts图表、WebSocket实时通信、Web Speech API语音播报、Canvas打卡卡片生成。')

doc.add_heading('1.4.1 页面清单与技术方案', level=3)
add_table(doc, ['页面', '路由', '技术方案', '优先级'], [
    ['登录/注册', '/login, /register', 'Ant Design Form + JWT存储', '最高'],
    ['首页', '/home', '快捷入口(FMS/训练/打卡)+连续天数横幅', '高'],
    ['FMS筛查', '/fms', 'MediaRecorder→Canvas抽帧→WS骨架叠加→逐动作引导', '最高'],
    ['FMS报告', '/fms/report/:id', 'ECharts雷达图+新旧双图叠加+锁定建议+PDF导出', '最高'],
    ['训练', '/train', 'video+Canvas骨骼+ECharts实时角度+TTS语音(基础/进阶)', '最高'],
    ['标准学习', '/learn/:action_id', '双骨架叠加+ECharts差异柱状图+逐帧回放', '最高'],
    ['处方管理', '/prescription', '4阶段卡片展示+激活/切换+推荐理由', '高'],
    ['解锁进度', '/prescription/unlock', 'Ant Design Progress+解锁条件+提前解锁按钮', '高'],
    ['处方跟练', '/follow/:id', '同训练页+阶段切换(热身→强化→主训练→冷身)', '高'],
    ['每日打卡', '/checkin', 'Canvas渲染卡片(渐变+天数+动作+二维码)+徽章弹窗', '高'],
    ['历史记录', '/history', 'ECharts趋势折线图(7/30/90天)', '中'],
    ['训练详情', '/history/:id', '角度曲线+反馈汇总+PDF/分享按钮', '中'],
    ['个人统计', '/stats', 'Dashboard面板(总次数/平均分/周期进度)', '中'],
    ['个人中心', '/profile', '信息编辑+生理周期设置+密码修改', '中'],
    ['学员管理', '/admin/students', 'Ant Design Table+Excel批量导入Modal', '高'],
    ['班级统计', '/admin/class-stats', 'ECharts雷达图+风险分布表+对称异常名单', '高'],
    ['动作库', '/admin/library', 'Ant Design Table(CRUD)+标准关键点编辑', '中'],
    ['系统设置', '/admin/settings', '模型切换(YOLO/MediaPipe)+FPS滑块+日志列表', '低'],
])

doc.add_heading('1.4.2 状态管理方案', level=3)
add_table(doc, ['Store', '方案', '数据', '消费者'], [
    ['authStore', 'Context + localStorage', '{user, token, fms_completed, role}', '全局(AuthGuard+Layout)'],
    ['trainStore', 'Zustand', '{session_id, stage, rep_count, score, angles, feedback}', 'TrainPage, FollowPage'],
    ['fmsStore', 'Zustand', '{session_id, current_test, results, progress}', 'FMSPage, FMSReportPage'],
    ['learnStore', 'Zustand', '{session_id, differences, score, standard_angles}', 'LearnPage'],
    ['checkinStore', 'Zustand', '{streak, badges, today_checked, calendar}', 'CheckinPage, HomePage'],
])

doc.add_heading('1.4.3 关键Hook与工具函数', level=3)
add_code(doc, '// hooks/useWebSocket.ts\
// 封装WS连接/自动重连(指数退避,最多5次)/心跳/消息分发\
// hook签名: { send, onMessage, close } = useWebSocket(url)\
\
// utils/voice.ts\
// speakFeedback(text, severity):\
//   - Web Speech API, lang=zh-CN, rate=0.9\
//   - error→pitch=0.8(低沉), warning→pitch=1.0\
//   - 基础模式仅播报severity==="error"\
//   - 3秒冷却机制避免重复播报\
\
// utils/checkinCard.ts\
// renderCheckinCard(ctx, data):\
//   - 750x1334竖版Canvas, 运动蓝→活力橙渐变\
//   - 日期+昵称+连续天数(120px大字)+动作列表+鼓励语+二维码\
//   - 返回 canvas.toDataURL("image/png")')

doc.add_page_break()
print('Person C+D done')


# ═══════════════════════════════════
# 第二章：核心时序图
# ═══════════════════════════════════
doc.add_heading('二、核心时序图', level=1)
add_note(doc, '以下时序图展示系统4个核心流程的完整交互路径，覆盖前端→后端→业务引擎→AI推理→返回的全链路。')

doc.add_heading('2.1 FMS筛查全流程', level=2)
add_code(doc, '用户 → 前端(FMSPage) → 后端(WS) → FMSEngine → PersonA(YOLO)\
│         │                    │              │              │\
├─开始──→│                    │              │              │\
│         ├─POST /fms/start──→│              │              │\
│         │                    ├─创建session──→│              │\
│         │←─session_id+ws───┤              │              │\
│         ├─WS connect──────→│              │              │\
│         │←─{test_start:"平衡"}──────────│              │\
│(做动作)→│                    │              │              │\
│         ├─send frame──────→├─分析────────→│─infer───────→│\
│         │                    │←──角度数据──│←──keypoints──│\
│         │                    ├─score()────→│              │\
│         │←─{test_result}───│←──{score}───│              │\
│         │  (重复3次 + 4动作)  │              │              │\
│         │←─{fms_complete}──│─aggregate()→│              │\
│         ├─GET 雷达图──────→│              │              │\
│         │←─{radar,tags,locks}────────────│              │')

doc.add_heading('2.2 实时跟练帧流', level=2)
add_code(doc, '摄像头(30fps) → TrainPage → WS后端 → FSM(B) → PoseAnalyzer(A)\
│                │              │           │            │\
├─frame────────→│              │           │            │\
│                ├─send{frame}→│           │            │\
│                │              ├─infer───────────────→│(YOLO推理)\
│                │              │←──keypoints──────────│\
│                │              ├─analyze──→│            │\
│                │              │←──angles──│            │\
│                │              ├─FSM.update→│           │\
│                │              │←──{stage,score,feedback}──│\
│                │←─{result}───│           │            │\
│                │[渲染:骨骼+角度折线图]        │            │\
│                │[TTS:偏差>阈值→播报(feedback)]│            │\
│ (循环至rep_count>=target)   │              │           │\
│                │←─{finished,total_score}───│           │')

doc.add_heading('2.3 标准学习对比流', level=2)
add_code(doc, 'LearnPage → WS后端 → StandardLearner(B) → PoseAnalyzer(A)\
│              │              │                    │\
├─POST/start─→│              │                    │\
│              ├─加载标准数据→│                    │\
│←─ws_url─────│              │                    │\
├─send frame─→├─角度────────→│─infer────────────→│\
│              │←──angles────│←──keypoints───────│\
│              ├─compare()──→│                    │\
│              │←──{diffs,score,feedback}────────│\
│←─{learn_result}────────────│                    │\
│[双骨架叠加+差异柱状图+反馈文本]                  │')

doc.add_heading('2.4 处方生成→解锁→复测升级', level=2)
add_code(doc, 'FMS完成 → PrescriptionEngine.generate(fms_result)\
  ├─ 提取problem_tags → tag_action_mapping → 干预动作(难度升序)\
  ├─ 检查lock_suggestions → 排除锁定动作\
  ├─ 4阶段组装(warmup/strengthen/main/cooldown)\
  └─ 输出 prescription_json → 入库 → 前端展示\
\
用户训练 → 打卡 → CheckinEngine.checkin() → streak更新 → badge判定\
\
复测FMS → FMSEngine.compare_reports(old, new)\
  ├─ 维度score变化 → UnlockManager.check_unlock()\
  │   └─ 提升>阈值 → 解锁对应动作 → 发送通知\
  └─ PrescriptionEngine.upgrade_on_retest()\
      └─ 新动作加入主训练 → 新版处方替换旧版')

doc.add_page_break()

# ═══════════════════════════════════
# 第三章：数据库详细设计
# ═══════════════════════════════════
doc.add_heading('三、数据库详细设计', level=1)
doc.add_paragraph('数据库：MySQL 8.0 InnoDB，字符集 utf8mb4。共14张表，分为6大域：用户认证、FMS数据、处方数据、训练数据、社交激励、管理数据。')

doc.add_heading('3.1 ER关系概述', level=2)
add_code(doc, 'users(1) ──< fms_records(1) ──< fms_scores(5维度)\
users(1) ──< prescriptions(N)\
users(1) ──< train_records(N)\
users(1) ──< check_in_cards(N) ──< badges(N)\
users(1) ──< fms_comparisons(N)  (新旧FMS对比)\
users(N) >──< class_groups(N)    (班级关联)\
action_library ──< action_mapping >── tags')

doc.add_heading('3.2 核心表DDL (14张)', level=2)

doc.add_heading('3.2.1 users 用户表', level=3)
add_code(doc, 'CREATE TABLE users (\
  id BIGINT AUTO_INCREMENT PRIMARY KEY,\
  username VARCHAR(64) NOT NULL UNIQUE,\
  password_hash VARCHAR(256) NOT NULL,          -- bcrypt\
  role ENUM("trainee","coach","admin") DEFAULT "trainee",\
  gender ENUM("male","female","other"),\
  nickname VARCHAR(64),\
  fms_completed BOOLEAN DEFAULT FALSE,\
  class_group_id BIGINT,\
  cycle_length INT DEFAULT 28,\
  last_period_date DATE,\
  streak_current INT DEFAULT 0,\
  streak_highest INT DEFAULT 0,\
  created_at DATETIME DEFAULT NOW(),\
  updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),\
  INDEX idx_role(role), INDEX idx_class_group(class_group_id)\
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')

doc.add_heading('3.2.2 fms_records / fms_scores', level=3)
add_code(doc, 'CREATE TABLE fms_records (\
  id BIGINT AUTO_INCREMENT PRIMARY KEY,\
  user_id BIGINT NOT NULL REFERENCES users(id),\
  status ENUM("in_progress","completed") DEFAULT "in_progress",\
  problem_tags JSON,          -- ["核心不稳","肩关节紧张"]\
  lock_suggestions JSON,      -- {core:{locked_actions:[3,7,12]}}\
  radar_data JSON,            -- {labels:[],values:[],risks:[]}\
  created_at DATETIME DEFAULT NOW(),\
  INDEX idx_user_created(user_id, created_at)\
);\
\
CREATE TABLE fms_scores (\
  id BIGINT AUTO_INCREMENT PRIMARY KEY,\
  fms_record_id BIGINT NOT NULL REFERENCES fms_records(id) ON DELETE CASCADE,\
  dimension VARCHAR(32) NOT NULL,   -- balance/flexibility/shoulder/core/symmetry\
  score DECIMAL(5,2) NOT NULL,      -- 0.00~100.00\
  details JSON, risk_level ENUM("red","yellow","green"),\
  UNIQUE KEY uk_record_dim(fms_record_id, dimension)\
);')

doc.add_heading('3.2.3 prescriptions / train_records', level=3)
add_code(doc, 'CREATE TABLE prescriptions (\
  id BIGINT AUTO_INCREMENT PRIMARY KEY,\
  user_id BIGINT NOT NULL REFERENCES users(id),\
  fms_record_id BIGINT REFERENCES fms_records(id),\
  status ENUM("active","completed","upgraded") DEFAULT "active",\
  phases JSON NOT NULL,     -- {warmup:[],strengthen:[],main:[],cooldown:[]}\
  lock_info JSON, intensity_level TINYINT DEFAULT 1,\
  created_at DATETIME DEFAULT NOW()\
);\
\
CREATE TABLE train_records (\
  id BIGINT AUTO_INCREMENT PRIMARY KEY,\
  user_id BIGINT NOT NULL REFERENCES users(id),\
  prescription_id BIGINT, action_id BIGINT NOT NULL,\
  action_name VARCHAR(64), mode ENUM("basic","advanced") DEFAULT "basic",\
  total_score DECIMAL(5,2), reps INT, feedback TEXT,\
  key_angles JSON, angle_chart JSON, duration_seconds INT,\
  created_at DATETIME DEFAULT NOW(),\
  INDEX idx_user_created(user_id, created_at)\
);')

doc.add_heading('3.2.4 check_in_cards / badges / class_groups / system_logs', level=3)
add_code(doc, 'CREATE TABLE check_in_cards (\
  id BIGINT AUTO_INCREMENT PRIMARY KEY,\
  user_id BIGINT NOT NULL REFERENCES users(id),\
  checkin_date DATE NOT NULL, streak INT DEFAULT 1,\
  actions_completed JSON, encouragement VARCHAR(128),\
  card_image_url VARCHAR(512),\
  created_at DATETIME DEFAULT NOW(),\
  UNIQUE KEY uk_user_date(user_id, checkin_date)\
);\
\
CREATE TABLE badges (\
  id BIGINT AUTO_INCREMENT PRIMARY KEY,\
  user_id BIGINT NOT NULL REFERENCES users(id),\
  badge_type VARCHAR(32) NOT NULL,  -- week_streak|month_streak\
  earned_at DATETIME DEFAULT NOW(),\
  UNIQUE KEY uk_user_badge(user_id, badge_type)\
);\
\
CREATE TABLE fms_comparisons (\
  id BIGINT AUTO_INCREMENT PRIMARY KEY,\
  user_id BIGINT NOT NULL REFERENCES users(id),\
  old_record_id BIGINT, new_record_id BIGINT,\
  score_changes JSON,   -- {"balance":+5,"core":+10}\
  created_at DATETIME DEFAULT NOW()\
);\
\
CREATE TABLE class_groups (\
  id BIGINT AUTO_INCREMENT PRIMARY KEY,\
  name VARCHAR(64) NOT NULL, coach_id BIGINT,\
  student_ids JSON, created_at DATETIME DEFAULT NOW()\
);\
\
CREATE TABLE action_library (\
  id BIGINT AUTO_INCREMENT PRIMARY KEY,\
  name VARCHAR(64), category VARCHAR(32),\
  difficulty TINYINT DEFAULT 1, risk_tags JSON,\
  lock_thresholds JSON, standard_keypoints JSON,\
  demo_video_url VARCHAR(512), created_at DATETIME DEFAULT NOW()\
);\
\
CREATE TABLE action_mapping (\
  id BIGINT AUTO_INCREMENT PRIMARY KEY,\
  tag_id BIGINT NOT NULL, action_id BIGINT NOT NULL, priority INT DEFAULT 1\
);\
\
CREATE TABLE system_logs (\
  id BIGINT AUTO_INCREMENT PRIMARY KEY,\
  level VARCHAR(16) DEFAULT "info", module VARCHAR(64), message TEXT,\
  created_at DATETIME DEFAULT NOW(),\
  INDEX idx_level_time(level, created_at)\
);')

doc.add_heading('3.3 索引策略汇总', level=2)
add_table(doc, ['表', '索引', '类型', '用途'], [
    ['users', 'username', 'UNIQUE', '登录查询'],
    ['users', 'class_group_id', 'BTREE', '班级关联查询'],
    ['fms_records', '(user_id, created_at)', 'COMPOSITE', '按用户+时间查询'],
    ['fms_scores', '(fms_record_id, dimension)', 'UNIQUE', '唯一评分约束'],
    ['train_records', '(user_id, created_at)', 'COMPOSITE', '训练历史查询'],
    ['check_in_cards', '(user_id, checkin_date)', 'UNIQUE', '每日唯一打卡'],
    ['system_logs', '(level, created_at)', 'COMPOSITE', '日志筛选查询'],
])

doc.add_page_break()

# ═══════════════════════════════════
# 第四章：状态机定义
# ═══════════════════════════════════
doc.add_heading('四、状态机定义', level=1)

doc.add_heading('4.1 跟练动作FSM (以深蹲为例)', level=2)
add_table(doc, ['状态', '转移条件', '输出'], [
    ['idle', '首次检测到关键点置信度>0.7', '→ ready, "准备就绪"'],
    ['ready', '髋角<150°(两侧)', '→ down, "匀速下蹲"'],
    ['down', '膝角<90°(任一侧)', '→ bottom, "到达底部"'],
    ['bottom', '髋角>120°(两侧)', '→ up, "向上站起"'],
    ['up', '髋角>160°(两侧)', '→ complete, rep_count++'],
    ['complete', '自动转换(0.5s后) 或 rep_count>=target', '→ ready 或 finished'],
    ['finished', '—', '训练结束, 输出total_score'],
])

doc.add_heading('4.2 处方生命周期', level=2)
add_code(doc, 'active → in_progress → phase_complete → all_complete → retest_due → upgraded\
                                      \
                               (复测FMS通过, check_unlock → 解锁动作, upgrade → 新版处方)')

doc.add_heading('4.3 打卡状态机', level=2)
add_code(doc, '今日未打卡 ──POST /checkin──→ 今日已打卡\
                                        │\
                           ┌────────────┴────────────┐\
                           ↓                         ↓\
                      昨日已打卡                  昨日未打卡\
                      streak = prev+1             streak = 1\
                           │\
                           ├── streak==7  → badge: week_streak\
                           └── streak==30 → badge: month_streak')

doc.add_page_break()
print('Ch 2-4 done')


# ═══════════════════════════════════
# 第五章：前端组件树与状态管理
# ═══════════════════════════════════
doc.add_heading('五、前端组件树与状态管理', level=1)

doc.add_heading('5.1 组件层级结构', level=2)
add_code(doc, '<App>\
├── <AuthGuard>                         # 路由守卫(JWT检查)\
│   ├── <Layout>                        # 侧边栏+顶栏+用户信息\
│   │   ├── <Routes>\
│   │   │   ├── /login        → <LoginPage>\
│   │   │   ├── /register     → <RegisterPage>\
│   │   │   ├── /home         → <HomePage>\
│   │   │   │   ├── <QuickActions>       (FMS/训练/打卡快捷入口)\
│   │   │   │   ├── <StreakBanner>        (连续打卡天数)\
│   │   │   │   └── <RecentTrainings>     (最近训练记录)\
│   │   │   ├── /fms          → <FMSPage>\
│   │   │   │   ├── <CameraView>          (摄像头+Canvas骨架)\
│   │   │   │   ├── <TestGuide>           (逐动作引导文案)\
│   │   │   │   └── <ProgressBar>         (FMS进度条)\
│   │   │   ├── /fms/report/:id → <FMSReportPage>\
│   │   │   │   ├── <RadarChart>          (ECharts雷达图)\
│   │   │   │   ├── <ComparisonRadar>     (新旧对比叠加)\
│   │   │   │   └── <LockSuggestions>     (锁定建议+原因)\
│   │   │   ├── /train        → <TrainPage>\
│   │   │   │   ├── <CameraView> + <SkeletonCanvas>\
│   │   │   │   ├── <AngleChart>          (ECharts实时角度)\
│   │   │   │   ├── <VoiceFeedback>       (TTS语音播报)\
│   │   │   │   └── <StageIndicator>      (当前阶段显示)\
│   │   │   ├── /learn/:id    → <LearnPage>\
│   │   │   │   ├── <DualSkeleton>        (双骨架叠加)\
│   │   │   │   └── <DiffBarChart>        (ECharts差异柱状图)\
│   │   │   ├── /prescription → <PrescriptionPage>\
│   │   │   │   ├── <PhaseCard>           (各阶段动作卡片)\
│   │   │   │   └── <UnlockProgress>      (解锁进度条)\
│   │   │   ├── /checkin      → <CheckinPage>\
│   │   │   │   ├── <CheckinButton>, <StreakDisplay>\
│   │   │   │   ├── <CheckinCard>         (Canvas渲染+分享)\
│   │   │   │   └── <BadgeModal>          (徽章弹窗)\
│   │   │   ├── /history      → <HistoryPage>  (趋势折线图)\
│   │   │   ├── /admin/students  → <AdminStudentsPage>\
│   │   │   │   └── <BatchImportModal>    (Excel导入+预览)\
│   │   │   ├── /admin/class-stats → <ClassStatsPage>\
│   │   │   │   ├── <ClassRadarChart>, <RiskTable>\
│   │   │   │   └── <SymmetryWarnings>\
│   │   │   └── /admin/settings → <SettingsPage>\
│   │   │       ├── <ModelSwitcher>       (YOLO/MediaPipe切换)\
│   │   │       └── <LogList>             (系统日志列表)')

doc.add_heading('5.2 路由配置 (18个路由)', level=2)
add_table(doc, ['路径', '组件', '认证', '角色'], [
    ['/', 'HomePage', '需要登录', '全部'],
    ['/login', 'LoginPage', '公开', '—'],
    ['/register', 'RegisterPage', '公开', '—'],
    ['/fms', 'FMSPage', '需要登录', 'trainee'],
    ['/fms/report/:id', 'FMSReportPage', '需要登录', 'trainee'],
    ['/train', 'TrainPage', '需要登录', 'trainee'],
    ['/learn/:action_id', 'LearnPage', '需要登录', 'trainee'],
    ['/prescription', 'PrescriptionPage', '需要登录', 'trainee'],
    ['/prescription/unlock', 'UnlockPage', '需要登录', 'trainee'],
    ['/follow/:id', 'FollowPage', '需要登录', 'trainee'],
    ['/checkin', 'CheckinPage', '需要登录', 'trainee'],
    ['/history', 'HistoryPage', '需要登录', 'trainee'],
    ['/history/:id', 'HistoryDetailPage', '需要登录', 'trainee'],
    ['/stats', 'StatsPage', '需要登录', '全部'],
    ['/profile', 'ProfilePage', '需要登录', '全部'],
    ['/admin/students', 'AdminStudentsPage', '需要登录', 'coach/admin'],
    ['/admin/class-stats', 'ClassStatsPage', '需要登录', 'coach/admin'],
    ['/admin/library', 'AdminLibraryPage', '需要登录', 'coach/admin'],
    ['/admin/settings', 'SettingsPage', '需要登录', 'admin'],
])

doc.add_page_break()

# ═══════════════════════════════════
# 第六章：错误码完整表
# ═══════════════════════════════════
doc.add_heading('六、错误码完整表', level=1)

add_table(doc, ['错误码', '分类', 'HTTP', '说明', '前端处理'], [
    ['0', '成功', '200', '操作成功', '直接展示data'],
    ['1001', '参数', '400', '必填参数缺失', '表单提示"请填写完整"'],
    ['1002', '参数', '400', '参数类型错误', '表单提示格式错误'],
    ['1003', '参数', '400', '参数值超出范围', '提示"请输入有效值"'],
    ['1004', '参数', '400', '图片格式不支持', '提示"支持JPG/PNG"'],
    ['1005', '参数', '400', '视频帧数据为空', '提示"未检测到画面"'],
    ['2001', '认证', '401', '未登录/Token缺失', '跳转登录页'],
    ['2002', '认证', '401', 'Token已过期', '刷新或跳转登录'],
    ['2003', '认证', '403', '权限不足(角色不符)', '提示"无权访问"'],
    ['2004', '认证', '401', 'Token签名无效', '跳转登录页'],
    ['3001', '资源', '404', '用户不存在', '提示"用户不存在"'],
    ['3002', '资源', '404', 'FMS记录不存在', '提示"记录不存在"'],
    ['3003', '资源', '404', '处方不存在', '提示"请先进行FMS筛查"'],
    ['3004', '资源', '404', '动作不存在', '提示"动作已下架"'],
    ['3006', '资源', '404', '班级不存在', '提示"班级不存在"'],
    ['4001', '业务', '409', '今日已打卡', '按钮变灰"今日已打卡"'],
    ['4002', '业务', '403', '动作被锁定', '显示锁定原因+进度'],
    ['4003', '业务', '400', '超出复测周期', '提示"请先复测FMS"'],
    ['4004', '业务', '409', '解锁申请已提交', '显示申请状态'],
    ['4005', '业务', '400', 'FMS未完成', '提示"请先完成5项FMS"'],
    ['4006', '业务', '400', '处方已过期', '提示"请查看最新处方"'],
    ['5001', '服务端', '500', '模型推理失败', '提示"系统繁忙，请重试"'],
    ['5002', '服务端', '500', '数据库异常', '提示"系统异常"'],
    ['5003', '服务端', '500', '文件处理失败', '提示"文件处理失败"'],
    ['5004', '服务端', '500', 'PDF生成失败', '提示"报告生成失败"'],
    ['5005', '服务端', '500', 'WS连接异常', '自动重连+提示"已断开"'],
])

doc.add_page_break()

# ═══════════════════════════════════
# 第七章：测试策略
# ═══════════════════════════════════
doc.add_heading('七、测试策略', level=1)

doc.add_heading('7.1 分层测试方案', level=2)
add_table(doc, ['层级', '负责人', '工具', '覆盖目标', '关键用例数'], [
    ['A-单元', 'Person A', 'pytest', 'AngleUtils 100%, PoseAnalyzer精度验证', 'calc_angle:20组 / 角度精度:100组标注'],
    ['B-单元', 'Person B', 'pytest', '每识别器>=5帧, FMS评分>=10组对比', '9识别器:50帧 / FMS:50组评分'],
    ['C-集成', 'Person C', 'pytest+httpx', '33端点各>=3case, 4种WS session', 'REST:99case / WS:12scenario'],
    ['D-组件', 'Person D', 'Jest+RTL', '6新组件渲染+交互', 'VoiceFeedback/CheckinCard等:18case'],
    ['E2E', '全体', 'Playwright', '核心用户旅程', '注册→FMS→处方→跟练→打卡:1条链'],
])

doc.add_heading('7.2 角度精度验证专项', level=2)
doc.add_paragraph('人工标注100组关键点（深蹲/平板支撑/过头推举，正/侧/背面），由专业教练标注真值，与PoseAnalyzer对比。指标：MAE<3°, RMSE<4°, MaxAE<8°。')

doc.add_heading('7.3 性能测试标准', level=2)
add_table(doc, ['指标', '目标', '测试方法'], [
    ['YOLO推理帧率', 'GPU >=25fps, CPU >=12fps', '1000帧连续推理取P95'],
    ['API响应时间', 'REST P95 <200ms', 'JMeter 100并发压测'],
    ['WS帧处理延迟', '端到端 <100ms', '带timestamp帧往返计算'],
    ['数据库查询', '单表 <50ms', 'EXPLAIN+索引确认'],
    ['前端首屏', '<3s (Lighthouse)', 'Chrome DevTools Audit'],
])

doc.add_page_break()

# ═══════════════════════════════════
# 第八章：部署配置
# ═══════════════════════════════════
doc.add_heading('八、部署配置', level=1)

doc.add_heading('8.1 Docker Compose 编排', level=2)
add_code(doc, '# docker-compose.yml\
version: "3.8"\
services:\
  mysql:       image: mysql:8.0,    ports: [3306]\
  redis:       image: redis:7-alpine, ports: [6379]\
  minio:       image: minio/minio,   ports: [9000,9001]\
  fastapi: \
    build: ./backend\
    environment:\
      MODEL_PATH: /app/models/yolov8n-pose.pt\
      DEVICE: cuda\
      JWT_SECRET: your-secret-key\
      DB_URL: mysql+pymysql://user:pass@mysql:3306/pose_assessment\
      REDIS_URL: redis://redis:6379/0\
      MINIO_URL: http://minio:9000\
    ports: [8000]\
    deploy:\
      resources:\
        reservations:\
          devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]\
  nginx:       image: nginx:alpine,  ports: [80,443]')

doc.add_heading('8.2 环境变量清单', level=2)
add_table(doc, ['变量', '说明', '默认值', '必填'], [
    ['MODEL_PATH', 'YOLO模型权重路径', 'yolov8n-pose.pt', '是'],
    ['DEVICE', '推理设备(cpu/cuda/auto)', 'auto', '是'],
    ['JWT_SECRET', 'JWT签名密钥', '(必须设置)', '是'],
    ['JWT_EXPIRE_HOURS', 'JWT有效期(小时)', '24', '否'],
    ['DB_URL', 'MySQL连接字符串', '—', '是'],
    ['REDIS_URL', 'Redis连接字符串', '—', '是'],
    ['MINIO_URL/USER/PASSWORD', 'MinIO相关配置', '—', '是'],
    ['LOG_LEVEL', '日志级别', 'INFO', '否'],
    ['CORS_ORIGINS', '允许跨域来源', 'http://localhost:5173', '否'],
    ['RATE_LIMIT', '每分钟请求限制', '60', '否'],
])

doc.add_heading('8.3 GPU资源需求', level=2)
add_table(doc, ['模型', '显存', '单帧推理', '适用GPU'], [
    ['YOLOv8n-pose (nano)', '~1.5GB', '~8ms', 'T4/GTX 1660+'],
    ['YOLOv8s-pose (small)', '~2.5GB', '~12ms', 'RTX 3060+'],
    ['MediaPipe Pose', '~0.5GB', '~5ms', '任意(含CPU)'],
])

footer(doc)

# =================== SAVE ===================
output_path = 'D:/workbench/program3/plan/详细设计文档_v1.0.docx'
doc.save(output_path)
print('SUCCESS: Detailed Design saved to ' + output_path)
