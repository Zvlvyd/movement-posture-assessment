import { Typography } from "antd";
import { ThunderboltOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";

const { Text, Title } = Typography;

export default function HomePage() {
  const navigate = useNavigate();
  const user = useAuthStore(s => s.user);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "calc(100vh - 120px)",
        padding: 24,
      }}
    >
      {/* Greeting */}
      <Title
        level={2}
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 400,
          fontSize: "clamp(1.1rem, 2.5vw, 1.5rem)",
          color: "var(--color-text-secondary)",
          marginBottom: 40,
          textAlign: "center",
          letterSpacing: "-0.01em",
        }}
      >
        欢迎回来，{user?.username}
      </Title>

      {/* Hero Button — Swiss: bold, clean, asymmetric accent */}
      <button
        onClick={() => navigate("/training")}
        style={{
          height: 64,
          minWidth: 240,
          padding: "0 48px",
          border: "2px solid var(--color-primary)",
          borderRadius: "var(--radius-sm)",
          background: "var(--color-primary)",
          color: "#FFFFFF",
          fontFamily: "var(--font-display)",
          fontWeight: 600,
          fontSize: 20,
          letterSpacing: "0.03em",
          cursor: "pointer",
          boxShadow: "4px 4px 0 rgba(0,0,0,0.06)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 12,
          transition: "all 200ms var(--ease-swiss)",
        }}
        onMouseEnter={e => {
          e.currentTarget.style.background = "var(--color-pure-white)";
          e.currentTarget.style.color = "var(--color-primary)";
          e.currentTarget.style.boxShadow = "2px 2px 0 rgba(0,0,0,0.04)";
          e.currentTarget.style.transform = "translate(1px, 1px)";
        }}
        onMouseLeave={e => {
          e.currentTarget.style.background = "var(--color-primary)";
          e.currentTarget.style.color = "#FFFFFF";
          e.currentTarget.style.boxShadow = "4px 4px 0 rgba(0,0,0,0.06)";
          e.currentTarget.style.transform = "";
        }}
      >
        <ThunderboltOutlined style={{ fontSize: 22 }} />
        开始训练
      </button>

      {/* Hint Link */}
      <div style={{ marginTop: 32 }}>
        <Text
          style={{
            fontFamily: "var(--font-body)",
            fontSize: 14,
            color: "var(--color-text-muted)",
          }}
        >
          还没有处方？请先进行
        </Text>
        <span
          onClick={() => navigate("/assessment")}
          style={{
            fontFamily: "var(--font-body)",
            fontSize: 14,
            color: "var(--color-accent)",
            cursor: "pointer",
            fontWeight: 500,
            marginLeft: 4,
            borderBottom: "1px solid var(--color-accent)",
            paddingBottom: 1,
          }}
          onMouseEnter={e => {
            e.currentTarget.style.color = "var(--color-primary)";
            e.currentTarget.style.borderBottomColor = "var(--color-primary)";
          }}
          onMouseLeave={e => {
            e.currentTarget.style.color = "var(--color-accent)";
            e.currentTarget.style.borderBottomColor = "var(--color-accent)";
          }}
        >
          评估
        </span>
        <Text
          style={{
            fontFamily: "var(--font-body)",
            fontSize: 14,
            color: "var(--color-text-muted)",
          }}
        >
          哦
        </Text>
      </div>
    </div>
  );
}
