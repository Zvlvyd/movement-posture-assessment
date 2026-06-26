import { useEffect, useRef, useState } from 'react';
import { PictureOutlined, VideoCameraOutlined } from '@ant-design/icons';

/** 动作示范 + 图片/视频占位 + 倒计时叠加层 */
interface Props {
  /** 评估项名称（如"颈部活动度评估"） */
  movementName: string;
  /** 当前步骤名称（如"颈部左旋"） */
  stepName?: string;
  /** 当前步骤引导语 */
  instruction: string;
  /** 步骤序号（1-based） */
  stepIndex?: number;
  /** 总步骤数 */
  totalSteps?: number;
  /** 预计耗时 */
  durationHint?: string;
  /** 倒计时秒数，0 表示不显示 */
  countdown: number;
  /** 倒计时结束回调 */
  onCountdownEnd?: () => void;
  /** 示范图片 URL（留空使用占位） */
  imageUrl?: string;
  /** 示范视频 URL（留空使用占位） */
  videoUrl?: string;
  /** 过渡提示（步骤完成后的引导） */
  transitionHint?: string;
}

/** 通用站姿关节坐标 */
const DEFAULT_POSE = {
  joints: [[100,35],[100,55],[100,80],[100,110],[100,140],[100,80],[85,100],[70,120],[100,80],[115,100],[130,120]],
  connections: [[0,1],[1,2],[2,3],[3,4],[2,5],[5,6],[6,7],[2,8],[8,9],[9,10]] as [number,number][],
  label: '',
};

const POSE_COORDS: Record<string, { joints: [number,number][]; connections: [number,number][]; label: string }> = {
  '颈部': { joints:[[100,35],[100,55],[80,65],[60,75],[100,55],[120,65],[140,75],[100,80],[100,110],[100,140],[100,80],[85,100],[70,120],[100,80],[115,100],[130,120]], connections:[[0,1],[1,2],[2,3],[1,4],[4,5],[5,6],[1,7],[7,8],[8,9],[1,10],[10,11],[11,12],[1,13],[13,14],[14,15]], label:'颈部旋转/侧屈' },
  '肩关节': { joints:[[100,35],[100,55],[100,80],[100,110],[100,140],[100,80],[80,65],[60,55],[100,80],[120,65],[140,55],[100,80],[80,110],[60,130],[100,80],[120,110],[140,130]], connections:[[0,1],[1,2],[2,3],[3,4],[2,5],[5,6],[6,7],[2,8],[8,9],[9,10],[2,11],[11,12],[12,13],[2,14],[14,15],[15,16]], label:'双臂前举/背后触手' },
  '脊柱': { joints:[[100,35],[100,55],[100,80],[85,115],[60,150],[100,80],[80,115],[60,150],[100,80],[115,115],[140,150],[100,80],[120,115],[150,150]], connections:[[0,1],[1,2],[2,3],[3,4],[2,5],[5,6],[6,7],[2,8],[8,9],[9,10],[2,11],[11,12],[12,13]], label:'体前屈/侧屈' },
  '深蹲': { joints:[[100,25],[100,45],[100,70],[85,105],[70,140],[100,105],[115,105],[130,140],[100,45],[85,60],[100,45],[115,60],[100,70],[80,90],[100,70],[120,90]], connections:[[0,1],[1,2],[2,3],[3,4],[2,5],[5,6],[6,7],[1,8],[8,9],[1,10],[10,11],[2,12],[12,13],[2,14],[14,15]], label:'下蹲至最低点' },
  '髋关节': { joints:[[100,35],[100,55],[100,80],[100,110],[100,140],[100,80],[85,100],[70,90],[100,80],[80,100],[100,80],[115,100],[120,90],[100,80],[130,100]], connections:[[0,1],[1,2],[2,3],[3,4],[2,5],[5,6],[6,7],[2,8],[2,9],[2,10],[10,11],[11,12],[2,13]], label:'抬膝/外展' },
};

function pickPose(name: string) {
  for (const [key, pose] of Object.entries(POSE_COORDS)) {
    if (name.includes(key)) return pose;
  }
  return DEFAULT_POSE;
}

export default function MovementDemo({
  movementName, stepName, instruction, stepIndex, totalSteps,
  durationHint, countdown, onCountdownEnd,
  imageUrl, videoUrl, transitionHint,
}: Props) {
  const [cd, setCd] = useState(countdown);
  const timerRef = useRef<number>(0);
  const pose = pickPose(movementName);
  const svgSize = 220;

  useEffect(() => {
    setCd(countdown);
    if (countdown <= 0) return;
    timerRef.current = window.setInterval(() => {
      setCd(prev => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          onCountdownEnd?.();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, [countdown, onCountdownEnd]);

  return (
    <div className="demo-enter" style={{ textAlign: 'center', padding: '12px 0' }}>
      {/* ── 标题行 ──────────────────────────── */}
      <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 2, color: '#1a1a2e' }}>
        {movementName}
      </div>
      {stepName && (
        <div style={{ fontSize: 14, color: '#4ECDC4', fontWeight: 600, marginBottom: 4 }}>
          当前步骤：{stepName}
          {stepIndex && totalSteps ? ` (${stepIndex}/${totalSteps})` : ''}
        </div>
      )}
      <div style={{ fontSize: 13, color: '#888', marginBottom: 8 }}>{pose.label}</div>

      {/* ── 示范区域（简笔画 + 图片/视频占位） ── */}
      <div style={{
        display: 'flex', gap: 12, justifyContent: 'center', alignItems: 'stretch',
        marginBottom: 12, flexWrap: 'wrap',
      }}>
        {/* 图片占位 */}
        <div style={{
          width: svgSize, minHeight: svgSize,
          background: '#f5f5f5', borderRadius: 16,
          border: '1px dashed #d9d9d9',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          color: '#bbb', fontSize: 12,
        }}>
          {imageUrl ? (
            <img src={imageUrl} alt={stepName || movementName} style={{ width: '100%', height: '100%', borderRadius: 16, objectFit: 'cover' }} />
          ) : (
            <>
              <PictureOutlined style={{ fontSize: 36, marginBottom: 8 }} />
              <span>示范图片</span>
              <span style={{ fontSize: 10 }}>（待补充）</span>
            </>
          )}
        </div>

        {/* 视频占位 */}
        <div style={{
          width: svgSize, minHeight: svgSize,
          background: '#f5f5f5', borderRadius: 16,
          border: '1px dashed #d9d9d9',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          color: '#bbb', fontSize: 12,
        }}>
          {videoUrl ? (
            <video src={videoUrl} controls muted style={{ width: '100%', height: '100%', borderRadius: 16, objectFit: 'cover' }} />
          ) : (
            <>
              <VideoCameraOutlined style={{ fontSize: 36, marginBottom: 8 }} />
              <span>示范视频</span>
              <span style={{ fontSize: 10 }}>（待补充）</span>
            </>
          )}
        </div>
      </div>

      {/* ── 倒计时叠加在示范区域上方（独立展示）── */}
      {cd > 0 && (
        <div style={{
          width: '100%', maxWidth: svgSize * 2 + 12, margin: '-80px auto 16px',
          height: 80, display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0,0,0,0.45)', borderRadius: 16, position: 'relative', zIndex: 2,
        }}>
          <span className="countdown-number" style={{
            fontSize: 64, fontWeight: 900, color: '#fff',
            textShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}>
            {cd}
          </span>
        </div>
      )}

      {/* ── 当前步骤引导语 ── */}
      <div style={{
        background: '#e6f7ff', border: '1px solid #91d5ff',
        borderRadius: 8, padding: '10px 16px', marginBottom: 8,
        fontSize: 14, color: '#0050b3', lineHeight: 1.6,
      }}>
        💡 {instruction}
      </div>

      {/* ── 过渡提示（步骤完成后显示） ── */}
      {transitionHint && (
        <div style={{
          background: '#fff7e6', border: '1px solid #ffd591',
          borderRadius: 8, padding: '8px 16px', marginBottom: 8,
          fontSize: 14, color: '#ad6800', fontWeight: 500,
          animation: 'fadeInUp 0.4s ease-out',
        }}>
          ⏭ {transitionHint}
        </div>
      )}

      {durationHint && (
        <div style={{ fontSize: 12, color: '#999' }}>
          预计耗时：{durationHint}
        </div>
      )}
    </div>
  );
}
