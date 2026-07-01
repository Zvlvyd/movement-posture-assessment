import React, { useRef, useEffect } from "react";

// COCO 17 keypoint indices
// 0:nose 1:left_eye 2:right_eye 3:left_ear 4:right_ear
// 5:left_shoulder 6:right_shoulder 7:left_elbow 8:right_elbow
// 9:left_wrist 10:right_wrist 11:left_hip 12:right_hip
// 13:left_knee 14:right_knee 15:left_ankle 16:right_ankle

// Complete COCO 17 skeleton connections
const SKELETON: [number, number][] = [
  // Face
  [0, 1], [0, 2], [1, 3], [2, 4],
  // Arms
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  // Torso
  [5, 11], [6, 12], [11, 12],
  // Legs
  [11, 13], [13, 15], [12, 14], [14, 16],
];

// Keypoint labels for annotation
const KP_LABELS: string[] = [
  "鼻", "左眼", "右眼", "左耳", "右耳",
  "左肩", "右肩", "左肘", "右肘",
  "左腕", "右腕", "左髋", "右髋",
  "左膝", "右膝", "左踝", "右踝",
];

const SKELETON_COLORS: Record<string, string> = {
  good: "#52c41a",
  close: "#faad14",
  warning: "#fa8c16",
  bad: "#f5222d",
  unknown: "#d9d9d9",
};

interface Props {
  width?: number;
  height?: number;
  userKeypoints?: number[][] | null;
  confidences?: number[];
  statuses?: string[];
  showStandard?: boolean;
  standardKeypoints?: number[][] | null;
  /** 可选：从 video 元素动态推导画布尺寸 */
  videoRef?: React.RefObject<HTMLVideoElement | null>;
  /** YOLO 推理时帧的实际宽度（用于坐标缩放） */
  frameWidth?: number;
  /** YOLO 推理时帧的实际高度（用于坐标缩放） */
  frameHeight?: number;
}

/** 最小置信度阈值，低于此值的关键点不绘制（与后端 0.15 对齐） */
const MIN_CONFIDENCE = 0.15;

const SkeletonOverlay: React.FC<Props> = ({
  width: explicitWidth, height: explicitHeight,
  userKeypoints, confidences, statuses,
  showStandard, standardKeypoints,
  videoRef, frameWidth = 640, frameHeight = 480,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // 从 video 元素推导尺寸，回退到显式 props
  const videoEl = videoRef?.current;
  const width = explicitWidth ?? (videoEl ? videoEl.getBoundingClientRect().width : 0);
  const height = explicitHeight ?? (videoEl ? videoEl.getBoundingClientRect().height : 0);

  // 坐标缩放：从 YOLO 帧空间 → 显示画布空间
  const scaleX = frameWidth > 0 ? width / frameWidth : 1;
  const scaleY = frameHeight > 0 ? height / frameHeight : 1;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);
    if (width === 0 || height === 0) return;

    // 将帧坐标缩放到画布坐标
    const sx = (x: number) => x * scaleX;
    const sy = (y: number) => y * scaleY;

    // ── Standard skeleton (dashed gray) ──
    if (showStandard && standardKeypoints) {
      ctx.strokeStyle = "rgba(180, 180, 180, 0.4)";
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      for (const [i, j] of SKELETON) {
        if (i < standardKeypoints.length && j < standardKeypoints.length) {
          const [x1, y1] = standardKeypoints[i];
          const [x2, y2] = standardKeypoints[j];
          if (x1 > 0 && y1 > 0 && x2 > 0 && y2 > 0) {
            ctx.beginPath();
            ctx.moveTo(sx(x1), sy(y1));
            ctx.lineTo(sx(x2), sy(y2));
            ctx.stroke();
          }
        }
      }
      ctx.setLineDash([]);
      ctx.fillStyle = "rgba(180, 180, 180, 0.4)";
      for (const kp of standardKeypoints) {
        const [x, y] = kp;
        if (x > 0 && y > 0) {
          ctx.beginPath();
          ctx.arc(sx(x), sy(y), 3, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }

    // ── User skeleton ──
    if (userKeypoints) {
      // 辅助函数：检查关键点是否满足置信度阈值
      const isValid = (idx: number) =>
        idx < userKeypoints.length &&
        userKeypoints[idx][0] > 0 &&
        userKeypoints[idx][1] > 0 &&
        (!confidences || confidences[idx] >= MIN_CONFIDENCE);

      // Lines — 两端点都需通过置信度检查
      ctx.lineWidth = 3;
      ctx.lineCap = "round";
      for (const [i, j] of SKELETON) {
        if (isValid(i) && isValid(j)) {
          const [x1, y1] = userKeypoints[i];
          const [x2, y2] = userKeypoints[j];
          const s = statuses?.[i] || "unknown";
          ctx.strokeStyle = SKELETON_COLORS[s] || SKELETON_COLORS.unknown;
          ctx.beginPath();
          ctx.moveTo(sx(x1), sy(y1));
          ctx.lineTo(sx(x2), sy(y2));
          ctx.stroke();
        }
      }

      // Joint dots — 只绘制通过置信度检查的关键点
      for (let i = 0; i < userKeypoints.length; i++) {
        if (!isValid(i)) continue;
        const [x, y] = userKeypoints[i];
        const s = statuses?.[i] || "unknown";
        const color = SKELETON_COLORS[s] || SKELETON_COLORS.unknown;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(sx(x), sy(y), 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Label every keypoint with small text
        ctx.fillStyle = "rgba(255,255,255,0.85)";
        ctx.font = "9px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(KP_LABELS[i] || String(i), sx(x), sy(y) - 8);
      }
    }
  }, [width, height, scaleX, scaleY, userKeypoints, confidences, statuses, showStandard, standardKeypoints, videoRef]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }}
    />
  );
};

export default SkeletonOverlay;
