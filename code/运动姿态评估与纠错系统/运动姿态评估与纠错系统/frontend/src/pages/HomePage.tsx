import { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, Button, Typography, List, Tag } from "antd";
import { ExperimentOutlined, PlayCircleOutlined, CheckCircleOutlined, TrophyOutlined, ScanOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import { recordsApi, prescriptionApi, checkinApi } from "../services/api";
import type { TrainingStats, Prescription } from "../types";

export default function HomePage() {
  const navigate = useNavigate();
  const user = useAuthStore(s => s.user);
  const [stats, setStats] = useState<TrainingStats | null>(null);
  const [rx, setRx] = useState<Prescription | null>(null);
  const [badgeCount, setBadgeCount] = useState(0);

  useEffect(() => {
    recordsApi.stats().then(setStats).catch(() => {});
    prescriptionApi.list().then(rxs => { if (rxs.length > 0) setRx(rxs[0]); }).catch(() => {});
    checkinApi.badges().then(b => setBadgeCount(b.length)).catch(() => {});
  }, []);

  return (
    <div>
      <Typography.Title level={4}>欢迎回来，{user?.username}</Typography.Title>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={6}><Card className="stat-card"><Statistic title="连续打卡" value={stats?.current_streak || 0} suffix="天" prefix={<CheckCircleOutlined />} /></Card></Col>
        <Col span={6}><Card className="stat-card"><Statistic title="近7天训练" value={stats?.total_sessions_7d || 0} suffix="次" prefix={<PlayCircleOutlined />} /></Card></Col>
        <Col span={6}><Card className="stat-card"><Statistic title="平均评分" value={stats?.average_score || 0} suffix="分" precision={1} /></Card></Col>
        <Col span={6}><Card className="stat-card"><Statistic title="徽章" value={badgeCount} suffix="枚" prefix={<TrophyOutlined />} /></Card></Col>
      </Row>
      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card title="快捷入口">
            <Button block type="primary" icon={<ScanOutlined />} style={{ marginBottom: 12 }} onClick={() => navigate("/assessment")}>体态评估（新）</Button>
            <Button block icon={<ExperimentOutlined />} style={{ marginBottom: 12 }} onClick={() => navigate("/fms")}>FMS 筛查（旧）</Button>
            <Button block icon={<PlayCircleOutlined />} onClick={() => navigate("/training")}>开始今日训练</Button>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="当前处方">
            {rx ? (
              <div>
                <Tag color="blue">第{rx.phase}阶段</Tag>
                <Tag color={rx.status === "active" ? "green" : "default"}>{rx.status}</Tag>
                <List size="small" dataSource={rx.items.slice(0, 5)} renderItem={item => (
                  <List.Item>{item.action_name} - {item.sets}组 x {item.reps}次</List.Item>
                )} />
                <Button type="link" onClick={() => navigate("/training")}>查看全部</Button>
              </div>
            ) : (
              <div style={{ textAlign: "center", padding: 24 }}>
                <Typography.Text type="secondary">暂无活跃处方，请先完成评估</Typography.Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
