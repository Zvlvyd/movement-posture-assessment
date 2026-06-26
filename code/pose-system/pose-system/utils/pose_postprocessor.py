import cv2
import numpy as np
from scipy.spatial import distance

class PosePostProcessor:
    def __init__(self, image_width, image_height):
        self.image_width = image_width
        self.image_height = image_height
        
        self.default_limb_lengths = {
            'arm': 0.25,  
            'leg': 0.3,   
            'torso': 0.3  
        }
        
        self.skeleton_constraints = {
            'shoulder_width': (0.15, 0.25),  
            'arm_length_ratio': (0.4, 0.6),  
            'leg_length_ratio': (0.45, 0.65),  
            'torso_height_ratio': (0.25, 0.4)  
        }
    
    def filter_low_confidence_keypoints(self, persons, confidence_threshold=0.1):
        filtered_persons = []
        for person in persons:
            filtered_kp = [kp for kp in person['keypoints'] if kp['confidence'] >= confidence_threshold]
            person['keypoints'] = filtered_kp
            if len(filtered_kp) >= 5:
                filtered_persons.append(person)
        return filtered_persons
    
    def detect_truncation(self, person, margin=20):
        truncation_info = {
            'left': False,
            'right': False,
            'top': False,
            'bottom': False,
            'severity': 'none'
        }
        
        if person['bbox'] is not None:
            x1, y1, x2, y2 = person['bbox']
            
            if x1 < margin:
                truncation_info['left'] = True
            if x2 > self.image_width - margin:
                truncation_info['right'] = True
            if y1 < margin:
                truncation_info['top'] = True
            if y2 > self.image_height - margin:
                truncation_info['bottom'] = True
            
            truncated_sides = sum([truncation_info['left'], truncation_info['right'], 
                                  truncation_info['top'], truncation_info['bottom']])
            
            if truncated_sides == 1:
                truncation_info['severity'] = 'mild'
            elif truncated_sides == 2:
                truncation_info['severity'] = 'moderate'
            elif truncated_sides >= 3:
                truncation_info['severity'] = 'severe'
        
        person['truncation_info'] = truncation_info
        return person
    
    def estimate_missing_keypoints(self, person):
        keypoints = person['keypoints']
        kp_dict = {kp['id']: kp for kp in keypoints}
        
        def get_kp(id):
            return kp_dict.get(id, None)
        
        nose = get_kp(0)
        left_shoulder, right_shoulder = get_kp(5), get_kp(6)
        left_hip, right_hip = get_kp(11), get_kp(12)
        
        if left_shoulder and right_shoulder:
            shoulder_center_x = (left_shoulder['x'] + right_shoulder['x']) / 2
            shoulder_center_y = (left_shoulder['y'] + right_shoulder['y']) / 2
            
            if not nose:
                estimated_nose = {
                    'id': 0, 'label': 'nose',
                    'x': shoulder_center_x,
                    'y': shoulder_center_y - 60,
                    'confidence': 0.7
                }
                keypoints.append(estimated_nose)
                kp_dict[0] = estimated_nose
        
        if left_shoulder and left_hip:
            torso_length = np.sqrt((left_shoulder['x'] - left_hip['x'])**2 + 
                                   (left_shoulder['y'] - left_hip['y'])**2)
            
            if not get_kp(7):
                ratio = 0.4
                est_x = left_shoulder['x'] + (left_hip['x'] - left_shoulder['x']) * ratio
                est_y = left_shoulder['y'] + (left_hip['y'] - left_shoulder['y']) * ratio
                keypoints.append({'id': 7, 'label': 'left_elbow', 'x': est_x, 'y': est_y, 'confidence': 0.6})
            
            if not get_kp(9):
                ratio = 0.8
                est_x = left_shoulder['x'] + (left_hip['x'] - left_shoulder['x']) * ratio
                est_y = left_shoulder['y'] + (left_hip['y'] - left_shoulder['y']) * ratio
                keypoints.append({'id': 9, 'label': 'left_wrist', 'x': est_x, 'y': est_y, 'confidence': 0.5})
        
        if right_shoulder and right_hip:
            if not get_kp(8):
                ratio = 0.4
                est_x = right_shoulder['x'] + (right_hip['x'] - right_shoulder['x']) * ratio
                est_y = right_shoulder['y'] + (right_hip['y'] - right_shoulder['y']) * ratio
                keypoints.append({'id': 8, 'label': 'right_elbow', 'x': est_x, 'y': est_y, 'confidence': 0.6})
            
            if not get_kp(10):
                ratio = 0.8
                est_x = right_shoulder['x'] + (right_hip['x'] - right_shoulder['x']) * ratio
                est_y = right_shoulder['y'] + (right_hip['y'] - right_shoulder['y']) * ratio
                keypoints.append({'id': 10, 'label': 'right_wrist', 'x': est_x, 'y': est_y, 'confidence': 0.5})
        
        if left_hip and not get_kp(13):
            if get_kp(15):
                est_x = (left_hip['x'] + get_kp(15)['x']) / 2
                est_y = (left_hip['y'] + get_kp(15)['y']) / 2
                keypoints.append({'id': 13, 'label': 'left_knee', 'x': est_x, 'y': est_y, 'confidence': 0.6})
            else:
                est_y = left_hip['y'] + 80
                keypoints.append({'id': 13, 'label': 'left_knee', 'x': left_hip['x'], 'y': est_y, 'confidence': 0.5})
        
        if right_hip and not get_kp(14):
            if get_kp(16):
                est_x = (right_hip['x'] + get_kp(16)['x']) / 2
                est_y = (right_hip['y'] + get_kp(16)['y']) / 2
                keypoints.append({'id': 14, 'label': 'right_knee', 'x': est_x, 'y': est_y, 'confidence': 0.6})
            else:
                est_y = right_hip['y'] + 80
                keypoints.append({'id': 14, 'label': 'right_knee', 'x': right_hip['x'], 'y': est_y, 'confidence': 0.5})
        
        person['keypoints'] = sorted(keypoints, key=lambda x: x['id'])
        return person
    
    def handle_occlusion(self, person):
        visible_count = sum(1 for kp in person['keypoints'] if kp['confidence'] > 0.3)
        total_kp = len(person['keypoints'])
        
        if visible_count < total_kp * 0.5:
            person['occlusion_severity'] = 'heavy'
        elif visible_count < total_kp * 0.75:
            person['occlusion_severity'] = 'moderate'
        else:
            person['occlusion_severity'] = 'light'
        
        if person['occlusion_severity'] != 'heavy':
            person = self.estimate_missing_keypoints(person)
        
        return person
    
    def sort_persons_by_proximity(self, persons, frame_center=None):
        if frame_center is None:
            frame_center = (self.image_width // 2, self.image_height // 2)
        
        for person in persons:
            if person['bbox'] is not None:
                x1, y1, x2, y2 = person['bbox']
                bbox_center = ((x1 + x2) // 2, (y1 + y2) // 2)
                person['distance_to_center'] = distance.euclidean(bbox_center, frame_center)
        
        sorted_persons = sorted(persons, key=lambda p: p.get('distance_to_center', float('inf')))
        return sorted_persons
    
    def smooth_keypoints(self, person, prev_person=None, alpha=0.3):
        if prev_person is None:
            return person
        
        current_kp_dict = {kp['id']: kp for kp in person['keypoints']}
        prev_kp_dict = {kp['id']: kp for kp in prev_person.get('keypoints', [])}
        
        for kp in person['keypoints']:
            prev_kp = prev_kp_dict.get(kp['id'])
            if prev_kp:
                kp['x'] = alpha * kp['x'] + (1 - alpha) * prev_kp['x']
                kp['y'] = alpha * kp['y'] + (1 - alpha) * prev_kp['y']
        
        return person
    
    def process(self, persons, prev_persons=None):
        persons = self.filter_low_confidence_keypoints(persons)
        
        for i, person in enumerate(persons):
            person = self.detect_truncation(person)
            person = self.handle_occlusion(person)
            
            if prev_persons and i < len(prev_persons):
                person = self.smooth_keypoints(person, prev_persons[i])
            
            persons[i] = person
        
        persons = self.sort_persons_by_proximity(persons)
        
        return persons