import { useEffect, useState } from 'react';
import { Card, Button, Typography, Statistic, List, Tag, message, Row, Col } from 'antd';
import { CheckCircleOutlined, TrophyOutlined } from '@ant-design/icons';
import { checkinApi } from '../services/api';

export default function CheckinPage() {
  const [status, setStatus] = useState<any>(null);
  const [badges, setBadges] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = () => {
    checkinApi.status().then(setStatus).catch(() => {});
    checkinApi.badges().then(setBadges).catch(() => {});
  };
  useEffect(() => { fetchData(); }, []);

  const handleCheckin = async () => {
    setLoading(true);
    try {
      const res = await checkinApi.checkin();
      message.success('打卡成功！');
      if (res.new_badges?.length) message.info();
      fetchData();
    } catch (e: any) {
      message.error(e.response?.data?.detail || '打卡失败');
    } finally { setLoading(false); }
  };

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <Card>
        <Statistic title="连续打卡" value={status?.streak_days || 0} suffix="天" prefix={<CheckCircleOutlined />} />
        <Button type="primary" size="large" block loading={loading} onClick={handleCheckin} style={{ marginTop: 16 }}>
          今日打卡
        </Button>
      </Card>
      <Card title="我的徽章" style={{ marginTop: 16 }}>
        {badges.length > 0 ? (
          <Row gutter={[8, 8]}>
            {badges.map((b: any) => (
              <Col key={b.type}><Tag color="gold" icon={<TrophyOutlined />}>{b.name}</Tag></Col>
            ))}
          </Row>
        ) : <Typography.Text type="secondary">还没有获得徽章，坚持打卡获得！</Typography.Text>}
      </Card>
    </div>
  );
}
