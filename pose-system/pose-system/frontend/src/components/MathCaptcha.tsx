import { useState, useCallback, useRef } from 'react';
import { Input, Button, Space } from 'antd';
import { SafetyCertificateOutlined } from '@ant-design/icons';

/**
 * 数学加法验证码展示组件（纯展示，不含校验逻辑）。
 *
 * 与 useCaptchaRule hook 配合使用：
 * ```
 * const { a, b, validator, refresh } = useCaptchaRule();
 * <Form.Item name="captcha" rules={[{ required: true }, { validator }]}>
 *   <MathCaptcha a={a} b={b} onRefresh={refresh} />
 * </Form.Item>
 * ```
 */
export default function MathCaptcha({
  value,
  onChange,
  a,
  b,
  onRefresh,
}: {
  value?: string;
  onChange?: (value: string) => void;
  a: number;
  b: number;
  onRefresh: () => void;
}) {
  return (
    <Space.Compact style={{ width: '100%' }}>
      <Input
        prefix={<SafetyCertificateOutlined />}
        placeholder={`${a} + ${b} = ?`}
        value={value}
        onChange={e => onChange?.(e.target.value)}
        style={{ flex: 1 }}
        aria-label={`验证码：${a} 加 ${b} 等于多少？`}
        inputMode="numeric"
      />
      <Button onClick={onRefresh} type="link" size="small" aria-label="换一个验证码">
        换一个
      </Button>
    </Space.Compact>
  );
}

/**
 * 验证码业务逻辑 Hook。
 *
 * 管理验证码题目生成与校验，返回：
 * - a, b: 当前题目数字
 * - validator: Ant Design Form validator 函数
 * - refresh: 刷新题目
 */
export function useCaptchaRule() {
  const [captcha, setCaptcha] = useState(makeCaptcha);

  // 用 ref 保持最新答案，避免 validator 闭包过期
  const answerRef = useRef(captcha.answer);
  answerRef.current = captcha.answer;

  const refresh = useCallback(() => setCaptcha(makeCaptcha()), []);

  const validator = useCallback((_: any, value: string) => {
    if (!value) return Promise.reject(new Error('请输入验证码'));
    if (Number(value) === answerRef.current) return Promise.resolve();
    setCaptcha(makeCaptcha());
    return Promise.reject(new Error('验证码错误，请重试'));
  }, []);

  return { a: captcha.a, b: captcha.b, validator, refresh } as const;
}

// ── 内部工具 ──────────────────────────────────────────────

interface CaptchaState {
  a: number;
  b: number;
  answer: number;
}

function makeCaptcha(): CaptchaState {
  const a = Math.floor(Math.random() * 4) + 1; // 1~4
  const b = Math.floor(Math.random() * 4) + 1; // 1~4, 和最大=8，保证个位数
  return { a, b, answer: a + b };
}
