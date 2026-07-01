import { useEffect, useState, useCallback, useMemo } from "react";
import {
  Card, Row, Col, Select, Input, List, Typography, Tag, Spin,
  Space, Button, message, Empty, Modal, Descriptions, Tooltip,
} from "antd";
import {
  PlayCircleOutlined, InfoCircleOutlined, SearchOutlined,
  ThunderboltOutlined, BookOutlined, CaretRightOutlined,
  WarningOutlined,
  CheckCircleOutlined, AimOutlined,
} from "@ant-design/icons";
import { learningApi } from "../services/api";
import { useTrainingSession } from "../hooks/useTrainingSession";
import TrainingSessionPanel from "../components/TrainingSessionPanel";
import TrainingResultPanel from "./training/TrainingResultPanel";
import MovementDemo from "../components/MovementDemo";
import type {
  ActionItem, LearnableAction, LearnableActionDetail, LearningComplete,
} from "../types";

const { Title, Text, Paragraph } = Typography;

const DIFFICULTY_LABELS: Record<number, string> = { 1: "初级", 2: "中级", 3: "高级" };
const DIFFICULTY_COLORS: Record<number, string> = { 1: "green", 2: "blue", 3: "red" };
const INTENSITY_LABELS: Record<string, string> = { LOW: "低强度", MEDIUM: "中强度", HIGH: "高强度" };
const INTENSITY_COLORS: Record<string, string> = { LOW: "green", MEDIUM: "orange", HIGH: "red" };
const PHASE_LABELS: Record<string, string> = { warmup: "热身", main: "主体", cooldown: "冷却" };

function diffLabel(d: number) { return DIFFICULTY_LABELS[d] || "Lv." + d; }
function diffColor(d: number) { return DIFFICULTY_COLORS[d] || "default"; }

type PageMode = "list" | "demo" | "learning" | "result";

export default function LearningPage() {
  const [mode, setMode] = useState<PageMode>("list");
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [learnable, setLearnable] = useState<LearnableAction[]>([]);
  const [category, setCategory] = useState<string | undefined>();
  const [family, setFamily] = useState<string | undefined>();
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  const [detailAction, setDetailAction] = useState<LearnableActionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);

  const [selectedAction, setSelectedAction] = useState("");
  const [demoAction, setDemoAction] = useState<LearnableActionDetail | null>(null);
  const [mediaFailed, setMediaFailed] = useState(false);
  const [result, setResult] = useState<LearningComplete | null>(null);

  const [sessionState, sessionActions] = useTrainingSession({
    actionName: selectedAction,
    onComplete: (data) => {
      setResult(data);
      setMode("result");
    },
    onError: (msg) => message.error(msg),
  });

  useEffect(() => {
    setLoading(true);
    Promise.all([
      learningApi.getActions(),
      learningApi.getLearnable(),
    ]).then(([a, l]) => {
      setActions(a);
      setLearnable(l);
    }).catch(() => message.error("加载动作库失败"))
      .finally(() => setLoading(false));
  }, []);

  // Dynamic categories from actual data (both DB + learnable)
  const categories = useMemo(() => {
    const set = new Set<string>();
    actions.forEach(a => { if (a.category) set.add(a.category); });
    learnable.forEach(l => { if (l.category) set.add(l.category); });
    return Array.from(set).sort();
  }, [actions, learnable]);

  // Dynamic families from learnable data
  const families = useMemo(() => {
    const set = new Set<string>();
    learnable.forEach(l => { if (l.family) set.add(l.family); });
    return Array.from(set).sort();
  }, [learnable]);

  const learnableNames = useMemo(
    () => new Set(learnable.map(l => l.name)),
    [learnable],
  );

  // Get learnable metadata by name
  const learnableMap = useMemo(() => {
    const map = new Map<string, LearnableAction>();
    learnable.forEach(l => map.set(l.name, l));
    return map;
  }, [learnable]);

  // Filter DB actions (merge with learnable-only actions from JSON, may not be in DB)
  const filtered = useMemo(() => {
    const dbNames = new Set(actions.map(a => a.name));
    const allActions: ActionItem[] = [...actions];
    // 合并 learnable 中但不在 DB 中的动作
    for (const l of learnable) {
      if (!dbNames.has(l.name)) {
        allActions.push({
          id: 0,
          name: l.name,
          category: l.category || "",
          difficulty: l.difficulty || 1,
          description: l.description || "",
          target_body_parts: (l.target_body_parts || []).join(", "),
        });
      }
    }

    let list = allActions;
    if (category) list = list.filter(a => a.category === category);
    if (family) {
      list = list.filter(a => {
        const l = learnableMap.get(a.name);
        return l && l.family === family;
      });
    }
    if (search.trim()) {
      const kw = search.trim().toLowerCase();
      list = list.filter(a => {
        const l = learnableMap.get(a.name);
        return a.name.toLowerCase().includes(kw)
          || (a.description || "").toLowerCase().includes(kw)
          || (a.target_body_parts || "").toLowerCase().includes(kw)
          || (l?.family_name || "").toLowerCase().includes(kw);
      });
    }
    return [...list].sort((a, b) => {
      const aL = learnableNames.has(a.name) ? 0 : 1;
      const bL = learnableNames.has(b.name) ? 0 : 1;
      if (aL !== bL) return aL - bL;
      return (a.difficulty ?? 99) - (b.difficulty ?? 99);
    });
  }, [actions, learnable, category, family, search, learnableNames, learnableMap]);

  const enterLearning = useCallback(async (actionName: string) => {
    setSelectedAction(actionName);
    setDetailLoading(true);
    try {
      const d = await learningApi.getLearnableDetail(actionName);
      setDemoAction(d);
      setMediaFailed(false);
      setMode("demo");
    } catch {
      message.error("加载动作详情失败");
    } finally {
      setDetailLoading(false);
    }
  }, []);

  // 从 demo 模式切换到学习模式：先挂载 TrainingSessionPanel（包含 video 元素），
  // 等 DOM 提交后再启动摄像头 + WS，确保 videoRef 已可用
  const startCameraFromDemo = useCallback(async () => {
    setMode("learning");
    await new Promise(r => setTimeout(r, 150));
    const ok = await sessionActions.startSession();
    if (!ok) setMode("list");
  }, [sessionActions]);

  const showDetail = useCallback(async (name: string) => {
    setDetailLoading(true);
    setDetailOpen(true);
    try {
      const d = await learningApi.getLearnableDetail(name);
      setDetailAction(d);
    } catch {
      message.error("加载动作详情失败");
      setDetailOpen(false);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  // ============================================================
  // Demo 模式：展示动作示范，用户确认后进入实时学习
  if (mode === "demo" && demoAction) {
    // Gather media: prefer DB-uploaded media, fall back to thumbnail_url/video_url
    const mediaImages = (demoAction.media || []).filter(m => m.media_type !== 'video');
    const mediaVideos = (demoAction.media || []).filter(m => m.media_type === 'video');
    const bestImage = demoAction.thumbnail_url
      || mediaImages[0]?.url
      || '';
    const bestVideo = demoAction.video_url
      || mediaVideos[0]?.url
      || '';
    const hasImage = !!bestImage;
    const hasVideo = !!bestVideo;

    return (
      <div style={{ maxWidth: 960, margin: "0 auto", padding: "16px 16px 32px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <Title level={3} style={{ margin: 0 }}>
            <BookOutlined style={{ marginRight: 8, color: "var(--color-accent)" }} />
            {demoAction.name} — 标准动作示范
          </Title>
          <Button onClick={() => setMode("list")}>返回列表</Button>
        </div>

        <Card style={{ marginBottom: 20 }}>
          {/* 视频 / 图片 / SVG 示范 */}
          <div style={{
            position: "relative", background: "#000", borderRadius: 12,
            width: "100%", height: 420, display: "flex", alignItems: "center",
            justifyContent: "center", overflow: "hidden", marginBottom: 16,
          }}>
            {(!mediaFailed && hasVideo) && (
              <video
                src={bestVideo}
                controls autoPlay loop muted playsInline
                poster={bestImage || undefined}
                style={{ width: "100%", height: "100%", objectFit: "contain" }}
                onError={() => setMediaFailed(true)}
              />
            )}
            {(!mediaFailed && !hasVideo && hasImage) && (
              <img
                src={bestImage}
                alt={demoAction.name}
                style={{ width: "100%", height: "100%", objectFit: "contain" }}
                onError={() => setMediaFailed(true)}
              />
            )}
            {(mediaFailed || (!hasVideo && !hasImage)) && (
              <MovementDemo
                movementName={demoAction.name}
                instruction={demoAction.description || "请观察标准动作示范"}
                countdown={0}
              />
            )}
            <Tag color="var(--color-accent)" style={{ position: "absolute", top: 12, left: 12, fontSize: 14 }}>
              标准示范
            </Tag>
          </div>

          <Row gutter={12} style={{ marginBottom: 12 }}>
            {demoAction.steps && demoAction.steps.length > 0 && (
              <Col span={12}>
                <Card title="动作步骤" size="small">
                  {demoAction.steps.map((s: string, i: number) => (
                    <div key={i} style={{ marginBottom: 4, display: "flex", gap: 8 }}>
                      <Tag color="blue" style={{ flexShrink: 0 }}>{i + 1}</Tag>
                      <Text style={{ fontSize: 13 }}>{s}</Text>
                    </div>
                  ))}
                </Card>
              </Col>
            )}
            <Col span={12}>
              {demoAction.cues && demoAction.cues.length > 0 && (
                <Card title="动作要领" size="small" style={{ marginBottom: 8 }}>
                  <Space wrap>
                    {demoAction.cues.map((cue: string, i: number) => (
                      <Tag key={i} icon={<AimOutlined />} color="processing">{cue}</Tag>
                    ))}
                  </Space>
                </Card>
              )}
              {demoAction.target_body_parts && demoAction.target_body_parts.length > 0 && (
                <Card title="目标部位" size="small">
                  <Space wrap>
                    {demoAction.target_body_parts.map((bp: string, i: number) => (
                      <Tag key={i} color="purple">{bp}</Tag>
                    ))}
                  </Space>
                </Card>
              )}
            </Col>
          </Row>

          {/* 常见错误 */}
          {demoAction.common_errors && demoAction.common_errors.length > 0 && (
            <Card title="常见错误" size="small" style={{ marginBottom: 12 }}>
              {demoAction.common_errors.map((err: any, i: number) => (
                <div key={i} style={{ marginBottom: 6 }}>
                  <Text strong style={{ color: "var(--color-error)", fontSize: 13 }}>{err.name}</Text>
                  <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>{err.feedback}</Text>
                </div>
              ))}
            </Card>
          )}

          <Descriptions size="small" column={2} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="支持视角">
              {demoAction.views?.join(" / ") || "正面"}
            </Descriptions.Item>
            <Descriptions.Item label="难度">
              <Tag color={diffColor(demoAction.difficulty)}>{diffLabel(demoAction.difficulty)}</Tag>
            </Descriptions.Item>
          </Descriptions>

          {/* 进入学习按钮 */}
          <div style={{ textAlign: "center", paddingTop: 8 }}>
            {demoAction.has_standard_angles ? (
              <>
                <Button
                  type="primary" size="large"
                  icon={<PlayCircleOutlined />}
                  onClick={startCameraFromDemo}
                  style={{ height: 48, paddingLeft: 32, paddingRight: 32, fontSize: 16, borderRadius: 8 }}
                >
                  学习完毕，亲自上阵
                </Button>
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    点击后将打开摄像头，实时检测动作并给出反馈
                  </Text>
                </div>
              </>
            ) : (
              <div style={{
                background: "var(--color-surface)", border: "1px solid var(--color-border)",
                borderRadius: 8, padding: "16px 24px",
              }}>
                <WarningOutlined style={{ color: "#faad14", fontSize: 20, marginRight: 8 }} />
                <Text type="warning" style={{ fontSize: 14 }}>
                  该动作暂未配置标准角度数据，无法进行实时对比学习
                </Text>
                <div style={{ marginTop: 8 }}>
                  <Button onClick={() => setMode("list")}>返回列表</Button>
                </div>
              </div>
            )}
          </div>
        </Card>
      </div>
    );
  }

  // ============================================================
  if (mode === "learning") {
    return (
      <TrainingSessionPanel
        state={sessionState}
        actions={sessionActions}
        exerciseInfo={{ name: selectedAction }}
        onExit={() => { sessionActions.endSession(); setMode("list"); }}
      />
    );
  }

  if (mode === "result" && result) {
    return (
      <TrainingResultPanel
        result={result}
        plan={{ id: 0, user_id: 0, plan_name: selectedAction, status: "", generation_method: "", items: [] }}
        completedCount={1} totalCount={1}
        onBackToPlan={() => setMode("list")}
        onNextExercise={() => setMode("list")}
        onAllPlans={() => setMode("list")}
      />
    );
  }

  // ============================================================
  return (
    <div style={{ maxWidth: 1024, margin: "0 auto" }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ color: "var(--color-text-primary)", marginBottom: 8 }}>
          <BookOutlined style={{ marginRight: 10, color: "var(--color-accent)" }} />
          标准动作学习
        </Title>
        <Text type="secondary">
          全部 {actions.length} 个动作 · {learnable.length} 个支持标准学习模式
          {" · "}{families.length} 个动作家族
          {" · "}{learnable.filter(l => l.has_standard_angles).length} 个已配置实时对比
        </Text>
      </div>

      {/* Toolbar */}
      <Card size="small" style={{ marginBottom: 20 }}>
        <Space wrap>
          <Input
            prefix={<SearchOutlined />}
            placeholder="搜索动作名称、描述、家族..."
            allowClear
            style={{ width: 240 }}
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <Select
            placeholder="全部分类"
            allowClear
            style={{ width: 160 }}
            value={category}
            onChange={v => { setCategory(v); setFamily(undefined); }}
            options={categories.map(c => ({ value: c, label: c }))}
          />
          <Select
            placeholder="全部家族"
            allowClear
            style={{ width: 180 }}
            value={family}
            onChange={v => { setFamily(v); setCategory(undefined); }}
            options={families.map(f => {
              const first = learnable.find(l => l.family === f);
              return { value: f, label: first?.family_name || f };
            })}
          />
          <Tooltip title="已配置标准角度数据，可进行逐帧实时对比">
            <Tag color="var(--color-accent)" style={{ marginLeft: 8 }}>
              <ThunderboltOutlined /> 实时对比就绪
            </Tag>
          </Tooltip>
        </Space>
      </Card>

      {/* Action card grid */}
      {loading ? (
        <div style={{ textAlign: "center", padding: 64 }}><Spin size="large" /></div>
      ) : filtered.length === 0 ? (
        <Empty description={search || category || family ? "无匹配动作" : "动作库为空"} />
      ) : (
        <List
          grid={{ gutter: 16, xs: 1, sm: 2, md: 2, lg: 3, xl: 3, xxl: 4 }}
          dataSource={filtered}
          renderItem={(item: ActionItem) => {
            const l = learnableMap.get(item.name);
            const isLearnable = !!l;
            const hasAngles = l?.has_standard_angles ?? false;
            return (
              <List.Item>
                <Card
                  hoverable
                  size="small"
                  style={{
                    borderLeft: hasAngles ? "3px solid var(--color-accent)" : isLearnable ? "3px solid var(--color-muted)" : undefined,
                    height: "100%",
                  }}
                  bodyStyle={{ display: "flex", flexDirection: "column", height: "100%" }}
                >
                  {/* Title */}
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                    <Text strong style={{ fontSize: 14, flex: 1 }}>{item.name}</Text>
                    {hasAngles && (
                      <Tag color="var(--color-accent)" style={{ margin: 0, fontSize: 11 }}>
                        <ThunderboltOutlined /> 实时对比
                      </Tag>
                    )}
                    {isLearnable && !hasAngles && (
                      <Tag color="var(--color-muted)" style={{ margin: 0, fontSize: 11 }}>
                        可学习
                      </Tag>
                    )}
                  </div>

                  {/* Tags */}
                  <Space size={4} wrap style={{ marginBottom: 6 }}>
                    {l && <Tag color="geekblue">{l.family_name}</Tag>}
                    <Tag>{item.category}</Tag>
                    <Tag color={diffColor(item.difficulty)}>{diffLabel(item.difficulty)}</Tag>
                    {l?.intensity && (
                      <Tag color={INTENSITY_COLORS[l.intensity] || "default"}>
                        {INTENSITY_LABELS[l.intensity] || l.intensity}
                      </Tag>
                    )}
                  </Space>

                  {/* Description */}
                  {item.description && (
                    <Text type="secondary"
                      style={{ fontSize: 12, lineHeight: 1.5, flex: 1, marginBottom: 10 }}
                      ellipsis={{ tooltip: true }}>
                      {item.description}
                    </Text>
                  )}

                  {/* Actions */}
                  <Space style={{ marginTop: "auto" }}>
                    {isLearnable && (
                      <Button
                        type={hasAngles ? "primary" : "default"}
                        icon={<PlayCircleOutlined />}
                        size="small"
                        onClick={() => enterLearning(item.name)}
                      >
                        开始标准学习
                      </Button>
                    )}
                    {isLearnable && (
                      <Button
                        icon={<InfoCircleOutlined />}
                        size="small"
                        onClick={() => showDetail(item.name)}
                      >
                        查看详情
                      </Button>
                    )}
                    {!isLearnable && (
                      <Button
                        icon={<InfoCircleOutlined />}
                        size="small"
                        onClick={() => showDetail(item.name)}
                      >
                        查看详情
                      </Button>
                    )}
                  </Space>
                </Card>
              </List.Item>
            );
          }}
        />
      )}

      {/* Detail Modal */}
      <Modal
        title={detailAction ? detailAction.name + " - 动作详情" : "动作详情"}
        open={detailOpen}
        onCancel={() => { setDetailOpen(false); setDetailAction(null); }}
        footer={detailAction ? [
          <Button key="cancel" onClick={() => { setDetailOpen(false); setDetailAction(null); }}>关闭</Button>,
          <Button key="start" type="primary" icon={<PlayCircleOutlined />}
            onClick={() => { setDetailOpen(false); enterLearning(detailAction.name); }}>
            开始标准学习
          </Button>,
        ] : null}
        width={680}
      >
        {detailLoading ? (
          <div style={{ textAlign: "center", padding: 48 }}><Spin /></div>
        ) : detailAction ? (
          <>
            <Descriptions column={2} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="家族">{detailAction.family_name}</Descriptions.Item>
              <Descriptions.Item label="分类">{detailAction.subcategory || detailAction.category}</Descriptions.Item>
              <Descriptions.Item label="难度">
                <Tag color={diffColor(detailAction.difficulty)}>{diffLabel(detailAction.difficulty)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="强度">
                <Tag color={INTENSITY_COLORS[detailAction.intensity] || "default"}>
                  {INTENSITY_LABELS[detailAction.intensity] || detailAction.intensity}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="支持视角">
                {detailAction.views?.join(" / ") || "正面"}
              </Descriptions.Item>
              <Descriptions.Item label="实时对比">
                {detailAction.has_standard_angles
                  ? <Tag color="var(--color-accent)"><CheckCircleOutlined /> 标准角度已配置</Tag>
                  : <Tag color="var(--color-muted)">待配置标准角度</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {detailAction.description || "-"}
              </Descriptions.Item>
            </Descriptions>

            {/* Steps */}
            {detailAction.steps && detailAction.steps.length > 0 && (
              <Card title="动作步骤" size="small" style={{ marginBottom: 12 }}>
                {detailAction.steps.map((s: string, i: number) => (
                  <div key={i} style={{ marginBottom: 4, display: "flex", alignItems: "flex-start", gap: 8 }}>
                    <Tag color="blue" style={{ flexShrink: 0 }}>{i + 1}</Tag>
                    <Text>{s}</Text>
                  </div>
                ))}
              </Card>
            )}

            {/* Cues */}
            {detailAction.cues && detailAction.cues.length > 0 && (
              <Card title="动作要领" size="small" style={{ marginBottom: 12 }}>
                <Space wrap>
                  {detailAction.cues.map((cue: string, i: number) => (
                    <Tag key={i} icon={<AimOutlined />} color="processing">{cue}</Tag>
                  ))}
                </Space>
              </Card>
            )}

            {/* Phases */}
            {detailAction.phases && detailAction.phases.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  适用训练阶段：{detailAction.phases.map(p => PHASE_LABELS[p] || p).join(" / ")}
                </Text>
              </div>
            )}

            {/* Target body parts */}
            {detailAction.target_body_parts && detailAction.target_body_parts.length > 0 && (
              <Card title="目标部位" size="small" style={{ marginBottom: 12 }}>
                <Space wrap>
                  {detailAction.target_body_parts.map((bp: string, i: number) => (
                    <Tag key={i} color="purple">{bp}</Tag>
                  ))}
                </Space>
              </Card>
            )}

            {/* Common errors */}
            {detailAction.common_errors && detailAction.common_errors.length > 0 && (
              <Card title="常见错误" size="small" style={{ marginBottom: 12 }}>
                {detailAction.common_errors.map((err: any, i: number) => (
                  <div key={i} style={{ marginBottom: 8 }}>
                    <Text strong style={{ color: "var(--color-error)" }}>{err.name}</Text>
                    <br />
                    <Text type="secondary">{err.feedback}</Text>
                  </div>
                ))}
              </Card>
            )}

            {/* Standard keypoints */}
            {detailAction.standard_keypoints && Object.keys(detailAction.standard_keypoints).length > 0 && (
              <Card title="标准关键点" size="small">
                {Object.entries(detailAction.standard_keypoints).map(([view, vdata]: [string, any]) => (
                  <div key={view} style={{ marginBottom: 12 }}>
                    <Text strong>{view}</Text>
                    {vdata.description && <Text type="secondary"> - {vdata.description}</Text>}
                    {vdata.target_angles && (
                      <div style={{ marginTop: 4, display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {Object.entries(vdata.target_angles as Record<string, any>).map(([joint, range]: [string, any]) => (
                          <Tag key={joint} color="blue" style={{ fontSize: 12 }}>
                            {joint}: {range.min}&deg;&ndash;{range.max}&deg; (最优 {range.optimal}&deg;)
                          </Tag>
                        ))}
                      </div>
                    )}
                    {vdata.key_checks && (
                      <div style={{ marginTop: 6 }}>
                        {vdata.key_checks.map((kc: any, ci: number) => (
                          <Text key={ci} type="secondary" style={{ fontSize: 12, display: "block" }}>
                            <CheckCircleOutlined style={{ marginRight: 4 }} />
                            {kc.joint}: {kc.rule} ({kc.direction} {kc.threshold}{kc.unit})
                          </Text>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </Card>
            )}
          </>
        ) : (
          <Text type="secondary">无法加载动作详情</Text>
        )}
      </Modal>
    </div>
  );
}
