import cv2
import numpy as np
import base64
from typing import List, Dict, Optional, Tuple
from ultralytics import YOLO

class YOLOPoseEngine:
    _instance = None
    _model = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_path: str = "yolov8n-pose.pt", device: str = "auto"):
        if self._model is not None:
            return
        if device == "auto":
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.model_path = model_path
        print(f"Loading YOLO-Pose model: {model_path} on {device}")
        self._model = YOLO(model_path)
        if device != "cpu":
            self._model.to(device)
        self.input_size = 640
        print("YOLO-Pose model loaded")

    @property
    def model(self):
        return self._model

    def process_frame(self, frame: np.ndarray) -> Tuple[List[Dict], Optional[np.ndarray]]:
        results = self.model(frame, verbose=False)
        persons = []
        if results and len(results) > 0:
            r = results[0]
            if r.keypoints is not None and r.keypoints.data is not None:
                kp_data = r.keypoints.data.cpu().numpy()
                boxes = r.boxes
                for i, kps in enumerate(kp_data):
                    person = {
                        "keypoints": kps[:, :2].tolist(),
                        "confidences": kps[:, 2].tolist() if kps.shape[1] >= 3 else [1.0] * len(kps),
                        "bbox": boxes.xyxy[i].cpu().numpy().tolist() if boxes is not None and i < len(boxes) else None,
                    }
                    persons.append(person)
        return persons, results

    def process_base64_frame(self, b64_str: str) -> Tuple[List[Dict], Optional[np.ndarray]]:
        try:
            img_data = base64.b64decode(b64_str.split(",")[-1] if "," in b64_str else b64_str)
            np_arr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None:
                return [], None
            return self.process_frame(frame)
        except Exception as e:
            print(f"Error processing base64 frame: {e}")
            return [], None

    def draw_keypoints(self, frame: np.ndarray, persons: List[Dict]) -> np.ndarray:
        vis = frame.copy()
        for person in persons:
            kps = np.array(person["keypoints"])
            confs = person.get("confidences", [1.0] * len(kps))
            # Draw skeleton connections
            skeleton = [
                (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
                (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)
            ]
            for (i, j) in skeleton:
                if i < len(kps) and j < len(kps) and confs[i] > 0.3 and confs[j] > 0.3:
                    pt1 = tuple(kps[i][:2].astype(int))
                    pt2 = tuple(kps[j][:2].astype(int))
                    cv2.line(vis, pt1, pt2, (0, 255, 0), 2)

            for i, (x, y) in enumerate(kps[:, :2].astype(int)):
                if confs[i] > 0.3:
                    cv2.circle(vis, (x, y), 4, (0, 0, 255), -1)
                    cv2.putText(vis, str(i), (x + 5, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        return vis
