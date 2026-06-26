import cv2
import argparse
import os
import torch
from models.yolo_pose_engine import YOLOPoseEngine
from utils.pose_postprocessor import PosePostProcessor

class PoseEstimationApp:
    def __init__(self, model_path='yolov8n-pose.pt', device='auto'):
        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        self.engine = YOLOPoseEngine(model_path=model_path, device=device)
        self.postprocessor = None
        self.prev_persons = None
        
        print(f"YOLO-Pose Engine initialized with device: {device}")
    
    def process_image(self, image_path, output_path=None, visualize=True):
        frame = cv2.imread(image_path)
        if frame is None:
            print(f"Error: Cannot read image {image_path}")
            return None
        
        if self.postprocessor is None:
            height, width = frame.shape[:2]
            self.postprocessor = PosePostProcessor(width, height)
        
        persons, _ = self.engine.process_frame(frame)
        persons = self.postprocessor.process(persons, self.prev_persons)
        self.prev_persons = persons
        
        if visualize:
            vis_frame = self.engine.draw_keypoints(frame, persons, show_confidence=True)
            if output_path:
                cv2.imwrite(output_path, vis_frame)
            return persons, vis_frame
        
        return persons, None
    
    def process_video(self, input_path, output_path=None, show=True):
        cap = cv2.VideoCapture(input_path)
        
        if not cap.isOpened():
            print(f"Error: Cannot open video {input_path}")
            return
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        self.postprocessor = PosePostProcessor(width, height)
        
        out = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            persons, _ = self.engine.process_frame(frame)
            persons = self.postprocessor.process(persons, self.prev_persons)
            self.prev_persons = persons
            
            vis_frame = self.engine.draw_keypoints(frame, persons)
            
            if out:
                out.write(vis_frame)
            
            if show:
                cv2.imshow('YOLO-Pose Detection', vis_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"Processed {frame_count}/{total_frames} frames")
        
        cap.release()
        if out:
            out.release()
        cv2.destroyAllWindows()
    
    def process_webcam(self, camera_index=0, show=True):
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            print(f"Error: Cannot open webcam {camera_index}")
            return
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.postprocessor = PosePostProcessor(width, height)
        
        print("Press 'q' to quit")
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            persons, _ = self.engine.process_frame(frame)
            persons = self.postprocessor.process(persons, self.prev_persons)
            self.prev_persons = persons
            
            vis_frame = self.engine.draw_keypoints(frame, persons)
            
            if show:
                cv2.imshow('YOLO-Pose Webcam', vis_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        cap.release()
        cv2.destroyAllWindows()
    
    def export_keypoints(self, persons, output_file):
        import json
        import numpy as np
        
        def convert_to_serializable(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.float32):
                return float(obj)
            elif isinstance(obj, np.int64):
                return int(obj)
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            else:
                return obj
        
        output_data = {
            'persons': convert_to_serializable(persons),
            'frame_info': {
                'width': self.postprocessor.image_width if self.postprocessor else 0,
                'height': self.postprocessor.image_height if self.postprocessor else 0
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Keypoints exported to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='YOLO-Pose Human Pose Estimation')
    parser.add_argument('--model', type=str, default='yolov8n-pose.pt', help='Path to YOLO-Pose model')
    parser.add_argument('--input', type=str, help='Input image/video path')
    parser.add_argument('--output', type=str, help='Output path')
    parser.add_argument('--webcam', action='store_true', help='Use webcam input')
    parser.add_argument('--camera', type=int, default=0, help='Webcam index')
    parser.add_argument('--device', type=str, default='auto', help='Device (cpu/cuda/auto)')
    
    args = parser.parse_args()
    
    app = PoseEstimationApp(model_path=args.model, device=args.device)
    
    if args.webcam:
        app.process_webcam(camera_index=args.camera)
    elif args.input:
        if args.input.endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            persons, vis_frame = app.process_image(args.input, args.output)
            if vis_frame is not None:
                cv2.imshow('Result', vis_frame)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            
            if persons:
                print(f"Detected {len(persons)} person(s)")
                for i, person in enumerate(persons):
                    print(f"\nPerson {i+1}:")
                    print(f"  BBox: {person['bbox']}")
                    print(f"  Keypoints: {len(person['keypoints'])} detected")
                    for part, points in person['body_parts'].items():
                        print(f"  {part}: {len(points)} points")
        else:
            app.process_video(args.input, args.output, show=True)
    else:
        print("Please provide either --input or --webcam argument")

if __name__ == '__main__':
    main()