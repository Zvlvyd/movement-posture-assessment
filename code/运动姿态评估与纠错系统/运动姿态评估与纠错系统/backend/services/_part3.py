class FMSState:
    def __init__(self):
        self.current_test_idx = 0
        self.frame_count = 0
        self.last_angles = {}
        self.tests = [
            {'idx': 0, 'name': '闭眼单腿站立', 'instruction': '闭上双眼，抬起单腿，保持平衡', 'status': 'pending', 'start_time': 0, 'data': None, 'score': 0, 'completed': False},
            {'idx': 1, 'name': '徒手过头深蹲', 'instruction': '双手举过头顶，做深蹲至最低点', 'status': 'pending', 'start_time': 0, 'data': None, 'score': 0, 'completed': False},
            {'idx': 2, 'name': '肩关节活动度', 'instruction': '一手从肩上、一手从腰后向背后靠拢', 'status': 'pending', 'start_time': 0, 'data': None, 'score': 0, 'completed': False},
            {'idx': 3, 'name': '平板支撑', 'instruction': '保持平板支撑姿势，尽量坚持', 'status': 'pending', 'start_time': 0, 'data': None, 'score': 0, 'completed': False},
            {'idx': 4, 'name': '弓步蹲对称', 'instruction': '分别做左右弓步蹲', 'status': 'pending', 'start_time': 0, 'left_score': 0, 'right_score': 0, 'data': None, 'score': 0, 'completed': False},
        ]

    def current_test(self):
        if self.current_test_idx < len(self.tests):
            return self.tests[self.current_test_idx]
        return None

    def reset(self):
        self.__init__()
