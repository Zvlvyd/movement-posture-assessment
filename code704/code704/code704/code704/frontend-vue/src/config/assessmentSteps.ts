/**
 * 体态评估动作子步骤配置
 *
 * 每一项评估包含 1~N 个子步骤。每个子步骤有对应的引导语、目标关节高亮、
 * 过渡提示语，以及为尚未制作完成的示范图片/视频预留的占位。
 *
 * 图片/视频就绪后，只需将 imageUrls / videoUrl 填入即可自动展示。
 */

export interface MovementStep {
  /** 步骤 ID */
  id: string;
  /** 步骤名称（如"左旋"、"屈曲"） */
  name: string;
  /** 当前步骤引导语 */
  instruction: string;
  /** 本步骤完成后的过渡提示（如"回正"、"换右侧继续"） */
  transitionHint: string;
  /** 本步骤关注的关节角度键名 */
  highlightAngles: string[];
  /** 示范图片 URL 列表，支持同一步骤展示多张参考图 */
  imageUrls: string[];
  /** 示范视频 URL（就绪后填入，留空使用占位） */
  videoUrl: string;
}

export interface AssessmentItem {
  index: number;
  name: string;
  durationHint: string;
  steps: MovementStep[];
}

const PLACEHOLDER = '';

export const ASSESSMENT_ITEMS: AssessmentItem[] = [
  // ────────── 0. 颈部活动度评估 ──────────
  {
    index: 0,
    name: '颈部活动度评估',
    durationHint: '约30秒',
    steps: [
      {
        id: 'neck_rotate_left',
        name: '颈部左旋',
        instruction: '站直身体，缓慢将头转向左侧至最大限度，保持2秒',
        transitionHint: '请回正头部，准备向右旋转',
        highlightAngles: ['neck_tilt'],
        imageUrls: ['/media/postural_assessment/1_left.png'],
        videoUrl: PLACEHOLDER,
      },
      {
        id: 'neck_rotate_right',
        name: '颈部右旋',
        instruction: '将头缓慢转向右侧至最大限度，保持2秒',
        transitionHint: '请回正头部，准备左侧屈',
        highlightAngles: ['neck_tilt'],
        imageUrls: ['/media/postural_assessment/1_right.png'],
        videoUrl: PLACEHOLDER,
      },
      {
        id: 'neck_lateral_left',
        name: '颈部左侧屈',
        instruction: '头部缓慢向左肩侧屈，感受右侧颈部拉伸',
        transitionHint: '请回正头部，准备右侧屈',
        highlightAngles: ['head_tilt'],
        imageUrls: ['/media/postural_assessment/1.2_left.png'],
        videoUrl: PLACEHOLDER,
      },
      {
        id: 'neck_lateral_right',
        name: '颈部右侧屈',
        instruction: '头部缓慢向右肩侧屈，感受左侧颈部拉伸',
        transitionHint: '',
        highlightAngles: ['head_tilt'],
        imageUrls: ['/media/postural_assessment/1.2_right.png'],
        videoUrl: PLACEHOLDER,
      },
    ],
  },

  // ────────── 1. 肩关节活动度评估 ──────────
  {
    index: 1,
    name: '肩关节活动度评估',
    durationHint: '约30秒',
    steps: [
      {
        id: 'shoulder_flexion',
        name: '双臂前举',
        instruction: '双臂从体侧缓慢向前举起至头顶上方，尽量伸直手臂',
        transitionHint: '请放下手臂，准备背后触手测试',
        highlightAngles: ['left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow'],
        imageUrls: [
          '/media/postural_assessment/2_ready.png',
          '/media/postural_assessment/2_done.png',
        ],
        videoUrl: PLACEHOLDER,
      },
      {
        id: 'shoulder_back_touch',
        name: '背后触手测试',
        instruction: '右手从肩上向后、左手从腰后向上，尝试在背后触碰双手',
        transitionHint: '',
        highlightAngles: ['left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow'],
        imageUrls: [
          '/media/postural_assessment/2.1front.png',
          '/media/postural_assessment/2.1_done.png',
        ],
        videoUrl: PLACEHOLDER,
      },
    ],
  },

  // ────────── 2. 脊柱活动度评估 ──────────
  {
    index: 2,
    name: '脊柱活动度评估',
    durationHint: '约30秒',
    steps: [
      {
        id: 'spine_flexion',
        name: '体前屈',
        instruction: '双脚与肩同宽，缓慢向前弯腰，尽量用手触摸脚趾，膝盖保持伸直',
        transitionHint: '请缓慢直立回正，准备侧屈',
        highlightAngles: ['trunk_tilt', 'left_hip', 'right_hip'],
        imageUrls: ['/media/postural_assessment/3_front.png'],
        videoUrl: PLACEHOLDER,
      },
      {
        id: 'spine_lateral_left',
        name: '左侧屈',
        instruction: '身体缓慢向左侧弯曲，感受右侧拉伸',
        transitionHint: '请回正，准备向右侧弯曲',
        highlightAngles: ['trunk_tilt', 'left_hip', 'right_hip'],
        imageUrls: ['/media/postural_assessment/3_left.png'],
        videoUrl: PLACEHOLDER,
      },
      {
        id: 'spine_lateral_right',
        name: '右侧屈',
        instruction: '身体缓慢向右侧弯曲，感受左侧拉伸',
        transitionHint: '',
        highlightAngles: ['trunk_tilt', 'left_hip', 'right_hip'],
        imageUrls: ['/media/postural_assessment/3_right.png'],
        videoUrl: PLACEHOLDER,
      },
    ],
  },

  // ────────── 3. 深蹲活动度评估 ──────────
  {
    index: 3,
    name: '深蹲活动度评估',
    durationHint: '约40秒',
    steps: [
      {
        id: 'squat_both',
        name: '双腿深蹲',
        instruction: '双脚与肩同宽，双手前平举保持平衡，缓慢下蹲至最低点，保持脚跟不离地',
        transitionHint: '请站立回正，准备单腿下蹲',
        highlightAngles: ['left_knee', 'right_knee', 'left_hip', 'right_hip'],
        imageUrls: ['/media/postural_assessment/4_both.png'],
        videoUrl: PLACEHOLDER,
      },
      {
        id: 'squat_left',
        name: '左腿单腿蹲',
        instruction: '重心移至左腿，右腿微抬，做小幅下蹲',
        transitionHint: '请换右腿',
        highlightAngles: ['left_knee', 'left_hip'],
        imageUrls: ['/media/postural_assessment/4_left.png'],
        videoUrl: PLACEHOLDER,
      },
      {
        id: 'squat_right',
        name: '右腿单腿蹲',
        instruction: '重心移至右腿，左腿微抬，做小幅下蹲',
        transitionHint: '',
        highlightAngles: ['right_knee', 'right_hip'],
        imageUrls: ['/media/postural_assessment/4_right.png'],
        videoUrl: PLACEHOLDER,
      },
    ],
  },

  // ────────── 4. 髋关节活动度评估 ──────────
  {
    index: 4,
    name: '髋关节活动度评估',
    durationHint: '约40秒',
    steps: [
      {
        id: 'hip_flexion_left',
        name: '左腿抬膝',
        instruction: '扶墙保持平衡，将左膝向胸部抬起至最高',
        transitionHint: '请放下左腿，准备外展',
        highlightAngles: ['left_hip'],
        imageUrls: ['/media/postural_assessment/5.1.png'],
        videoUrl: PLACEHOLDER,
      },
      {
        id: 'hip_abduct_left',
        name: '左腿外展',
        instruction: '左腿缓慢向侧面抬起（外展），保持身体直立',
        transitionHint: '请放下左腿，换右侧',
        highlightAngles: ['left_hip'],
        imageUrls: ['/media/postural_assessment/5.2.png'],
        videoUrl: PLACEHOLDER,
      },
      {
        id: 'hip_flexion_right',
        name: '右腿抬膝',
        instruction: '扶墙保持平衡，将右膝向胸部抬起至最高',
        transitionHint: '请放下右腿，准备外展',
        highlightAngles: ['right_hip'],
        imageUrls: ['/media/postural_assessment/5.3.png'],
        videoUrl: PLACEHOLDER,
      },
      {
        id: 'hip_abduct_right',
        name: '右腿外展',
        instruction: '右腿缓慢向侧面抬起（外展），保持身体直立',
        transitionHint: '',
        highlightAngles: ['right_hip'],
        imageUrls: ['/media/postural_assessment/5.4.png'],
        videoUrl: PLACEHOLDER,
      },
    ],
  },
];

/** 根据后端返回的 movement index 查找对应的前端评估项配置 */
export function getAssessmentItem(index: number): AssessmentItem | undefined {
  return ASSESSMENT_ITEMS.find(item => item.index === index);
}
