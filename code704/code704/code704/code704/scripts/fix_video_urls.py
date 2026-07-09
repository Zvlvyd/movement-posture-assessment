# -*- coding: utf-8 -*-
"""批量修正 standard_actions.json 中的 video_url，匹配 public/media/videos 下的实际文件"""
import os, json, re

JSON_PATH = r"d:\program\pythonProject\运动姿态评估与纠错系统\code704\code704\code704\models\knowledge\standard_actions.json"
VIDEO_DIR = r"d:\program\pythonProject\运动姿态评估与纠错系统\code704\code704\code704\frontend-vue\public\media\videos"

videos = set(os.listdir(VIDEO_DIR))

# 手动映射：动作名 -> 视频文件名（中文名到英文文件名的人工对应）
NAME_TO_FILE = {
    "标准深蹲": "squat_left_standard.mp4",
    "标准俯卧撑": "standardpush-standard.mp4",
    "标准平板支撑": "plank_standard.mp4",
    "死虫式": "dead_bug_standard .mp4",
    "猫牛式": "cat_cow_stretch_standard.mp4",
    "鸟狗式": "bird_dog_standard.mp4",
    "臀桥": "glute_bridge_standard.mp4",
    "单腿臀桥": "single_leg_glute_bridge_standard.mp4",
    "保加利亚分腿蹲": "bulgarian_split_squat_standard.mp4",
    "肩部推举": "shoulder_press__standard.mp4",
    "硬拉": "deadlift_standard.mp4",
    "罗马尼亚硬拉": "romanian_deadlift_standard.mp4",
    "弓步蹲": "lunge_left_standard.mp4",
    "深弓步": "deep_lunge_standard.mp4",
    "靠墙天使": "wall_angels_standard.mp4",
    "登山者（慢速控制）": "slow_controlled_mountain_climber_standard.mp4",
    "反向平板": "reverse_plank_standard.mp4",
    "膝盖平板支撑": "knee_plank_standard.mp4",
    "开合跳": "jumpjack_standard.mp4",
    "窄距俯卧撑": "closegrip_pushup_standard.mp4",
    "单腿俯卧撑": "single_leg_pushup_standard.mp4",
    "上斜俯卧撑": "incline_pushup_standard.mp4",
    "下斜俯卧撑": "incline_pushup_standard.mp4",
    "墙壁俯卧撑": "wall_pushup_standard.mp4",
    "膝盖俯卧撑": "knee_pushup_standard.mp4",
    "箱式深蹲": "box_squat_standard.mp4",
    "椅子辅助深蹲": "chair_assisted_squat_standard.mp4",
    "窄距深蹲": "close_stance_squat_standard.mp4",
    "深蹲静态保持": "deepsquat_hold_standard.mp4",
    "最伟大拉伸": "worlds_greatest_stretch_standard.mp4",
    "小狗伸展式": "extend_puppy_standard.mp4",
    "门框胸拉伸": "doorway_chest_stretch_standard.mp4",
    "髋关节环绕": "hip_circles_standard.mp4",
    "髋部打开": "hip_openers_standard.mp4",
    "踝关节环绕": "ankle_circles_standard.mp4",
    "肩部环绕": "shoulder_circles_standard.mp4",
    "肩部拉伸": "shoulder_stretch_standard.mp4",
    "胸部打开": "chest_open_standard.mp4",
    "单腿站立": "single_leg_stand_standard.mp4",
    "双腿闭眼站立": "stand_eyesclosed_standard.mp4",
    "闭眼单腿站立": "stand_eyesclosed_standard.mp4",
    "侧平板": "standard_side_plank_standard .mp4",
    "小狗伸展式": "extend_puppy_standard.mp4",
    "地板天使": "floor_angels_standard.mp4",
    "侧平板加旋转": "side_plank_with_rotation_standard.mp4",
    "侧卧胸椎旋转": "sidelying_thoracic_rotation_standard.mp4",
    "前后脚掌重心转换": "heeltotoe_rocks_standard.mp4",
    "仰卧直腿下落（离心）": "supine_straight_leg_lowering_standard.mp4",
    "猫牛式环绕": "cat_cow_circles_standard.mp4",
    "肩桥": "shoulder_bridge_standard.mp4",
    "普鲁士T字举": "proneT_raise_standard.mp4",
    "普鲁士W字举": "proneW_raise_standard.mp4",
    "普鲁士Y字举": "proneY_raise_standard.mp4",
    "侧向伸展": "side_reaches_standard.mp4",
}

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

updated = 0
for name, a in data['actions'].items():
    old = a.get('video_url', '')
    new_file = NAME_TO_FILE.get(name)

    if new_file and new_file in videos:
        new_url = f"/media/videos/{new_file}"
        if old != new_url:
            a['video_url'] = new_url
            print(f"  UPDATE: {name}: {old or '(无)'} -> {new_url}")
            updated += 1
    elif new_file and new_file not in videos:
        print(f"  WARN: {name}: file '{new_file}' not found on disk")
    else:
        print(f"  SKIP: {name} (no mapping, old={old or '(无)'})")

with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\nUpdated {updated} video_urls")
