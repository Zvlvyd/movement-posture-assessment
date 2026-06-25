import React, { useRef, useEffect } from 'react';

// COCO 17 keypoint skeleton connections
const SKELETON: [number, number][] = [
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],  // arms
  [5, 11], [6, 12], [11, 12],                  // shoulders-hips
  [11, 13], [13, 15], [12, 14], [14, 16],       // legs
];

const SKELETON_COLORS: Record<string, string> = {
  good: '#52c41a',     // green
  close: '#faad14',    // yellow
  warning: '#fa8c16',  // orange
  bad: '#f5222d',      // red
  unknown: '#d9d9d9',  // gray
};

interface Props {
  width: number;
  height: number;
  userKeypoints?: number[][] | null;  // 17x2
  statuses?: string[];                // per-keypoint status
  showStandard?: boolean;
  standardKeypoints?: number[][] | null;  // reference skeleton
}

const SkeletonOverlay: React.FC<Props> = ({
  width, height,
  userKeypoints, statuses,
  showStandard, standardKeypoints,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);

    // Draw standard skeleton (semi-transparent gray)
    if (showStandard && standardKeypoints) {
      ctx.strokeStyle = 'rgba(180, 180, 180, 0.5)';
      ctx.lineWidth = 3;
      ctx.setLineDash([6, 4]);
      for (const [i, j] of SKELETON) {
        if (i < standardKeypoints.length && j < standardKeypoints.length) {
          const [x1, y1] = standardKeypoints[i];
          const [x2, y2] = standardKeypoints[j];
          if (x1 > 0 && y1 > 0 && x2 > 0 && y2 > 0) {
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();
          }
        }
      }
      // Standard joints as semi-transparent dots
      ctx.fillStyle = 'rgba(180, 180, 180, 0.5)';
      for (const kp of standardKeypoints) {
        const [x, y] = kp;
        if (x > 0 && y > 0) {
          ctx.beginPath();
          ctx.arc(x, y, 4, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      ctx.setLineDash([]);
    }

    // Draw user skeleton
    if (userKeypoints) {
      ctx.lineWidth = 3;
      for (const [i, j] of SKELETON) {
        if (i < userKeypoints.length && j < userKeypoints.length) {
          const [x1, y1] = userKeypoints[i];
          const [x2, y2] = userKeypoints[j];
          if (x1 > 0 && y1 > 0 && x2 > 0 && y2 > 0) {
            const status = statuses?.[i] || 'unknown';
            ctx.strokeStyle = SKELETON_COLORS[status] || SKELETON_COLORS.unknown;
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();
          }
        }
      }
      // User joints
      for (let i = 0; i < userKeypoints.length; i++) {
        const [x, y] = userKeypoints[i];
        if (x > 0 && y > 0) {
          const status = statuses?.[i] || 'unknown';
          ctx.fillStyle = SKELETON_COLORS[status] || SKELETON_COLORS.unknown;
          ctx.beginPath();
          ctx.arc(x, y, 5, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = '#fff';
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
    }
  }, [width, height, userKeypoints, statuses, showStandard, standardKeypoints]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
    />
  );
};

export default SkeletonOverlay;
