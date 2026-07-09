# 测试脚本

## 运行环境

```bash
conda activate dl
```

## test_fms_video.py — FMS 本地视频离线测试

用本地视频文件测试 FMS 评估流水线的分析能力，不依赖 WebSocket / 数据库。

```bash
# 基本用法（从项目根目录运行）
python tests/test_fms_video.py -i 视频.mp4

# 完整参数
python tests/test_fms_video.py \
  --input 视频.mp4 \
  --output tests/output/标注结果.mp4 \
  --json tests/output/分析报告.json \
  --model yolov8n-pose.pt \
  --device cpu \
  --skip 2 \
  --show
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `-i / --input` | (必需) | 输入视频路径 |
| `-o / --output` | `输入文件名_fms_result.mp4` | 输出标注视频 |
| `-j / --json` | `输入文件名_fms_result.json` | 输出 JSON 报告 |
| `-m / --model` | `yolov8n-pose.pt` | YOLO 模型路径 |
| `-d / --device` | `auto` | 推理设备 (cpu/cuda/auto) |
| `--skip` | `2` | 跳帧间隔（1=每帧检测） |
| `--show` | (无) | 实时显示处理画面 |

## test_ws.py — WebSocket 连接测试

测试 WebSocket 实时评估的连接。

## output/ 目录

存放测试脚本的输出文件（标注视频、JSON 报告等）。
