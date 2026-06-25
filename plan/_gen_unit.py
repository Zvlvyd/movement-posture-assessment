# -*- coding: utf-8 -*-
"""Generate detailed design document for unit module design"""
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
import datetime

doc = Document()

for section in doc.sections:
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(3.17)
    section.right_margin = Cm(3.17)

style = doc.styles['Normal']
font = style.font
font.name = '宋体'
style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
font.size = Pt(12)

def h1(text):
    h = doc.add_heading(text, level=1)
    for r in h.runs: r.font.name = '黑体'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    return h

def h2(text):
    h = doc.add_heading(text, level=2)
    for r in h.runs: r.font.name = '黑体'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    return h

def h3(text):
    h = doc.add_heading(text, level=3)
    for r in h.runs: r.font.name = '黑体'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    return h

def p(text, bold=False, indent=True):
    para = doc.add_paragraph()
    if indent: para.paragraph_format.first_line_indent = Cm(0.74)
    run = para.add_run(text)
    run.font.name = '宋体'; run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    run.font.size = Pt(12); run.bold = bold
    return para

def table(headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = ''
        r = c.paragraphs[0].add_run(h)
        r.bold = True; r.font.name = '宋体'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        r.font.size = Pt(10); c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in rows:
        tr = t.add_row()
        for i, v in enumerate(row):
            c = tr.cells[i]; c.text = ''
            r = c.paragraphs[0].add_run(str(v))
            r.font.name = '宋体'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
            r.font.size = Pt(10)
    return t

def code_block(text):
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Cm(1)
    run = para.add_run(text)
    run.font.name = 'Consolas'; run.font.size = Pt(9)
    return para

print("Functions defined OK")

# ====== Cover ======
for _ in range(6): doc.add_paragraph()
tp = doc.add_paragraph(); tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = tp.add_run('运动姿态评估与纠错系统'); r.font.size = Pt(26); r.bold = True
r.font.name = '黑体'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
sp = doc.add_paragraph(); sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sp.add_run('详细分析与设计'); r.font.size = Pt(22)
r.font.name = '黑体'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
for _ in range(3): doc.add_paragraph()
vp = doc.add_paragraph(); vp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = vp.add_run('V2.0'); r.font.size = Pt(16)
dp = doc.add_paragraph(); dp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = dp.add_run(datetime.date.today().strftime('%Y年%m月%d日')); r.font.size = Pt(14)
doc.add_page_break()

# ====== TOC ======
h1('目   录')
toc = [('第一部分','引言'),('','一、编写目的'),('','二、项目背景'),('','三、参考资料'),
('第二部分','项目概述'),('第三部分','总体设计'),('','一、技术架构设计'),('','二、技术选型介绍'),('','三、核心控制流程'),
('第四部分','界面和业务单设计'),('','一、Web端桌面布局设计'),('','二、业务界面风格展示'),
('第五部分','单元模块设计'),('','一、数据采集与标注'),('','二、人工智能技术方案'),('','三、单元UI设计'),('','四、数据访问层设计'),('','五、业务逻辑层设计'),
('第六部分','数据库设计'),('第七部分','补充设计和说明')]
for sec, item in toc:
    para = doc.add_paragraph()
    run = para.add_run(f'{sec} {item}' if sec else f'    {item}')
    run.bold = bool(sec)
    run.font.name = '宋体'; run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体'); run.font.size = Pt(12)
doc.add_page_break()

# ====== Part 1 ======
h1('第一部分 引言')
h2('一、编写目的')
p('编写本设计的目的是为了准确阐述运动姿态评估与纠错系统的具体实现思路和方法，即系统的详细架构和实现逻辑，主要包括程序系统的结构以及各层次中每个程序的设计考虑。预期读者为项目全体成员，包括运行维护和测试人员。')
h2('二、项目背景')
p('系统名称：运动姿态评估与纠错系统'); p('任务提出者：重庆大学实训项目组')
p('开发者：Person A（模型推理层）、Person B（业务引擎层）、Person C（后端API层）、Person D（前端应用层）')
p('本项目通过构建"评估-干预"闭环：FMS功能性运动能力筛查（测）→ AI智能训练处方（算）→ 实时姿态纠错（练）→ 数据反馈与复测（看），实现低成本、广覆盖、实时化的运动姿态评估与智能干预。')
h2('三、参考资料')
for ref in ['《03-运动姿态评估与纠错系统-需求说明书》v1.0','《运动姿态评估与纠错系统-概要设计计划文档》v3.0','《API接口文档》v3.0','《任务书-PersonA-模型推理层》v3.0','《任务书-PersonB-业务引擎层》v3.0','《任务书-PersonC-后端API层》v3.0','《任务书-PersonD-前端应用层》v3.0','COCO Keypoint Detection 17关键点标注规范','YOLOv8-Pose 官方文档（Ultralytics）','MediaPipe Pose 官方文档（Google）','Functional Movement Screen (FMS) 评分标准']:
    p(ref)
doc.add_page_break()

# ====== Part 2 ======
h1('第二部分 项目概述')
p('运动姿态评估与纠错系统是基于深度学习人体姿态检测技术的智能运动评估平台。系统采用YOLO-Pose + MediaPipe双方案架构，支持摄像头实时检测与离线视频分析，实现常见健身动作的自动识别、精准计数、姿态量化评估与智能纠错。')
p('系统核心功能包括：FMS功能性运动能力筛查、AI智能训练处方生成、实时姿态纠错与动作计数、标准动作对比学习、每日打卡与社交激励、教练后台管理与班级统计分析。')
p('系统采用四层架构：模型推理层（Person A）→ 业务引擎层（Person B）→ 后端API层（Person C）→ 前端应用层（Person D），通过WebSocket实现实时帧流通信，支持基础模式与进阶模式双模式训练。')
doc.add_page_break()

print("Part 1-2 done")


# ====== Part 3: Overall Design ======
h1('第三部分 总体设计')

h2('一、技术架构设计')
p('系统采用B/S架构，前后端分离设计。整体分为四层：')
p('1. 模型推理层（Person A）：负责接收原始图像帧，基于YOLOv8-Pose / MediaPipe输出17关键点坐标和7个关节角度，支持卡尔曼滤波平滑与置信度过滤。')
p('2. 业务引擎层（Person B）：包含9个动作识别器（基于有限状态机FSM）、FMS筛查引擎、处方生成引擎、标准学习引擎、打卡引擎、解锁管理器、班级统计引擎、生理周期管理器。')
p('3. 后端API层（Person C）：基于FastAPI框架，提供33个REST端点、4种WebSocket Session、JWT认证、MySQL/Redis数据管理、PDF报告生成。')
p('4. 前端应用层（Person D）：基于React 18 SPA，包含18个页面、Canvas骨骼渲染、ECharts图表、WebSocket实时通信、Web Speech API语音播报。')
p('数据存储：MySQL 8.0（主存储）+ Redis（缓存/会话/Token黑名单）+ MinIO（视频/图片对象存储）。')
p('通信协议：REST API（业务数据交换）+ WebSocket（实时帧流与结果推送）。')

h2('二、技术选型介绍')
p('1. Python / FastAPI：采用Python作为主要开发语言，FastAPI作为后端Web框架，具有高性能异步支持、自动API文档生成、类型安全等特点，适合实时视频帧处理的场景。')
p('2. YOLOv8-Pose：基于Ultralytics YOLOv8框架的人体姿态估计模型，支持COCO 17关键点检测，在GPU环境下可达25+fps实时推理。作为高精度生产方案，适用于配置GPU的教学场景。')
p('3. MediaPipe Pose：Google开源的轻量级姿态估计框架，支持CPU实时推理（5ms/帧），作为低资源环境下的快速验证与移动端适配方案。')
p('4. React 18：前端采用React 18 SPA架构，结合Ant Design组件库、ECharts图表库、Web Speech API语音合成，实现丰富的用户交互体验。')
p('5. MySQL 8.0 + SQLAlchemy ORM：关系型数据库存储用户、FMS记录、训练记录、处方、打卡等结构化数据，通过SQLAlchemy ORM实现对象关系映射。')
p('6. Redis 7：用作JWT Token黑名单、WebSocket会话管理、实时统计缓存。')
p('7. MinIO：开源对象存储服务，用于存储训练视频、打卡卡片图片、PDF报告等非结构化数据。')

h2('三、核心控制流程')
h3('1、核心控制流程图')
p('系统核心业务流程：用户注册登录 → FMS功能性运动能力筛查（5维度雷达图）→ AI智能训练处方生成（4阶段处方结构）→ 处方跟练执行（实时姿态检测与纠错）→ 每日打卡与数据反馈 → 定期FMS复测 → 处方自动升级。')
p('实时训练流程：摄像头采集帧 → WebSocket发送帧到后端 → Person C转发到Person A推理 → Person A返回关键点+角度 → Person B进行动作识别/纠错/计数 → Person C推送结果到前端 → Person D渲染骨骼+角度图表+语音反馈。')

h3('2、核心控制流程说明')
p('（1）FMS筛查流程：用户进入筛查页面 → 系统引导完成5个测试动作（闭眼单腿站立、过头深蹲、肩活动度、平板支撑、弓步蹲）→ 每个动作实时检测关键点并记录数据 → 完成后生成5维度雷达图报告 → 输出问题标签与风险等级。')
p('（2）处方生成流程：基于FMS各维度评分提取问题标签 → 从动作库匹配干预动作（按难度升序）→ 生成3套备选方案（强化型/平衡型/恢复型）→ 组装4阶段处方结构 → 应用锁定策略（低于阈值自动限制高风险动作）。')
p('（3）实时纠错流程：摄像头帧 → 17关键点提取 → 7关节角度计算 → 动作FSM状态识别 → 与标准规则对比 → 角度偏差超过阈值 → 语音+视觉纠错提示 → 危险动作（如膝盖内扣>15°或躯干前倾>30°）立即暂停报警。')
doc.add_page_break()

print("Part 3 done")


# ====== Part 4: UI Design ======
h1('第四部分 界面和业务单设计')
p('系统Web端采用React 18 + Ant Design组件库进行开发，前端包含18个页面，覆盖训练者、教练/教师、系统管理员三种角色的业务需求。')
p('以下为各主要界面的布局设计说明。')

h2('一、Web端桌面布局设计')

h3('1、登录界面')
p('登录界面分为上中下三个部分，最上方是"运动姿态评估与纠错系统"标题与Logo，中间部分是用户输入用户名和密码的表单输入框，并包含登录按钮和注册链接，最下方是可选的第三方登录入口。')

h3('2、注册界面')
p('注册界面与登录界面风格一致，上方为注册标题，中间部分包含用户名、密码、确认密码、手机号、性别选择等表单输入框，并包含注册按钮和登录链接。女性用户可填写月经周期信息（上次开始日期、平均周期天数）。')

h3('3、首页')
p('首页采用卡片式布局，顶部显示连续打卡天数横幅（StreakBanner组件），中部为快捷入口区（QuickActions组件：FMS筛查、开始训练、每日打卡），下方为最近训练记录列表（RecentTrainings组件）。')

h3('4、FMS筛查页面')
p('FMS筛查页面分为左右两栏：左栏为摄像头预览区（CameraView组件+Canvas骨骼叠加），实时显示人体姿态骨架；右栏为测试引导区（TestGuide组件），逐动作显示说明文字、示范视频和进度条（ProgressBar组件）。')

h3('5、FMS报告页面')
p('FMS报告页面顶部显示5维度雷达图（RadarChart组件，ECharts实现），下方为各维度详细评分与风险等级。支持新旧两次筛查雷达图叠加对比（ComparisonRadar组件），底部显示问题标签与锁定建议（LockSuggestions组件），支持PDF导出。')

h3('6、训练页面')
p('训练页面是系统的核心页面，分为三栏布局：左栏为摄像头预览+骨骼叠加显示（SkeletonCanvas组件）；中栏为动作信息显示（动作名称、计数、阶段指示StageIndicator）；右栏为实时角度图表（AngleChart组件，ECharts柱状图实时刷新）。底部为语音反馈状态栏（VoiceFeedback组件，TTS语音播报纠错提示）。')

h3('7、标准学习页面')
p('标准学习页面分为左右两栏：左栏为标准示范视频播放器+用户实时摄像头画面（双骨架叠加DualSkeleton组件，用户骨架为蓝色、标准骨架为绿色）；右栏为差异分析区，显示7关节角度差异柱状图（DiffBarChart组件）和中文纠错反馈文字。')

h3('8、处方管理页面')
p('处方管理页面顶部显示当前激活处方概览卡片，下方分为4个阶段区域（PhaseCard组件：热身→强化激活→主训练→冷身），每个阶段卡片内列出动作列表及完成状态。底部提供方案切换按钮和解锁进度查看入口。')

h3('9、打卡页面')
p('打卡页面中央为大尺寸打卡按钮（CheckinButton），点击后通过Canvas渲染生成打卡卡片（含渐变背景、训练日期、昵称、连续天数、完成动作列表、系统鼓励语），支持保存图片和分享到社交平台。下方显示连续打卡天数和已获徽章列表（BadgeModal）。')

h3('10、历史记录页面')
p('历史记录页面顶部提供筛选条件（动作类型、时间范围、训练模式），主体为训练记录列表（按时间倒序），每条记录显示动作名称、得分、次数、时长。底部提供训练趋势折线图（ECharts，支持7天/30天/90天切换）。点击单条记录可进入训练详情页。')

h3('11、管理员班级统计页面')
p('班级统计页面顶部为班级选择下拉框，主体展示班级5维度平均雷达图（ClassRadarChart组件）、风险分布表（RiskTable组件：红色<40分/黄色40-70分/绿色>70分）、左右对称性异常学员预警列表（SymmetryWarnings）。')

h2('二、业务界面风格展示')
p('系统整体采用简洁现代的UI风格，主色调为蓝色系（#1890FF），辅助色为绿色（#52C41A，表示达标）和红色（#FF4D4F，表示危险/警告）。所有页面遵循Ant Design设计规范，保持视觉一致性。')
p('训练页面支持基础模式（蓝色主题）和进阶模式（紫色主题）的视觉切换。FMS筛查页面采用步骤条（Steps）引导用户完成5项测试。处方页面使用时间轴（Timeline）展示解锁进度。')
doc.add_page_break()

print("Part 4 done")


# ====== Part 5: Unit Module Design ======
h1('第五部分 单元模块设计')

h2('一、数据采集与标注')

h3('1、数据采集设计')
p('本项目人体姿态检测基于COCO 17关键点标注格式，使用两种数据来源：')
p('（A）COCO预训练数据集：采用COCO 2017 Keypoint Detection数据集的17关键点标注格式（鼻、左右眼、左右耳、左右肩、左右肘、左右腕、左右髋、左右膝、左右踝）。YOLOv8-Pose模型使用该数据集预训练权重作为初始化参数，无需从头训练。')
p('（B）自定义动作关键点验证数据集：为了验证PoseAnalyzer角度计算精度，需采集100组自定义标注数据。具体采集要求如下：')

table(
    ['采集要求', '详细参数', '说明'],
    [
        ['采集动作', '深蹲/俯卧撑/平板支撑/弓步蹲/过头推举', '覆盖5类核心动作'],
        ['采集视角', '正面/侧面/背面', '每个动作3个视角'],
        ['采集设备', '1080P摄像头（30fps）', '保证图像清晰度'],
        ['每动作帧数', '关键帧3-5帧（起始/中间/结束）', '覆盖动作全阶段'],
        ['标注人员', '专业健身教练', '保证标注准确性'],
        ['标注工具', 'LabelMe / CVAT', '支持关键点标注'],
        ['标注格式', 'COCO JSON (17 keypoints: x,y,v)', '与模型输出格式一致'],
        ['存储位置', '项目models/knowledge/目录', 'JSON格式存储'],
    ]
)

p('（C）动作规则知识库构建：系统维护一套标准动作规则知识库，包含以下内容：')

table(
    ['知识库文件', '内容', '示例'],
    [
        ['thresholds.json', '各动作关节角度阈值与容差范围', '深蹲: 膝角90°±10°, 髋角60°±15°'],
        ['exercises.json', '动作定义、FSM规则、纠错话术', '20-30个基础动作的规则定义'],
        ['muscles.json', '肌肉-动作映射关系', '深蹲→股四头肌/臀大肌/腘绳肌'],
        ['problems.json', '问题标签定义与干预方案', '核心不稳→平板支撑+死虫式'],
        ['rom_norms.json', '关节活动度正常范围标准', '膝关节屈曲0-140°, 髋关节屈曲0-120°'],
    ]
)

h3('2、数据标注协作要求')
p('在采集和标注关键点数据时，需要注意以下几点：')

table(
    ['注意点', '详细内容'],
    [
        ['标注精度', '关键点标注误差控制在±3像素以内，确保角度计算精度达标（MAE<3°）'],
        ['遮挡处理', '对于被遮挡的关键点，标注v=0（不可见），模型推理时自动处理'],
        ['多人场景', '当前版本仅标注画面中主要人物（最靠近镜头者），预留多人标注字段'],
        ['数据管理', '每组标注数据包含：原始帧图像、COCO格式JSON标注文件、标注人员ID、标注时间戳'],
        ['质量审核', '每批次标注完成后由第二位教练进行交叉验证，标注一致性>95%方可通过'],
        ['版本管理', '标注数据使用Git LFS进行版本管理，标注文件与代码仓库分离存储'],
    ]
)

h3('3、数据集工程设计')
p('本项目的数据集工程设计分为三个层次：')
p('（1）预训练层：直接使用YOLOv8官方在COCO数据集上的预训练权重（yolov8n-pose.pt / yolov8s-pose.pt），无需额外训练。17关键点检测精度已在COCO val2017上验证（mAP 50-95约50%+）。')
p('（2）验证层：自定义100组关键点标注数据，用于验证PoseAnalyzer角度计算精度。对比专业教练标注的真值与模型计算值，确保MAE<3°。存储在models/knowledge/目录。')
p('（3）规则层：动作规则知识库JSON文件（thresholds.json / exercises.json / muscles.json / problems.json / rom_norms.json），由运动科学领域专家定义标准动作的角度阈值、FSM状态转移规则、纠错话术模板。支持JSON格式热更新，无需重启服务。')

doc.add_page_break()

print("Part 5a done")


h2('二、人工智能技术方案')

h3('1、技术路线选择')
p('本系统采用"双引擎"架构，兼顾高精度与轻量化需求：')

table(
    ['方案', 'YOLOv8-Pose', 'MediaPipe Pose'],
    [
        ['适用场景', '高精度教学场景 / GPU环境', '低资源环境 / 移动端 / 快速验证'],
        ['推理设备', 'GPU (NVIDIA CUDA)', 'CPU / GPU / Edge TPU'],
        ['推理速度', '~8ms/帧 (nano) / ~12ms/帧 (small)', '~5ms/帧'],
        ['关键点数', '17 (COCO格式)', '33 (含手部/面部) → 映射为17'],
        ['多人支持', '原生支持多人检测', '支持多人检测'],
        ['置信度', '≥0.5（可配置）', '≥0.5（可配置）'],
        ['模型大小', 'yolov8n-pose.pt: ~6MB', 'mediapipe-pose: ~12MB'],
        ['精度', 'mAP 50-95: ~50%+', 'PDJ@0.2: ~87%'],
    ]
)

p('系统默认使用YOLOv8n-pose（nano版），支持通过配置切换为YOLOv8s-pose（高精度版）或MediaPipe Pose（轻量版）。管理员可在设置页面动态切换模型。')

h3('2、模型结构选择')
p('YOLOv8-Pose是基于YOLOv8目标检测框架扩展的姿态估计模型。其核心结构包括：')
p('（1）Backbone（特征提取网络）：采用CSPDarknet结构，通过C2f模块实现跨阶段部分连接，提供多层特征图（P3/P4/P5）。')
p('（2）Neck（特征融合网络）：采用PAN-FPN（路径聚合网络+特征金字塔网络）结构，实现自顶向下和自底向上的双向特征融合。')
p('（3）Head（检测头）：解耦头设计，分为分类分支、边界框回归分支和关键点回归分支。每个关键点输出(x, y, confidence)三元组。')
p('（4）Loss设计：关键点回归采用OKS（Object Keypoint Similarity）损失函数，边界框回归采用CIoU损失。')
p('模型输入尺寸：640x640，输出：检测框 + 17关键点坐标（归一化0-1）+ 置信度。')

h3('3、姿态估计与动作识别算法设计')
p('姿态评估与纠错系统的核心算法流程为：')

p('步骤1：关键点提取（Model Engine）', bold=True)
p('接收原始图像帧（RGB格式，640x480），通过YOLOv8-Pose模型推理，输出至少1组17关键点坐标（COCO格式）。经过卡尔曼滤波平滑（PosePostProcessor）和置信度过滤（threshold≥0.5），去除低置信度关键点。')

p('步骤2：关节角度计算（PoseAnalyzer）', bold=True)
p('基于17关键点坐标，计算7个核心关节角度：左膝角（hip-knee-ankle）、右膝角、左髋角（shoulder-hip-knee）、右髋角、左肩角（elbow-shoulder-hip）、右肩角、躯干倾角（shoulder-hip垂线夹角）。使用向量点积法计算角度，精度要求MAE<3°。')

p('步骤3：动作状态识别（ActionRecognizer）', bold=True)
p('每个动作类型对应一个有限状态机（FSM），基于关节角度和关键点位置定义状态转移条件。以深蹲为例：idle → ready（髋角>160°）→ down（髋角<150°）→ bottom（膝角<90°）→ up（髋角>120°）→ complete（髋角>160°）→ rep_count++。')

p('步骤4：姿态纠错逻辑（纠错规则引擎）', bold=True)
p('在动作执行过程中，实时对比当前关节角度与预设标准阈值。当偏差超过容差范围时，触发纠错提示：')
p('● 膝内扣检测：|左膝角水平分量 - 右膝角水平分量| > 15° → 黄色警告："膝盖内扣，请向外打开与脚尖同向"')
p('● 深度不足：底部膝角 > 100° → 黄色警告："下蹲深度不足，请再蹲低10°"')
p('● 躯干前倾：躯干倾角 > 30° → 红色警告："躯干过度前倾，请保持背部挺直"')
p('● 不对称检测：左右髋角差 > 15° → 黄色警告："身体偏向左侧，请保持重心居中"')
p('● 危险动作：膝角过小（<60°）、躯干过度扭转 → 立即暂停、红色报警。')

p('步骤5：动作评分（Scoring）', bold=True)
p('训练结束后，基于以下维度计算动作总分（满分100）：')
p('● 角度达标率（40%）：各关节角度在标准范围内的帧占比')
p('● 稳定性（20%）：角度波动标准差（越小越好）')
p('● 对称性（20%）：左右关节角度差异均值')
p('● 完成度（20%）：实际重复次数与目标次数的比值')
p('综合得分 = 角度达标率×40 + 稳定性得分×20 + 对称性得分×20 + 完成度得分×20')

p('步骤6：FMS筛查评分（FMSEngine）', bold=True)
p('FMS筛查引擎针对5个测试动作分别计算0-100分，汇总生成5维度雷达图。各维度评分基于：平衡能力（闭眼单腿站立：重心摆动幅度+维持时长）、柔韧性（过头深蹲：髋/膝/踝联动灵活性+深度）、上肢功能（肩活动度：左右肩活动范围）、核心稳定（平板支撑：维持时长+躯干晃动）、左右对称（弓步蹲：左右动作对称性）。')

p('步骤7：处方生成（PrescriptionEngine）', bold=True)
p('基于FMS结果生成个性化4阶段处方：热身阶段（warmup,5分钟）→ 强化激活阶段（strengthen,8分钟,针对问题标签匹配干预动作）→ 主训练阶段（main,15-20分钟,排除被锁定动作）→ 冷身阶段（cooldown,5分钟）。锁定策略：核心稳定性<50分→强制基础模式；左右对称差异>20%→所有负重动作提示风险。')

doc.add_page_break()

# ====== Unit UI ======
h2('三、单元UI设计')
p('本节对系统主要功能页面的UI组件结构、交互流程和数据绑定进行详细设计。')

h3('1、FMS筛查页UI设计')
p('组件结构：FMSPage > CameraView + TestGuide + ProgressBar')
p('交互流程：用户进入页面→播放筛查说明视频→点击"开始测试"→CameraView调用getUserMedia()获取摄像头流→<canvas>叠加绘制人体骨架→每100ms通过WebSocket发送帧到后端→接收关键点坐标→Canvas渲染骨架→TestGuide显示当前测试动作名称、要领文字、倒计时→ProgressBar显示5个动作完成进度→全部完成后跳转至FMS报告页。')
p('数据绑定：WebSocket onmessage → 更新关键点状态 → Canvas重绘 → 更新TestGuide文案')

h3('2、训练页UI设计')
p('组件结构：TrainPage > CameraView + SkeletonCanvas + AngleChart + VoiceFeedback + StageIndicator')
p('交互流程：用户选择动作类型+训练模式→点击"开始训练"→启动WebSocket帧流→进入实时检测模式→SkeletonCanvas在摄像头画面上叠加17关键点连线骨架（置信度>0.7绿色/0.5-0.7黄色/<0.5红色）→AngleChart（ECharts）实时更新7关节角度柱状图，红色标出偏差关节→VoiceFeedback调用Web Speech API播报中文纠错提示→StageIndicator显示当前动作阶段（准备→下蹲→底部→上升→完成）。')
p('数据绑定：WebSocket每帧推送 {angles, stage, rep_count, feedback, warnings} → React状态更新 → 各子组件响应式渲染')

h3('3、标准学习页UI设计')
p('组件结构：LearnPage > DualSkeleton + DiffBarChart + VideoPlayer')
p('交互流程：左侧播放框显示标准示范视频+用户实时画面→DualSkeleton在Canvas上叠加用户骨架（蓝色）+标准骨架（绿色），关节角度差异用红色线段标注→DiffBarChart（ECharts）柱状图显示7关节用户值vs标准值vs差异值→下方文本框显示逐帧中文描述→完成后显示综合标准度评分和扣分明细。')

h3('4、处方管理页UI设计')
p('组件结构：PrescriptionPage > PhaseCard × 4 + UnlockProgress + PlanSwitcher')
p('交互流程：顶部显示当前激活方案信息→4张阶段卡片水平排列（热身/强化/主训练/冷身），每卡片内列出动作缩略图+名称+组数×次数→底部方案切换器显示A/B/C方案→点击"开始跟练"进入FollowPage→UnlockProgress进度条显示各维度解锁进度。')

h3('5、打卡页UI设计')
p('组件结构：CheckinPage > CheckinButton + StreakDisplay + CheckinCard(Canvas) + BadgeModal')
p('交互流程：页面顶部显示连续打卡天数+历史最高记录→中央大按钮"今日打卡"→打卡成功后Canvas渲染卡片（渐变背景+日期+昵称+连续天数+动作列表+鼓励语）→支持"保存图片"/"分享"→连续7天触发week_streak徽章弹窗，30天触发month_streak徽章。')

doc.add_page_break()

print("Part 5b done")


h2('四、数据访问层设计')

h3('1、类图设计')
p('数据访问层采用Repository模式（基于SQLAlchemy ORM），将数据库操作封装为独立的DAO（Data Access Object）类。每个DAO对应一张或多张关联表，提供标准的CRUD操作与业务查询方法。')
p('类图结构如下：')

code_block('''
┌──────────────────────────────────────────────────────────┐
│                    数据访问层 (DAO Layer)                    │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   UserDAO    │  │   FMSDAO     │  │  TrainDAO    │   │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤   │
│  │ + create()   │  │ + create()   │  │ + create()   │   │
│  │ + get_by_id()│  │ + get_by_id()│  │ + get_list() │   │
│  │ + get_by_    │  │ + get_user_  │  │ + get_by_id()│   │
│  │   username() │  │   records()  │  │ + get_user_  │   │
│  │ + update()   │  │ + get_latest │  │   records()  │   │
│  │ + deactivate │  │ + compare()  │  │ + get_trend()│   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Prescription │  │  CheckInDAO  │  │  ActionDAO   │   │
│  │    DAO       │  │              │  │              │   │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤   │
│  │ + create()   │  │ + checkin()  │  │ + get_all()  │   │
│  │ + get_active │  │ + get_today_ │  │ + get_by_id()│   │
│  │ + switch()   │  │   status()   │  │ + create()   │   │
│  │ + update()   │  │ + get_calend │  │ + update()   │   │
│  │ + get_items()│  │ + get_badges │  │ + search()   │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  ClassDAO    │  │ SystemLogDAO │  │AssessmentDAO │   │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤   │
│  │ + create()   │  │ + log()      │  │ + create()   │   │
│  │ + get_student│  │ + get_list() │  │ + get_user_  │   │
│  │   s()        │  │ + get_filter │  │   records()  │   │
│  │ + add_student│  │ + delete_old │  │ + get_latest │   │
│  │ + get_stats()│  └──────────────┘  └──────────────┘   │
│  └──────────────┘                                         │
│                                                            │
│  所有DAO依赖: Session (SQLAlchemy) ← get_db() (FastAPI)    │
└──────────────────────────────────────────────────────────┘
''')

h3('2、类的详细设计描述')

h3('2.1 UserDAO接口设计')
p('详细描述：UserDAO负责用户表的数据库操作，包括注册、查询、更新和账户状态管理。')
code_block('''class UserDAO:
    session: Session

    def create(self, username, password_hash, role, phone=None, gender=None) -> User:
        """创建新用户记录，返回User对象"""

    def get_by_id(self, user_id: int) -> Optional[User]:
        """通过用户ID精确查询"""

    def get_by_username(self, username: str) -> Optional[User]:
        """通过用户名精确查询（用于登录验证）"""

    def update(self, user_id: int, data: dict) -> User:
        """更新用户信息（昵称、手机号、头像等）"""

    def deactivate(self, user_id: int) -> None:
        """停用用户账号（软删除）"""

    def list_by_role(self, role, page: int, size: int) -> List[User]:
        """分页查询指定角色的用户列表"""

    def get_class_students(self, class_id: int) -> List[User]:
        """查询班级关联的学生列表"
''')

h3('2.2 FMSDAO接口设计')
p('详细描述：FMSDAO负责FMS筛查记录和评分的数据库操作，包括记录创建、查询和导出。')
code_block('''class FMSDAO:
    session: Session

    def create(self, user_id, scores, radar_data, problem_tags, lock_suggestions) -> FMSRecord:
        """创建FMS筛查记录（含5维度评分和雷达图数据）"""

    def get_by_id(self, record_id: int) -> Optional[FMSRecord]:
        """通过记录ID精确查询"""

    def get_user_records(self, user_id: int) -> List[FMSRecord]:
        """查询用户的所有FMS记录（按时间倒序）"""

    def get_latest(self, user_id: int) -> Optional[FMSRecord]:
        """获取用户最新的FMS记录"""

    def compare(self, record_id1: int, record_id2: int) -> dict:
        """对比两次FMS记录的各维度变化"""

    def delete(self, record_id: int) -> None:
        """删除FMS记录（软删除）"
''')

h3('2.3 TrainDAO接口设计')
p('详细描述：TrainDAO负责训练记录的数据操作，支持分页查询、统计分析等功能。')
code_block('''class TrainDAO:
    session: Session

    def create(self, user_id, prescription_id, action_id, action_name, mode, total_score, reps, feedback, angle_data, duration) -> TrainingRecord:
        """创建训练记录"""

    def get_by_id(self, record_id: int) -> Optional[TrainingRecord]:
        """通过记录ID精确查询"""

    def get_user_records(self, user_id, action_type=None, mode=None, page=1, size=20) -> List[TrainingRecord]:
        """分页查询用户训练记录，支持按动作类型和模式筛选"""

    def get_trend(self, user_id: int, days: int) -> List[dict]:
        """获取用户训练趋势数据（7/30/90天）"""

    def get_recent(self, user_id: int, limit: int = 5) -> List[TrainingRecord]:
        """获取用户最近N条训练记录（首页展示）"
''')

h3('2.4 PrescriptionDAO接口设计')
p('详细描述：PrescriptionDAO负责训练处方的CRUD操作，包括处方生成、激活切换、项目管理和解锁管理。')
code_block('''class PrescriptionDAO:
    session: Session

    def create(self, user_id, fms_record_id, phases, lock_info, intensity) -> Prescription:
        """生成新的训练处方（含4阶段动作列表）"""

    def get_active(self, user_id: int) -> Optional[Prescription]:
        """获取用户当前激活的处方"""

    def get_by_id(self, prescription_id: int) -> Optional[Prescription]:
        """通过处方ID精确查询"""

    def get_user_prescriptions(self, user_id: int) -> List[Prescription]:
        """查询用户所有处方记录"""

    def activate(self, user_id: int, prescription_id: int) -> None:
        """激活指定处方，同时将其他处方标记为非激活"""

    def update_phases(self, prescription_id: int, phases: dict) -> None:
        """更新处方阶段内容（教练调整处方时使用）"""

    def get_items(self, prescription_id: int) -> List[PrescriptionItem]:
        """获取指定处方的所有动作项目（按阶段和顺序排列）"""

    def update_item_status(self, item_id: int, status: str) -> None:
        """更新处方项目的完成状态"
''')

h3('2.5 CheckInDAO接口设计')
p('详细描述：CheckInDAO负责每日打卡和徽章管理的数据库操作。')
code_block('''class CheckInDAO:
    session: Session

    def checkin(self, user_id, actions, encouragement) -> CheckInCard:
        """创建今日打卡记录，计算连续打卡天数"""

    def get_today_status(self, user_id: int) -> Optional[CheckInCard]:
        """查询今日是否已打卡"""

    def get_calendar(self, user_id, year, month) -> List[dict]:
        """查询用户指定月份的打卡日历"""

    def get_streak(self, user_id: int) -> dict:
        """获取用户当前连续打卡天数和历史最高天数"""

    def award_badge(self, user_id: int, badge_type: str) -> Badge:
        """授予用户徽章（7天/30天连续打卡）"""

    def get_badges(self, user_id: int) -> List[Badge]:
        """获取用户已获徽章列表"
''')

h3('2.6 ActionDAO接口设计')
p('详细描述：ActionDAO负责动作库和问题标签映射的CRUD操作。')
code_block('''class ActionDAO:
    session: Session

    def get_all(self, category=None, difficulty=None, page=1, size=20) -> List[ActionLibrary]:
        """分页查询动作库，支持按类别和难度筛选"""

    def get_by_id(self, action_id: int) -> Optional[ActionLibrary]:
        """通过动作ID精确查询"""

    def create(self, data: dict) -> ActionLibrary:
        """新增动作（教练/管理员权限）"""

    def update(self, action_id: int, data: dict) -> ActionLibrary:
        """更新动作信息"""

    def search(self, keyword: str, page: int, size: int) -> List[ActionLibrary]:
        """模糊搜索动作"""

    def get_by_tags(self, tag_ids: list) -> List[ActionLibrary]:
        """通过问题标签查询对应干预动作"""

    def create_tag_mapping(self, tag_id, action_id, relevance) -> None:
        """创建标签-动作映射关系"""

    def get_tags(self) -> List[ProblemTag]:
        """获取所有问题标签"
''')

h3('2.7 DAO接口实现类汇总')
table(
    ['接口', '实现类', '对应数据库表'],
    [
        ['UserDAO', 'UserDAOImpl', 'user'],
        ['FMSDAO', 'FMSDAOImpl', 'fms_record'],
        ['TrainDAO', 'TrainDAOImpl', 'training_record'],
        ['PrescriptionDAO', 'PrescriptionDAOImpl', 'prescription, prescription_item'],
        ['CheckInDAO', 'CheckInDAOImpl', 'check_in_card, badge'],
        ['ActionDAO', 'ActionDAOImpl', 'action_library, problem_tag, tag_action_mapping'],
        ['ClassDAO', 'ClassDAOImpl', 'class_group, class_group_student'],
        ['SystemLogDAO', 'SystemLogDAOImpl', 'system_log'],
        ['AssessmentDAO', 'AssessmentDAOImpl', 'assessment_record'],
    ]
)

doc.add_page_break()

print("Part 5c done")


h2('五、业务逻辑层设计')

h3('1、类图设计')
p('业务逻辑层（Service Layer）位于数据访问层之上、API路由层之下，负责封装核心业务逻辑。每个Service对应一个业务领域，注入相应的DAO进行数据操作，同时调用Person B引擎层完成AI推理与决策。')

code_block('''
┌──────────────────────────────────────────────────────────────────┐
│                    业务逻辑层 (Service Layer)                       │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐   │
│  │   AuthService    │  │   FMSService     │  │ TrainService │   │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────┤   │
│  │ - user_dao       │  │ - fms_dao        │  │ - train_dao  │   │
│  │ + register()     │  │ - fms_engine     │  │ - engine_mgr │   │
│  │ + login()        │  │ + start_screen() │  │ + start()    │   │
│  │ + verify_token() │  │ + process_test() │  │ + process_   │   │
│  │ + get_profile()  │  │ + get_report()   │  │   frame()    │   │
│  │ + update_profile │  │ + export_pdf()   │  │ + get_result │   │
│  └──────────────────┘  └──────────────────┘  └──────────────┘   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐   │
│  │PrescriptionSvc   │  │  LearnService    │  │CheckInService│   │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────┤   │
│  │ - rx_dao         │  │ - action_dao     │  │ - checkin_dao│   │
│  │ - rx_engine      │  │ - std_learner    │  │ - checkin_eng│   │
│  │ + generate()     │  │ + start_compare()│  │ + do_checkin │   │
│  │ + activate()     │  │ + compare_frame()│  │ + get_status │   │
│  │ + get_progress() │  │ + get_diff()     │  │ + get_calend │   │
│  │ + adjust()       │  │ + get_score()    │  │ + get_badges │   │
│  └──────────────────┘  └──────────────────┘  └──────────────┘   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐   │
│  │  AdminService    │  │  ActionService   │  │CycleService  │   │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────┤   │
│  │ - class_dao      │  │ - action_dao     │  │ - user_dao   │   │
│  │ - log_dao        │  │ + get_library()  │  │ - cycle_mgr  │   │
│  │ + create_class() │  │ + create_action()│  │ + set_cycle()│   │
│  │ + get_class_     │  │ + update_action()│  │ + get_phase()│   │
│  │   stats()        │  │ + get_tags()     │  │ + adjust_rx()│   │
│  │ + import_student │  │ + mapping()      │  └──────────────┘   │
│  │ + get_logs()     │  └──────────────────┘                      │
│  │ + get_dashboard()│                                             │
│  └──────────────────┘                                             │
│  所有Service依赖: Session (SQLAlchemy) + Person B 引擎层组件        │
└──────────────────────────────────────────────────────────────────┘
''')

h3('2、类的详细设计描述')

h3('2.1 AuthService接口设计')
p('详细描述：AuthService负责用户认证与账户管理，是系统安全的第一道防线。')
p('事务定义：@Transactional，如果当前没有事务就新建一个事务，如果已经存在一个事务就加入到这个事务中。')
code_block('''class AuthService:
    user_dao: UserDAO

    def register(self, username, password, role, phone, gender) -> UserResponse:
        """注册新用户：密码哈希(bcrypt) → 创建User记录 → 返回用户信息"""

    def login(self, username, password) -> TokenResponse:
        """用户登录：验证密码 → 生成JWT Token(24h有效期) → 返回token+用户信息"""

    def verify_token(self, token: str) -> dict:
        """验证JWT Token有效性，返回解析后的用户信息"""

    def get_profile(self, user_id: int) -> UserResponse:
        """获取个人资料信息"""

    def update_profile(self, user_id: int, data: dict) -> UserResponse:
        """更新个人资料（昵称、手机号、头像等）"
''')

h3('2.2 FMSService接口设计')
p('详细描述：FMSService负责FMS功能性运动能力筛查的业务流程编排，协调前端帧流、模型推理、评分引擎和数据持久化。')
code_block('''class FMSService:
    fms_dao: FMSDAO
    fms_engine: FMSEngine

    def start_screening(self, user_id: int) -> str:
        """启动FMS筛查会话，返回session_id"""

    def process_screening(self, user_id, data) -> FMSResultResponse:
        """处理筛查数据：调用FMSEngine评分 → 生成雷达图 → 标记问题标签 → 生成锁定建议 → 持久化 → 返回报告"""

    def get_report(self, record_id, user_id) -> FMSResultResponse:
        """获取指定FMS筛查报告详情"""

    def get_user_records(self, user_id: int) -> List[FMSRecord]:
        """获取用户所有FMS筛查记录列表"""

    def export_pdf(self, record_id, user_id) -> bytes:
        """导出FMS报告PDF（含雷达图+评分+建议）"""

    def compare_reports(self, old_id, new_id) -> dict:
        """对比两次FMS报告的各维度变化"
''')

h3('2.3 TrainService接口设计')
p('详细描述：TrainService是系统的核心业务服务，负责训练会话的完整生命周期管理。')
code_block('''class TrainService:
    train_dao: TrainDAO
    engine_manager: EngineManager

    def start_training(self, user_id, action_type, mode, prescription_id=None) -> str:
        """启动训练会话：初始化对应动作的FSM识别器 → 返回session_id"""

    def process_frame(self, session_id, keypoints, angles) -> dict:
        """处理单帧数据：调用ActionRecognizer分析 → 返回 {stage, rep_count, feedback, warnings, score}"""

    def get_result(self, session_id, user_id, action_type) -> TrainResult:
        """结束训练：计算最终得分 → 生成评语 → 持久化TrainingRecord → 返回训练报告"""

    def get_records(self, user_id, action_type=None, mode=None, page=1, size=20) -> List:
        """分页查询用户训练记录"""

    def get_trend(self, user_id: int, days: int = 30) -> dict:
        """获取训练趋势数据（用于ECharts趋势图）"""

    def get_detail(self, record_id, user_id) -> TrainRecord:
        """获取单条训练记录的详细信息"
''')

h3('2.4 PrescriptionService接口设计')
p('详细描述：PrescriptionService负责智能训练处方的生成、管理和执行跟踪。')
code_block('''class PrescriptionService:
    rx_dao: PrescriptionDAO
    rx_engine: PrescriptionEngine
    unlock_mgr: UnlockManager

    def generate(self, user_id, fms_record_id) -> dict:
        """基于FMS结果生成3套备选处方方案（强化型/平衡型/恢复型）"""

    def activate(self, user_id, prescription_id) -> Prescription:
        """激活指定处方方案"""

    def get_active(self, user_id: int) -> Optional[Prescription]:
        """获取当前激活的处方"""

    def get_progress(self, user_id: int) -> dict:
        """获取处方执行进度：各维度改善进度、锁定动作解锁条件"""

    def get_reason(self, prescription_id: int) -> dict:
        """获取处方推荐理由（问题→干预的医学原理说明）"""

    def adjust(self, prescription_id, adjustments) -> Prescription:
        """教练调整处方内容（仅教练/管理员）"""

    def request_unlock(self, user_id, prescription_id, dimension) -> dict:
        """提前解锁申请：检查条件→解锁或提示需完成额外安全测试"
''')

h3('2.5 LearnService接口设计')
p('详细描述：LearnService负责标准学习模式，支持逐帧对比用户动作与标准动作的差异分析。')
code_block('''class LearnService:
    action_dao: ActionDAO
    std_learner: StandardLearner

    def start_compare(self, user_id, action_id) -> str:
        """启动标准学习会话：加载动作标准关键点数据 → 返回session_id"""

    def compare_frame(self, session_id, user_keypoints) -> dict:
        """单帧对比：用户关键点 vs 标准关键点 → 返回 {diff_angles, score, feedback}"""

    def get_diff(self, session_id: str) -> dict:
        """获取当前对比结果详情（7关节角度差异+评语）"""

    def get_score(self, session_id: str) -> dict:
        """获取学习综合评分（标准度0-100分+扣分明细）"
''')

h3('2.6 CheckInService接口设计')
p('详细描述：CheckInService负责每日打卡、连续天数计算和徽章授予。')
code_block('''class CheckInService:
    checkin_dao: CheckInDAO
    checkin_engine: CheckinEngine

    def do_checkin(self, user_id: int) -> dict:
        """执行每日打卡：检查今日是否已打卡 → 计算连续天数 → 创建记录 → 检查徽章触发 → 返回打卡卡片数据"""

    def get_status(self, user_id: int) -> dict:
        """获取打卡状态：今日是否已打卡、当前连续天数、历史最高天数"""

    def get_calendar(self, user_id, year, month) -> List[dict]:
        """获取指定月份打卡日历"""

    def get_badges(self, user_id: int) -> List[Badge]:
        """获取用户已获徽章列表"
''')

h3('2.7 AdminService接口设计')
p('详细描述：AdminService负责教练/管理员后台功能。')
code_block('''class AdminService:
    class_dao: ClassDAO
    log_dao: SystemLogDAO

    def create_class(self, coach_id, name, description) -> ClassGroup:
        """创建班级"""

    def get_class_stats(self, class_id: int) -> dict:
        """获取班级统计：5维度平均分、风险分布、对称性异常学员列表"""

    def import_students(self, class_id, students_data) -> dict:
        """批量导入学员（Excel解析 → 批量创建/关联）"""

    def get_logs(self, level=None, page=1, size=50) -> List[SystemLog]:
        """分页查询系统日志，支持按级别筛选"""

    def get_dashboard(self) -> dict:
        """管理仪表盘：总用户数、活跃用户、总训练次数、处方完成率"
''')

h3('2.8 ActionService接口设计')
p('详细描述：ActionService负责动作库和标签映射的管理。')
code_block('''class ActionService:
    action_dao: ActionDAO

    def get_library(self, category=None, difficulty=None, page=1, size=20) -> List[ActionLibrary]:
        """获取动作库列表（分页+筛选）"""

    def create_action(self, data: dict) -> ActionLibrary:
        """新增动作（教练权限）"""

    def update_action(self, action_id: int, data: dict) -> ActionLibrary:
        """编辑动作"""

    def get_tags(self) -> List[ProblemTag]:
        """获取所有问题标签"""

    def create_mapping(self, tag_id, action_id, relevance) -> None:
        """创建标签→动作映射"
''')

h3('2.9 CycleService接口设计')
p('详细描述：CycleService负责女性用户月经周期管理和训练强度自动调整。')
code_block('''class CycleService:
    user_dao: UserDAO
    cycle_manager: CycleManager

    def set_cycle(self, user_id, cycle_length, last_period_date) -> None:
        """设置/更新月经周期信息"""

    def get_phase(self, user_id: int) -> dict:
        """获取用户当前所处周期阶段和推荐训练强度"""

    def auto_adjust_rx(self, user_id, prescription) -> Prescription:
        """根据当前周期阶段自动调整处方"
''')

h3('2.10 业务接口实现类汇总')
table(
    ['接口', '实现类', '依赖DAO', '依赖引擎'],
    [
        ['AuthService', 'AuthServiceImpl', 'UserDAO', '无'],
        ['FMSService', 'FMSServiceImpl', 'FMSDAO', 'FMSEngine, RadarReport, ProblemTagger'],
        ['TrainService', 'TrainServiceImpl', 'TrainDAO', 'EngineManager, ActionRecognizer'],
        ['PrescriptionService', 'PrescriptionSvcImpl', 'PrescriptionDAO', 'PrescriptionEngine, UnlockManager'],
        ['LearnService', 'LearnServiceImpl', 'ActionDAO', 'StandardLearner'],
        ['CheckInService', 'CheckInServiceImpl', 'CheckInDAO', 'CheckinEngine'],
        ['AdminService', 'AdminServiceImpl', 'ClassDAO, SystemLogDAO', 'ClassStatsEngine'],
        ['ActionService', 'ActionServiceImpl', 'ActionDAO', '无'],
        ['CycleService', 'CycleServiceImpl', 'UserDAO', 'CycleManager'],
    ]
)

doc.add_page_break()

print("Part 5d done")


# ====== Part 6: Database Design ======
h1('第六部分 数据库设计')

h2('一、数据库整体结构图')
p('本系统采用MySQL 8.0作为主数据库，Redis 7作为缓存和会话管理，MinIO作为对象存储。数据库设计遵循第三范式（3NF），共设计14张核心业务表。')

code_block('''
┌─────────────────────────────────────────────────────────────┐
│                        数据库结构                              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐     ┌──────────┐     ┌──────────────┐        │
│  │   user   │────→│fms_record│────→│ prescription │        │
│  │  用户表   │     │ FMS记录  │     │   训练处方    │        │
│  └──────────┘     └──────────┘     └──────┬───────┘        │
│       │                 │                 │                  │
│       ├──→ training_record    (训练记录)                     │
│       ├──→ check_in_card      (打卡记录)                     │
│       ├──→ badge              (徽章)                         │
│       ├──→ user_cycle_config  (生理周期)                     │
│       ├──→ system_log         (系统日志)                     │
│       ├──→ assessment_record  (评估记录)                     │
│       │                                                      │
│  ┌──────────┐     ┌──────────────┐                          │
│  │class_group│←──→│class_group_   │                          │
│  │  班级表   │     │  student(关联)│                          │
│  └──────────┘     └──────────────┘                          │
│                                                               │
│  ┌──────────┐     ┌──────────────┐                          │
│  │action_lib│←──→│tag_action_    │←──→ problem_tag          │
│  │ 动作库   │     │  mapping     │     问题标签              │
│  └──────────┘     └──────────────┘                          │
└─────────────────────────────────────────────────────────────┘
''')

h2('二、用户管理')

h3('1、USER表结构')
table(
    ['序号', '列名', '数据类型', '注释'],
    [
        ['1', 'id', 'BIGINT AUTO_INCREMENT', '用户编号（主键）'],
        ['2', 'username', 'VARCHAR(50) UNIQUE NOT NULL', '用户名（唯一索引）'],
        ['3', 'password_hash', 'VARCHAR(255) NOT NULL', '密码哈希（sha256+salt）'],
        ['4', 'role', "ENUM('trainee','coach','admin')", '角色'],
        ['5', 'phone', 'VARCHAR(20)', '手机号码'],
        ['6', 'avatar', 'VARCHAR(500)', '头像URL'],
        ['7', 'gender', 'VARCHAR(10)', '性别（male/female/other）'],
        ['8', 'is_active', 'BOOLEAN DEFAULT TRUE', '账号状态'],
        ['9', 'created_at', 'DATETIME DEFAULT NOW()', '创建时间'],
    ]
)

h3('2、用户管理ER图说明')
p('● 一个用户（user）拥有多条FMS记录（fms_record），关系: 1..*')
p('● 一个用户（user）拥有多条训练记录（training_record），关系: 1..*')
p('● 一个用户（user）拥有多条打卡记录（check_in_card），关系: 1..*')
p('● 一个用户（user）拥有多个徽章（badge），关系: 1..*')
p('● 一个用户（user）拥有一个生理周期配置（user_cycle_config），关系: 1..1')
p('● 多个用户（user）可以属于一个班级（class_group），关系: *..1')

h2('三、训练检测任务存储管理')

h3('1、training_record表结构')
table(
    ['序号', '列名', '数据类型', '注释'],
    [
        ['1', 'id', 'BIGINT AUTO_INCREMENT', '训练记录编号（主键）'],
        ['2', 'user_id', 'BIGINT NOT NULL', '用户编号（外键→user.id）'],
        ['3', 'prescription_id', 'BIGINT', '关联处方编号（外键→prescription.id）'],
        ['4', 'action_id', 'BIGINT NOT NULL', '动作编号（外键→action_library.id）'],
        ['5', 'action_name', 'VARCHAR(64)', '动作名称'],
        ['6', 'mode', "ENUM('basic','advanced')", '训练模式'],
        ['7', 'total_score', 'DECIMAL(5,2)', '动作总分'],
        ['8', 'reps', 'INT', '重复次数'],
        ['9', 'feedback', 'TEXT', '训练反馈（纠错记录）'],
        ['10', 'key_angles', 'JSON', '关键关节角度历史数据'],
        ['11', 'angle_chart', 'JSON', '角度曲线图表数据'],
        ['12', 'duration_seconds', 'INT', '训练时长（秒）'],
        ['13', 'created_at', 'DATETIME DEFAULT NOW()', '创建时间'],
    ]
)

h3('2、fms_record表结构')
table(
    ['序号', '列名', '数据类型', '注释'],
    [
        ['1', 'id', 'BIGINT AUTO_INCREMENT', 'FMS记录编号（主键）'],
        ['2', 'user_id', 'BIGINT NOT NULL', '用户编号（外键→user.id）'],
        ['3', 'test_date', 'DATETIME', '筛查日期'],
        ['4', 'balance_score', 'FLOAT', '平衡能力评分（0-100）'],
        ['5', 'flexibility_score', 'FLOAT', '柔韧性评分（0-100）'],
        ['6', 'upper_limb_score', 'FLOAT', '上肢功能评分（0-100）'],
        ['7', 'core_score', 'FLOAT', '核心稳定性评分（0-100）'],
        ['8', 'symmetry_score', 'FLOAT', '左右对称性评分（0-100）'],
        ['9', 'overall_score', 'FLOAT', '综合评分（0-100）'],
        ['10', 'risk_level', "ENUM('low','medium','high')", '风险等级'],
        ['11', 'created_at', 'DATETIME DEFAULT NOW()', '创建时间'],
    ]
)

h2('四、处方与动作管理')

h3('1、prescription表结构')
table(
    ['序号', '列名', '数据类型', '注释'],
    [
        ['1', 'id', 'BIGINT AUTO_INCREMENT', '处方编号（主键）'],
        ['2', 'user_id', 'BIGINT NOT NULL', '用户编号（外键→user.id）'],
        ['3', 'fms_record_id', 'BIGINT', '关联FMS记录（外键→fms_record.id）'],
        ['4', 'status', "ENUM('active','completed','upgraded')", '处方状态'],
        ['5', 'phases', 'JSON NOT NULL', '4阶段动作配置'],
        ['6', 'lock_info', 'JSON', '锁定信息'],
        ['7', 'intensity_level', 'TINYINT DEFAULT 1', '训练强度等级'],
        ['8', 'created_at', 'DATETIME DEFAULT NOW()', '创建时间'],
    ]
)

h3('2、action_library表结构')
table(
    ['序号', '列名', '数据类型', '注释'],
    [
        ['1', 'id', 'BIGINT AUTO_INCREMENT', '动作编号（主键）'],
        ['2', 'name', 'VARCHAR(100) NOT NULL', '动作名称'],
        ['3', 'category', 'VARCHAR(50)', '动作分类'],
        ['4', 'difficulty', 'INT DEFAULT 1', '难度等级（1-4星）'],
        ['5', 'target_body_parts', 'VARCHAR(200)', '目标肌群'],
        ['6', 'description', 'TEXT', '动作描述'],
        ['7', 'video_url', 'VARCHAR(500)', '示范视频URL'],
        ['8', 'thumbnail_url', 'VARCHAR(500)', '缩略图URL'],
        ['9', 'created_at', 'DATETIME DEFAULT NOW()', '创建时间'],
    ]
)

h2('五、打卡与徽章管理')

h3('1、check_in_card表结构')
table(
    ['序号', '列名', '数据类型', '注释'],
    [
        ['1', 'id', 'BIGINT AUTO_INCREMENT', '打卡编号（主键）'],
        ['2', 'user_id', 'BIGINT NOT NULL', '用户编号（外键→user.id）'],
        ['3', 'date', 'DATETIME', '打卡日期'],
        ['4', 'streak_days', 'INT DEFAULT 1', '连续打卡天数'],
        ['5', 'completed_actions', 'INT DEFAULT 0', '完成动作数'],
        ['6', 'total_duration', 'INT DEFAULT 0', '训练总时长（分钟）'],
        ['7', 'created_at', 'DATETIME DEFAULT NOW()', '创建时间'],
    ]
)

h3('2、badge表结构')
table(
    ['序号', '列名', '数据类型', '注释'],
    [
        ['1', 'id', 'BIGINT AUTO_INCREMENT', '徽章编号（主键）'],
        ['2', 'user_id', 'BIGINT NOT NULL', '用户编号（外键→user.id）'],
        ['3', 'badge_type', 'VARCHAR(50) NOT NULL', '徽章类型（week_streak/month_streak）'],
        ['4', 'name', 'VARCHAR(100) NOT NULL', '徽章名称'],
        ['5', 'description', 'VARCHAR(200)', '徽章描述'],
        ['6', 'earned_at', 'DATETIME DEFAULT NOW()', '获得时间'],
    ]
)

h2('六、系统管理')

h3('1、class_group表结构')
table(
    ['序号', '列名', '数据类型', '注释'],
    [
        ['1', 'id', 'BIGINT AUTO_INCREMENT', '班级编号（主键）'],
        ['2', 'coach_id', 'BIGINT NOT NULL', '教练编号（外键→user.id）'],
        ['3', 'name', 'VARCHAR(100) NOT NULL', '班级名称'],
        ['4', 'description', 'TEXT', '班级描述'],
        ['5', 'created_at', 'DATETIME DEFAULT NOW()', '创建时间'],
    ]
)

h3('2、system_log表结构')
table(
    ['序号', '列名', '数据类型', '注释'],
    [
        ['1', 'id', 'BIGINT AUTO_INCREMENT', '日志编号（主键）'],
        ['2', 'user_id', 'BIGINT', '操作用户编号（外键→user.id）'],
        ['3', 'action', 'VARCHAR(100) NOT NULL', '操作类型'],
        ['4', 'detail', 'TEXT', '操作详情'],
        ['5', 'ip_address', 'VARCHAR(50)', 'IP地址'],
        ['6', 'created_at', 'DATETIME DEFAULT NOW()', '创建时间'],
    ]
)

h3('3、储存管理外键清单')
table(
    ['外键名称', '父表', '父键列', '子表', '外键列', '关系', '说明'],
    [
        ['FK_USER_FMS', 'user', 'id', 'fms_record', 'user_id', '1..*', '一个用户可生成多条FMS记录'],
        ['FK_USER_TRAIN', 'user', 'id', 'training_record', 'user_id', '1..*', '一个用户可产生多条训练记录'],
        ['FK_USER_RX', 'user', 'id', 'prescription', 'user_id', '1..*', '一个用户可拥有多个处方'],
        ['FK_FMS_RX', 'fms_record', 'id', 'prescription', 'fms_record_id', '1..*', '一次FMS可生成多个处方方案'],
        ['FK_USER_CHECKIN', 'user', 'id', 'check_in_card', 'user_id', '1..*', '一个用户可有多条打卡记录'],
        ['FK_USER_BADGE', 'user', 'id', 'badge', 'user_id', '1..*', '一个用户可获得多个徽章'],
        ['FK_USER_CYCLE', 'user', 'id', 'user_cycle_config', 'user_id', '1..1', '一个用户有一个生理周期配置'],
        ['FK_COACH_CLASS', 'user', 'id', 'class_group', 'coach_id', '1..*', '一个教练可管理多个班级'],
        ['FK_RX_ITEM_RX', 'prescription', 'id', 'prescription_item', 'prescription_id', '1..*', '一个处方包含多个动作项目'],
        ['FK_ITEM_ACTION', 'action_library', 'id', 'prescription_item', 'action_id', '1..*', '一个动作可出现在多个处方中'],
        ['FK_TAG_MAP_TAG', 'problem_tag', 'id', 'tag_action_mapping', 'tag_id', '1..*', '一个标签可映射到多个动作'],
        ['FK_TAG_MAP_ACT', 'action_library', 'id', 'tag_action_mapping', 'action_id', '1..*', '一个动作可匹配多个标签'],
    ]
)

doc.add_page_break()

print("Part 6 done")


# ====== Part 7: Supplementary Design ======
h1('第七部分 补充设计和说明')

h2('一、编译运行环境设计')

h3('1、系统环境')
p('系统环境是指软件开发过程中所用的硬件设备、操作系统和相关软件等基础设施。本项目系统环境包括前后端开发环境、算法开发平台环境、服务器部署环境、客户使用环境四个系统环境。')

h3('1.1 前后端开发环境')
table(
    ['配置名称', '配置信息'],
    [
        ['操作系统', 'Windows 11 22H2'],
        ['CPU', 'Intel(R) Core(TM) i7-9750H'],
        ['GPU', 'NVIDIA GeForce RTX 2070'],
        ['内存', '32GB RAM'],
        ['硬盘', 'SAMSUNG SSD 1TB'],
    ]
)

h3('1.2 算法开发平台环境')
table(
    ['配置名称', '最低配置', '推荐配置'],
    [
        ['操作系统', 'Windows 10/11', 'Windows 11 / Ubuntu 22.04'],
        ['CPU', 'Intel Core i5-10400', 'Intel Xeon Gold 6226R'],
        ['GPU', 'NVIDIA GTX 1660 (6GB)', 'NVIDIA RTX 3090 (24GB)'],
        ['内存', '16GB RAM', '32GB RAM'],
        ['硬盘', 'SSD 512GB', 'SSD 1TB'],
    ]
)

h3('1.3 服务器部署环境')
table(
    ['配置名称', '配置信息'],
    [
        ['服务器提供方', '阿里云'],
        ['服务器位置', '上海'],
        ['系统', 'CentOS 7 / Ubuntu 22.04'],
        ['CPU', 'Intel(R) Xeon(R) Platinum 8269CY (4核)'],
        ['GPU', 'NVIDIA Tesla T4 (16GB)'],
        ['内存', '16GB RAM'],
        ['硬盘', '100GB SSD'],
    ]
)

h3('1.4 客户使用环境')
table(
    ['配置名称', '最低配置', '推荐配置'],
    [
        ['操作系统', 'Windows 10', 'Windows 10/11'],
        ['浏览器', 'Chrome 90+ / Edge 90+', 'Chrome 120+ / Edge 120+'],
        ['CPU', 'Intel Core i3 / AMD Ryzen 3', 'Intel Core i5 / AMD Ryzen 5'],
        ['摄像头', '720P USB摄像头', '1080P USB摄像头（30fps）'],
        ['内存', '4GB RAM', '8GB RAM'],
        ['网络', '宽带 10Mbps', '宽带 50Mbps'],
    ]
)

h2('二、运行环境')

h3('1、数据库')
table(
    ['组件', '版本/配置'],
    [
        ['MySQL', '8.0（端口3306）'],
        ['Redis', '7.x-alpine（端口6379）'],
        ['MinIO', 'latest（端口9000/9001）'],
    ]
)

h3('2、前端运行环境库')
table(
    ['包名', '版本', '用途'],
    [
        ['node.js', '18.x LTS', 'JavaScript运行时'],
        ['react', '18.2.0', 'UI框架'],
        ['react-router-dom', '6.x', '前端路由'],
        ['antd', '5.x', 'UI组件库（Ant Design）'],
        ['echarts', '5.4.x', '图表库（雷达图/柱状图/折线图）'],
        ['axios', '1.x', 'HTTP请求库'],
        ['typescript', '5.x', '类型安全'],
        ['vite', '5.x', '构建工具'],
    ]
)

h3('3、后端运行环境库')
table(
    ['包名', '版本', '用途'],
    [
        ['python', '3.10+', 'Python运行时'],
        ['fastapi', '0.100+', 'Web框架'],
        ['uvicorn', '0.23+', 'ASGI服务器'],
        ['sqlalchemy', '2.0+', 'ORM框架'],
        ['pymysql', '1.1+', 'MySQL驱动'],
        ['python-jose', '3.3+', 'JWT处理'],
        ['ultralytics', '8.1+', 'YOLOv8框架'],
        ['opencv-python', '4.8+', '图像处理'],
        ['numpy', '1.24+', '数值计算'],
        ['redis', '4.5+', 'Redis客户端'],
        ['reportlab', '4.0+', 'PDF生成'],
        ['pydantic', '2.0+', '数据验证'],
        ['alembic', '1.12+', '数据库迁移'],
    ]
)

h3('4、算法运行环境库')
table(
    ['包名', '版本', '用途'],
    [
        ['torch', '2.0+', 'PyTorch深度学习框架'],
        ['torchvision', '0.15+', 'PyTorch视觉库'],
        ['ultralytics', '8.1+', 'YOLOv8-Pose推理'],
        ['mediapipe', '0.10+', 'MediaPipe Pose（备用方案）'],
        ['filterpy', '1.4+', '卡尔曼滤波'],
        ['scipy', '1.10+', '科学计算/信号处理'],
    ]
)

h2('三、项目工程目录结构设计')
p('项目采用分层架构的目录组织方式，以下为完整的工程目录结构：')

code_block('''运动姿态评估与纠错系统/
├── backend/                          # 后端API服务 (Person C)
│   ├── main.py                       # FastAPI应用入口
│   ├── config.py                     # 配置管理
│   ├── database/
│   │   ├── connection.py             # 数据库连接
│   │   └── models.py                 # ORM模型定义（14张表）
│   ├── routers/                      # API路由（auth/training/fms/等）
│   ├── services/                     # 业务服务层
│   ├── schemas/                      # Pydantic模型
│   ├── websocket/                    # WebSocket管理
│   ├── utils/                        # 工具（错误码/PDF导出）
│   └── migrations/                   # Alembic迁移脚本
│
├── models/                           # 模型推理+业务引擎 (Person A + B)
│   ├── yolo_pose_engine.py           # YOLOv8-Pose推理引擎
│   ├── angle_calculator.py           # 角度计算器
│   ├── posture_analyzer.py           # 姿态分析器
│   ├── scoring.py                    # 动作评分模块
│   ├── action_recognizer/            # 动作识别器包（FSM）
│   ├── assessment/                   # 体态评估包
│   ├── fms_archived/                 # FMS筛查引擎
│   ├── prescription/                 # 处方引擎
│   └── knowledge/                    # 知识库（JSON配置）
│
├── frontend/                         # 前端SPA (Person D)
│   ├── src/
│   │   ├── services/api.ts           # Axios API封装
│   │   ├── store/auth.ts             # 认证状态管理
│   │   ├── types/index.ts            # TypeScript类型定义
│   │   └── components/               # React组件
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── utils/                            # 通用工具
├── app.py / run.py                   # 应用入口/启动脚本
├── process_video.py                  # 离线视频处理
└── requirements.txt                  # Python依赖清单
''')

h2('四、配置设计')
p('系统采用环境变量 + pydantic Settings 的配置管理方案，支持多环境（开发/测试/生产）灵活切换。')

h3('1、核心配置项')
table(
    ['分类', '配置项', '类型', '默认值', '说明'],
    [
        ['数据库', 'DB_TYPE', 'str', 'mysql', '数据库类型（mysql/sqlite）'],
        ['数据库', 'DB_HOST', 'str', 'localhost', '数据库主机地址'],
        ['数据库', 'DB_PORT', 'int', '3306', '数据库端口'],
        ['数据库', 'DB_USER', 'str', 'root', '数据库用户名'],
        ['数据库', 'DB_PASSWORD', 'str', '（必填）', '数据库密码'],
        ['数据库', 'DB_NAME', 'str', 'pose_correction', '数据库名称'],
        ['认证', 'SECRET_KEY', 'str', '（必填）', 'JWT签名密钥'],
        ['认证', 'ALGORITHM', 'str', 'HS256', 'JWT签名算法'],
        ['认证', 'ACCESS_TOKEN_EXPIRE_MINUTES', 'int', '1440', 'Token有效期（分钟）'],
        ['模型', 'MODEL_PATH', 'str', 'yolov8n-pose.pt', '默认模型路径'],
        ['模型', 'DEVICE', 'str', 'auto', '推理设备（auto/cpu/cuda）'],
        ['服务', 'HOST', 'str', '0.0.0.0', '绑定主机'],
        ['服务', 'PORT', 'int', '8002', '服务端口'],
        ['跨域', 'CORS_ORIGINS', 'list', 'localhost:5173', '允许跨域来源列表'],
    ]
)

h3('2、环境变量配置示例')
code_block('''# .env 文件示例
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=pose_correction

SECRET_KEY=pose-assessment-secret-key-2026
MODEL_PATH=yolov8n-pose.pt
DEVICE=auto

HOST=0.0.0.0
PORT=8002
CORS_ORIGINS=["http://localhost:5173","http://localhost:5179"]
''')

h2('五、部署过程描述')
p('部署步骤如下：')
p('1. 环境准备：安装Docker + Docker Compose，确保NVIDIA Container Toolkit已安装（GPU环境）')
p('2. 克隆代码仓库，进入项目根目录')
p('3. 配置环境变量：复制.env.example为.env，修改数据库密码、JWT密钥等敏感配置')
p('4. 启动服务：docker-compose up -d（启动MySQL + Redis + MinIO + FastAPI + Nginx）')
p('5. 数据库初始化：运行Alembic迁移脚本创建14张表，导入动作库初始数据')
p('6. 模型文件：将yolov8n-pose.pt放入models/目录或配置MODEL_PATH指向正确路径')
p('7. 验证：访问 http://localhost:8002/docs 查看Swagger API文档，确认所有端点正常')

doc.add_page_break()

# ====== End ======
p('')
p('--- 文档结束 ---', bold=True, indent=False)
p('文档版本：V2.0 | 生成日期：' + datetime.date.today().strftime('%Y年%m月%d日') + ' | 状态：详细设计-单元模块设计', indent=False)

output_path = r'D:\workbench\program3\doc\详细设计\运动姿态评估与纠错系统-详细设计文档_单元模块设计.docx'
doc.save(output_path)
print(f'Document saved to: {output_path}')
