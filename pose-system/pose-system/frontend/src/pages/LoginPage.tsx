import { useState } from 'react';
import { Form, Input, Button, Card, message, Typography } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import MathCaptcha, { useCaptchaRule } from '../components/MathCaptcha';
import useRoleNavigate from '../hooks/useRoleNavigate';

function getErrorMessage(e: unknown): string {
  if (e && typeof e === 'object' && 'response' in (e as Record<string, unknown>)) {
    const resp = (e as { response?: { status?: number; data?: { detail?: string } } }).response;
    if (resp?.status === 401) return '用户名或密码错误';
    if (resp?.status === 403) return '账户已被禁用';
    if (resp?.status === 429) return '请求过于频繁，请稍后再试';
    if (resp?.data?.detail) return resp.data.detail;
    return '服务器错误，请稍后再试';
  }
  if (e instanceof TypeError && (e as TypeError).message === 'Failed to fetch') {
    return '网络连接失败，请检查网络';
  }
  return '登录失败，请稍后再试';
}

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const roleGo = useRoleNavigate();
  const login = useAuthStore(s => s.login);

  const { a, b, validator, refresh: refreshCaptcha } = useCaptchaRule();

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success('登录成功');
      roleGo();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
      refreshCaptcha();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f0f2f5', padding: 'clamp(12px, 3vw, 24px)' }}>
      <Card style={{ maxWidth: 400, width: '100%', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
        <Typography.Title level={3} style={{ textAlign: 'center', marginBottom: 24 }}>
          运动姿态评估与纠错系统
        </Typography.Title>
        <Form onFinish={onFinish} size="large">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" aria-label="用户名" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" aria-label="密码" />
          </Form.Item>
          <Form.Item
            name="captcha"
            rules={[{ required: true, message: '请输入验证码' }, { validator }]}
          >
            <MathCaptcha a={a} b={b} onRefresh={refreshCaptcha} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
          <div style={{ textAlign: 'center' }}>
            还没有账号？<Link to="/register">立即注册</Link>
          </div>
          <div style={{ textAlign: 'center', marginTop: 12 }}>
            <Typography.Text type="secondary">首次使用？</Typography.Text>
            <Button type="link" size="small" onClick={() => navigate('/register')}>
              开始运动能力评估
            </Button>
          </div>
        </Form>
      </Card>
    </div>
  );
}
