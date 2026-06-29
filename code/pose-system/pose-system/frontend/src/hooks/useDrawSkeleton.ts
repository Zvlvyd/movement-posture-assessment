import { useCallback } from "react";

/**
 * COCO 17 keypoint skeleton connections.
 * Indices: 0:nose 1:l_eye 2:r_eye 3:l_ear 4:r_ear
 *   5:l_shoulder 6:r_shoulder 7:l_elbow 8:r_elbow 9:l_wrist 10:r_wrist
 *   11:l_hip 12:r_hip 13:l_knee 14:r_knee 15:l_ankle 16:r_ankle
 */
const FULL_SKELETON: [number, number][] = [
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10], // arms
  [5, 11], [6, 12], [11, 12],               // torso
  [11, 13], [13, 15], [12, 14], [14, 16],   // legs
];

const SKELETON_WITH_FACE: [number, number][] = [
  [0, 1], [0, 2], [1, 3], [2, 4],           // face
  ...FULL_SKELETON,
];

/** Color palette for angle status */
const STATUS_COLORS: Record<string, string> = {
  good: "#52c41a",
  close: "#faad14",
  warning: "#fa8c16",
  bad: "#f5222d",
  unknown: "#aaaaaa",
};

interface DrawSkeletonOptions {
  /** Whether to draw face keypoints (default: false) */
  showFace?: boolean;
  /** Color mode: 'rainbow' (each limb different) or 'status' (default: 'rainbow') */
  colorMode?: "rainbow" | "status";
  /** Per-keypoint status strings for status color mode */
  statuses?: string[];
  /** Optional standard keypoints to draw as dashed overlay */
  standardKeypoints?: number[][];
  /** Keypoint labels to draw (empty = no labels) */
  labels?: string[];
}

const RAINBOW = ["#ff4d4f", "#ff7a45", "#ffa940", "#ffec3d", "#bae637", "#73d13d", "#36cfc9", "#40a9ff", "#597ef7", "#9254de"];

/**
 * Hook that returns a stable `drawSkeleton` callback for canvas rendering.
 *
 * Usage:
 *   const drawSkeleton = useDrawSkeleton({ showFace: true, colorMode: 'status' });
 *   // In your WebSocket onmessage or render loop:
 *   drawSkeleton(canvas, keypoints, width, height);
 */
export function useDrawSkeleton(options: DrawSkeletonOptions = {}) {
  const {
    showFace = false,
    colorMode = "rainbow",
    statuses,
    standardKeypoints,
    labels,
  } = options;

  const skeleton = showFace ? SKELETON_WITH_FACE : FULL_SKELETON;

  const draw = useCallback(
    (
      canvas: HTMLCanvasElement,
      keypoints: number[][],
      width: number,
      height: number
    ) => {
      const ctx = canvas.getContext("2d");
      if (!ctx || !keypoints || keypoints.length === 0) return;

      // Match canvas size to display size
      if (canvas.width !== width) canvas.width = width;
      if (canvas.height !== height) canvas.height = height;

      ctx.clearRect(0, 0, width, height);

      // Scale keypoints to canvas size
      const scaleX = width / 640;
      const scaleY = height / 480;
      const scaled = keypoints.map(([x, y]) => [x * scaleX, y * scaleY]);

      // ── Standard skeleton overlay (dashed gray) ──
      if (standardKeypoints && standardKeypoints.length > 0) {
        const stdScaled = standardKeypoints.map(([x, y]) => [x * scaleX, y * scaleY]);
        ctx.strokeStyle = "rgba(180, 180, 180, 0.4)";
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
        for (const [i, j] of skeleton) {
          if (i < stdScaled.length && j < stdScaled.length) {
            const [x1, y1] = stdScaled[i];
            const [x2, y2] = stdScaled[j];
            if (x1 > 0 && y1 > 0 && x2 > 0 && y2 > 0) {
              ctx.beginPath();
              ctx.moveTo(x1, y1);
              ctx.lineTo(x2, y2);
              ctx.stroke();
            }
          }
        }
        ctx.setLineDash([]);
      }

      // ── User skeleton ──
      ctx.lineWidth = 3;
      ctx.lineCap = "round";

      for (let idx = 0; idx < skeleton.length; idx++) {
        const [i, j] = skeleton[idx];
        if (i >= scaled.length || j >= scaled.length) continue;
        const [x1, y1] = scaled[i];
        const [x2, y2] = scaled[j];
        if (x1 <= 0 && y1 <= 0) continue;
        if (x2 <= 0 && y2 <= 0) continue;

        if (colorMode === "status" && statuses) {
          ctx.strokeStyle = STATUS_COLORS[statuses[i]] || STATUS_COLORS.unknown;
        } else {
          ctx.strokeStyle = RAINBOW[idx % RAINBOW.length];
        }

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      // ── Joint dots ──
      for (let i = 0; i < scaled.length; i++) {
        const [x, y] = scaled[i];
        if (x <= 0 && y <= 0) continue;

        const color =
          colorMode === "status" && statuses
            ? STATUS_COLORS[statuses[i]] || STATUS_COLORS.unknown
            : RAINBOW[i % RAINBOW.length];

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fill();

        // White border
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Optional label
        if (labels && labels[i]) {
          ctx.fillStyle = "rgba(255,255,255,0.85)";
          ctx.font = "10px sans-serif";
          ctx.textAlign = "center";
          ctx.fillText(labels[i], x, y - 10);
        }
      }
    },
    [skeleton, colorMode, statuses, standardKeypoints, labels]
  );

  return draw;
}
