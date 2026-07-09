/**
 * Web Audio API 提示音工具
 * 无需外部音频文件，纯代码合成提示音
 */

let audioCtx: AudioContext | null = null;

function ctx(): AudioContext {
  if (!audioCtx) audioCtx = new AudioContext();
  if (audioCtx.state === 'suspended') audioCtx.resume();
  return audioCtx;
}

/** 倒计时嘀声（短促中频） */
export function playCountdownBeep() {
  const c = ctx();
  const t = c.currentTime;
  const osc = c.createOscillator();
  const gain = c.createGain();
  osc.type = 'sine';
  osc.frequency.value = 880;
  gain.gain.setValueAtTime(0.25, t);
  gain.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
  osc.connect(gain); gain.connect(c.destination);
  osc.start(t); osc.stop(t + 0.12);
}

/** 开始提示音（上行 C5→E5 双音） */
export function playStartBeep() {
  const c = ctx();
  const t = c.currentTime;
  [523, 659].forEach((freq, i) => {
    const osc = c.createOscillator();
    const gain = c.createGain();
    osc.type = 'triangle';
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.3, t + i * 0.18);
    gain.gain.exponentialRampToValueAtTime(0.001, t + i * 0.18 + 0.25);
    osc.connect(gain); gain.connect(c.destination);
    osc.start(t + i * 0.18); osc.stop(t + i * 0.18 + 0.25);
  });
}

/** 完成提示音（下行 E5→C5 双音） */
export function playEndBeep() {
  const c = ctx();
  const t = c.currentTime;
  [659, 523].forEach((freq, i) => {
    const osc = c.createOscillator();
    const gain = c.createGain();
    osc.type = 'triangle';
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.3, t + i * 0.18);
    gain.gain.exponentialRampToValueAtTime(0.001, t + i * 0.18 + 0.25);
    osc.connect(gain); gain.connect(c.destination);
    osc.start(t + i * 0.18); osc.stop(t + i * 0.18 + 0.25);
  });
}

/** 全部完成提示音（上行 C5→E5→G5→C6 四音阶） */
export function playFinalBeep() {
  const c = ctx();
  const t = c.currentTime;
  [523, 659, 784, 1047].forEach((freq, i) => {
    const osc = c.createOscillator();
    const gain = c.createGain();
    osc.type = 'triangle';
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.3, t + i * 0.12);
    gain.gain.exponentialRampToValueAtTime(0.001, t + i * 0.12 + 0.3);
    osc.connect(gain); gain.connect(c.destination);
    osc.start(t + i * 0.12); osc.stop(t + i * 0.12 + 0.3);
  });
}
