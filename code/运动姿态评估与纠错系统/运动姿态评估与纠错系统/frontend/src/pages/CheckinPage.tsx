import { useEffect, useState, useCallback } from "react";
import { Card, Button, Typography, Row, Col, Tag, message, Tooltip, Spin, Progress, Empty } from "antd";
import {
  CheckCircleOutlined, TrophyOutlined, FireOutlined,
  LeftOutlined, RightOutlined, StarOutlined, ThunderboltOutlined,
  HeartOutlined, SmileOutlined, CrownOutlined, AimOutlined
} from "@ant-design/icons";
import { checkinApi } from "../services/api";

// ── Calendar helpers ────────────────────────────────────────────────────
function getMonthDays(year: number, month: number) {
  const first = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const days: (number | null)[] = [];
  for (let i = 0; i < first; i++) days.push(null);
  for (let d = 1; d <= daysInMonth; d++) days.push(d);
  return days;
}

const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];

// ── Badge icon map ──────────────────────────────────────────────────────
const BADGE_ICONS: Record<string, React.ReactNode> = {
  streak_3: <FireOutlined style={{ color: "#fa8c16" }} />,
  streak_7: <ThunderboltOutlined style={{ color: "#faad14" }} />,
  streak_14: <StarOutlined style={{ color: "#f5222d" }} />,
  streak_30: <CrownOutlined style={{ color: "#eb2f96" }} />,
  sessions_5: <SmileOutlined style={{ color: "#52c41a" }} />,
  sessions_10: <HeartOutlined style={{ color: "#1890ff" }} />,
  sessions_30: <AimOutlined style={{ color: "#722ed1" }} />,
  score_80: <TrophyOutlined style={{ color: "#faad14" }} />,
};

// ── Check-in animation ──────────────────────────────────────────────────
function CheckinCelebration({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 1000, pointerEvents: "none",
    }}>
      <div style={{
        fontSize: 80, animation: "checkinPop 0.6s ease-out",
        textAlign: "center",
      }}>
        <CheckCircleOutlined style={{ color: "#52c41a", display: "block" }} />
        <div style={{ fontSize: 24, marginTop: 8, color: "#52c41a", fontWeight: 700 }}>
          打卡成功！
        </div>
      </div>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────
export default function CheckinPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth());
  const [status, setStatus] = useState<any>(null);
  const [badges, setBadges] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [celebrate, setCelebrate] = useState(false);

  const fetchData = useCallback(() => {
    checkinApi.status().then(setStatus).catch(() => {});
    checkinApi.badges().then(setBadges).catch(() => {});
  }, []);
  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCheckin = async () => {
    setLoading(true);
    try {
      const res = await checkinApi.checkin();
      setCelebrate(true);
      setTimeout(() => setCelebrate(false), 1200);
      setTimeout(() => fetchData(), 1300);
    } catch (e: any) {
      message.error(e.response?.data?.detail || "打卡失败，今天可能已经打过卡了");
    } finally { setLoading(false); }
  };

  const today = now.getDate();
  const isTodayThisMonth = now.getFullYear() === year && now.getMonth() === month;
  const checkedDates: number[] = (status?.recent_cards || [])
    .filter((c: any) => {
      const d = new Date(c.date);
      return d.getFullYear() === year && d.getMonth() === month;
    })
    .map((c: any) => new Date(c.date).getDate());

  const monthDays = getMonthDays(year, month);
  const streakDays = status?.streak_days || 0;
  const badgeLevel = streakDays >= 30 ? "legend" : streakDays >= 14 ? "master" : streakDays >= 7 ? "veteran" : streakDays >= 3 ? "rookie" : "newbie";

  const badgeLevelColors: Record<string, string> = {
    newbie: "#d9d9d9", rookie: "#fa8c16", veteran: "#faad14", master: "#f5222d", legend: "#eb2f96",
  };

  return (
    <div style={{ maxWidth: 640, margin: "0 auto" }}>
      <CheckinCelebration show={celebrate} />

      {/* ── Streak Hero ── */}
      <Card style={{ marginBottom: 16, textAlign: "center", overflow: "hidden" }}>
        <div style={{
          width: 80, height: 80, borderRadius: "50%",
          border: `4px solid ${badgeLevelColors[badgeLevel]}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          margin: "0 auto 12px", fontSize: 36,
        }}>
          <FireOutlined style={{ color: badgeLevelColors[badgeLevel] }} />
        </div>
        <Typography.Title level={2} style={{ margin: 0 }}>{streakDays}</Typography.Title>
        <Typography.Text type="secondary" style={{ fontSize: 16 }}>连续打卡天数</Typography.Text>
        <div style={{ marginTop: 12 }}>
          <Progress
            percent={Math.min(streakDays / 30 * 100, 100)}
            showInfo={false}
            strokeColor={badgeLevelColors[badgeLevel]}
            style={{ maxWidth: 300, margin: "0 auto" }}
          />
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {streakDays >= 30 ? "🔥 已达成30天传奇！" : `距离30天传奇还差 ${30 - streakDays} 天`}
          </Typography.Text>
        </div>
        <Button
          type="primary" size="large" block
          loading={loading}
          onClick={handleCheckin}
          disabled={!isTodayThisMonth && checkedDates.length === 0}
          style={{ marginTop: 16, height: 48, fontSize: 18, borderRadius: 12 }}
          icon={<CheckCircleOutlined />}
        >
          {checkedDates.includes(today) ? "今日已打卡 ✓" : "今日打卡"}
        </Button>
      </Card>

      {/* ── Calendar ── */}
      <Card
        title={
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Button type="text" icon={<LeftOutlined />} onClick={() => {
              if (month === 0) { setYear(y => y-1); setMonth(11); }
              else setMonth(m => m-1);
            }} />
            <span style={{ fontWeight: 600 }}>{year}年{month+1}月</span>
            <Button type="text" icon={<RightOutlined />} onClick={() => {
              if (month === 11) { setYear(y => y+1); setMonth(0); }
              else setMonth(m => m+1);
            }} />
          </div>
        }
        size="small"
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 4 }}>
          {WEEKDAYS.map(w => (
            <div key={w} style={{ textAlign: "center", fontWeight: 600, color: "#888", fontSize: 12, padding: "4px 0" }}>
              {w}
            </div>
          ))}
          {monthDays.map((d, i) => (
            <div key={i} style={{
              textAlign: "center", padding: "6px 0", borderRadius: 8,
              background: d && checkedDates.includes(d)
                ? (d === today && isTodayThisMonth ? "#52c41a" : "#f6ffed")
                : d === today && isTodayThisMonth ? "#e6f7ff"
                : "transparent",
              color: d && checkedDates.includes(d)
                ? (d === today && isTodayThisMonth ? "#fff" : "#52c41a")
                : d === today && isTodayThisMonth ? "#1890ff"
                : "#333",
              fontWeight: d === today && isTodayThisMonth ? 700 : 400,
              fontSize: 13,
              position: "relative",
            }}>
              {d}
              {d && checkedDates.includes(d) && (
                <CheckCircleOutlined style={{
                  position: "absolute", top: -2, right: 2,
                  fontSize: 10, color: d === today && isTodayThisMonth ? "#fff" : "#52c41a",
                }} />
              )}
            </div>
          ))}
        </div>
        <div style={{ marginTop: 8, textAlign: "center", fontSize: 12, color: "#aaa" }}>
          本月打卡 {checkedDates.length} 天
        </div>
      </Card>

      {/* ── Stats Row ── */}
      <Row gutter={12} style={{ marginTop: 16 }}>
        <Col span={8}>
          <Card size="small" style={{ textAlign: "center" }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#1890ff" }}>
              {status?.recent_cards?.length || 0}
            </div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>本月打卡</Typography.Text>
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" style={{ textAlign: "center" }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#52c41a" }}>
              {badges.length}
            </div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>已获得徽章</Typography.Text>
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" style={{ textAlign: "center" }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#fa8c16" }}>
              {streakDays}
            </div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>连续天数</Typography.Text>
          </Card>
        </Col>
      </Row>

      {/* ── Badges ── */}
      <Card title={
        <span><TrophyOutlined style={{ color: "#faad14" }} /> 我的徽章</span>
      } style={{ marginTop: 16 }}>
        {badges.length > 0 ? (
          <Row gutter={[12, 12]}>
            {badges.map((b: any) => (
              <Col key={b.type} xs={8} sm={6}>
                <Tooltip title={b.description || b.name}>
                  <div style={{
                    textAlign: "center", padding: 12, borderRadius: 8,
                    background: "#fffbe6", cursor: "pointer",
                    transition: "transform 0.2s",
                  }}
                    onMouseEnter={e => (e.currentTarget.style.transform = "scale(1.05)")}
                    onMouseLeave={e => (e.currentTarget.style.transform = "scale(1)")}
                  >
                    <div style={{ fontSize: 28, marginBottom: 4 }}>
                      {BADGE_ICONS[b.type] || <TrophyOutlined style={{ color: "#faad14" }} />}
                    </div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "#8c6e0c" }}>{b.name}</div>
                  </div>
                </Tooltip>
              </Col>
            ))}
          </Row>
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="还没有获得徽章，坚持打卡获得！"
          />
        )}
      </Card>

      {/* ── Animation CSS ── */}
      <style>{`
        @keyframes checkinPop {
          0% { transform: scale(0.3); opacity: 0; }
          50% { transform: scale(1.2); opacity: 1; }
          100% { transform: scale(1); opacity: 0.9; }
        }
      `}</style>
    </div>
  );
}
