import os
import cv2
import json
import numpy as np

os.environ['ULTRALYTICS_CONFIG_DIR'] = os.path.join(os.getcwd(), 'ultralytics_config')
os.makedirs(os.environ['ULTRALYTICS_CONFIG_DIR'], exist_ok=True)

from models.yolo_pose_engine import YOLOPoseEngine
from utils.pose_postprocessor import PosePostProcessor

def process_video(input_path, output_path='视频_结果.mp4', export_frames=10):
    print("=== 视频处理开始 ===")
    
    if not os.path.exists(input_path):
        print(f"错误：视频文件不存在 {input_path}")
        return
    
    engine = YOLOPoseEngine(model_path='yolov8n-pose.pt', device='cpu')
    print("✅ 模型加载成功")
    
    cap = cv2.VideoCapture(input_path)
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"✅ 视频信息：{width} x {height}, {fps:.1f} FPS, {total_frames} 帧")
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    postprocessor = PosePostProcessor(width, height)
    prev_persons = None
    
    frame_count = 0
    frame_interval = max(1, total_frames // export_frames)
    all_frames_data = []
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        persons, _ = engine.process_frame(frame)
        persons = postprocessor.process(persons, prev_persons)
        prev_persons = persons
        
        vis_frame = engine.draw_keypoints(frame, persons)
        out.write(vis_frame)
        
        if frame_count % frame_interval == 0:
            frame_data = {
                'frame_number': frame_count,
                'timestamp': frame_count / fps,
                'persons': []
            }
            
            for person in persons:
                person_data = {
                    'bbox': person['bbox'].tolist() if person['bbox'] is not None else None,
                    'bbox_confidence': float(person['bbox_confidence']) if person['bbox_confidence'] is not None else None,
                    'keypoints': []
                }
                
                for kp in person['keypoints']:
                    person_data['keypoints'].append({
                        'id': kp['id'],
                        'label': kp['label'],
                        'x': float(kp['x']),
                        'y': float(kp['y']),
                        'confidence': float(kp['confidence'])
                    })
                
                frame_data['persons'].append(person_data)
            
            all_frames_data.append(frame_data)
        
        frame_count += 1
        if frame_count % 30 == 0:
            progress = (frame_count / total_frames) * 100
            print(f"处理进度: {progress:.1f}% ({frame_count}/{total_frames}帧)")
    
    cap.release()
    out.release()
    print(f"✅ 处理完成，输出视频: {output_path}")
    
    with open('视频关键点数据.json', 'w', encoding='utf-8') as f:
        json.dump({
            'video_info': {
                'width': width,
                'height': height,
                'fps': fps,
                'total_frames': total_frames,
                'exported_frames': len(all_frames_data)
            },
            'frames': all_frames_data
        }, f, indent=2, ensure_ascii=False)
    
    print("✅ 关键点数据已导出到 视频关键点数据.json")

if __name__ == '__main__':
    process_video('视频.mp4')