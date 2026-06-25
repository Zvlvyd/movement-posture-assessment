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
doc.save('D:/workbench/program3/plan/详细设计文档_v1.0.docx')
print('SAVED preliminary')
