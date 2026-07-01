import { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Input, Select, Slider, Switch, Tag, Button, Pagination,
  Modal, Form, Image, Descriptions, Collapse, message, Space, Typography,
  Tabs, Timeline, Empty, Spin, Badge, Tooltip, Upload,
} from 'antd';
import {
  SearchOutlined, PlusOutlined, EditOutlined, EyeOutlined,
  BookOutlined, ThunderboltOutlined, FilterOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { UnifiedAction, UnifiedActionListResponse } from '../../types';
import { coachApi } from '../../services/api';
import MediaUpload from '../../components/MediaUpload';

const { Text, Paragraph, Title } = Typography;
const { Panel } = Collapse;

const DIFFICULTY_COLORS = ['#52c41a', '#1677ff', '#faad14', '#fa8c16', '#f5222d'];
const DIFFICULTY_LABELS = ['极简', '简单', '中等', '困难', '极难'];

export default function ActionLibraryPage() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<UnifiedActionListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(12);

  // Filters
  const [search, setSearch] = useState('');
  const [filterCategory, setFilterCategory] = useState<string | undefined>();
  const [filterFamily, setFilterFamily] = useState<string | undefined>();
  const [filterDifficulty, setFilterDifficulty] = useState<number | undefined>();
  const [bodyPart, setBodyPart] = useState('');

  // Modals
  const [selectedAction, setSelectedAction] = useState<UnifiedAction | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editForm] = Form.useForm();
  const [saving, setSaving] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm();
  const [creating, setCreating] = useState(false);

  const fetchActions = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page, page_size: pageSize };
      if (search) params.search = search;
      if (filterCategory) params.category = filterCategory;
      if (filterFamily) params.family = filterFamily;
      if (filterDifficulty) params.difficulty = filterDifficulty;
      if (bodyPart) params.body_part = bodyPart;
      const res = await coachApi.listActions(params);
      setData(res);
    } catch {
      message.error('获取动作库失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, filterCategory, filterFamily, filterDifficulty, bodyPart]);

  useEffect(() => { fetchActions(); }, [fetchActions]);

  // View detail
  const handleViewDetail = async (action: UnifiedAction) => {
    try {
      const id = action.id || action.json_id || action.name;
      const detail = await coachApi.getAction(id);
      setSelectedAction(detail);
      setDetailOpen(true);
      setEditMode(false);
    } catch {
      message.error('获取动作详情失败');
    }
  };

  // Open detail modal AND enter edit mode (waits for fetch to complete)
  const handleEditAction = async (action: UnifiedAction) => {
    try {
      const lookup = action.id ?? action.json_id ?? action.name;
      const detail = await coachApi.getAction(lookup);
      setSelectedAction(detail);
      setDetailOpen(true);
      // Pre-fill the edit form from fetched detail
      editForm.setFieldsValue({
        name: detail.name,
        category: detail.category,
        family: detail.family,
        family_name: detail.family_name,
        difficulty: detail.difficulty,
        description: detail.description,
        steps: detail.steps || [],
        cues: detail.cues || [],
        target_body_parts: detail.target_body_parts || [],
      });
      setEditMode(true);
    } catch {
      message.error('获取动作详情失败');
    }
  };

  // Edit (from detail modal — selectedAction already loaded)
  const handleEdit = () => {
    if (!selectedAction) return;
    editForm.setFieldsValue({
      name: selectedAction.name,
      category: selectedAction.category,
      family: selectedAction.family,
      family_name: selectedAction.family_name,
      difficulty: selectedAction.difficulty,
      description: selectedAction.description,
      steps: selectedAction.steps || [],
      cues: selectedAction.cues || [],
      target_body_parts: selectedAction.target_body_parts || [],
    });
    setEditMode(true);
  };

  const handleSave = async () => {
    if (!selectedAction?.id) {
      message.warning('只能编辑数据库中的动作');
      return;
    }
    const values = editForm.getFieldsValue();
    setSaving(true);
    try {
      await coachApi.updateAction(selectedAction.id, values);
      message.success('保存成功');
      setEditMode(false);
      fetchActions();
      setDetailOpen(false);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  // Create
  const handleCreate = async () => {
    const values = createForm.getFieldsValue();
    if (!values.name) {
      message.warning('请输入动作名称');
      return;
    }
    setCreating(true);
    try {
      await coachApi.createAction(values);
      message.success('创建成功');
      setCreateOpen(false);
      createForm.resetFields();
      fetchActions();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '创建失败');
    } finally {
      setCreating(false);
    }
  };

  // Media upload callback — refresh both the detail and the list
  const handleMediaChange = async () => {
    const actionRef = selectedAction;
    if (actionRef) {
      const lookup = actionRef.id ?? actionRef.json_id ?? actionRef.name;
      if (lookup) {
        try {
          const fresh = await coachApi.getAction(lookup);
          setSelectedAction(fresh);
        } catch { /* ignore, fetchActions below will still run */ }
      }
    }
    fetchActions();
  };

  // ── Render Card ──
  const renderActionCard = (action: UnifiedAction) => (
    <Col key={action.id || action.json_id || action.name} xs={24} sm={12} md={8} lg={6}>
      <Card
        hoverable
        size="small"
        style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
        bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        cover={
          <div style={{ height: 140, overflow: 'hidden', background: '#f5f5f5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {(action.thumbnail_url || action.media?.find(m => m.media_type === 'thumbnail')?.url) ? (
              <Image
                src={action.thumbnail_url || action.media?.find(m => m.media_type === 'thumbnail')?.url}
                alt={action.name}
                width="100%"
                height={140}
                style={{ objectFit: 'cover' }}
                preview={false}
                fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE0MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE0MCIgZmlsbD0iI2YwZjBmMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSIgZmlsbD0iIzk5OSI+5peg5Zu+54mHPC90ZXh0Pjwvc3ZnPg=="
              />
            ) : (
              <div style={{ width: '100%', height: 140, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <ThunderboltOutlined style={{ fontSize: 40, color: 'rgba(255,255,255,0.6)' }} />
              </div>
            )}
          </div>
        }
        actions={[
          <Tooltip title="查看详情"><EyeOutlined key="view" onClick={() => handleViewDetail(action)} /></Tooltip>,
          action.id ? <Tooltip title="编辑"><EditOutlined key="edit" onClick={() => handleEditAction(action)} /></Tooltip> : null,
        ].filter(Boolean)}
      >
        <Card.Meta
          style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
          title={
            <Text ellipsis style={{ display: 'block' }}>
              {action.name}
              {action.has_standard_angles && (
                <Badge status="processing" style={{ marginLeft: 6 }} />
              )}
            </Text>
          }
          description={
            <div style={{ display: 'flex', flexDirection: 'column', minHeight: 72 }}>
              <Space size={4} wrap style={{ marginBottom: 4 }}>
                {action.family_name && <Tag color="blue">{action.family_name}</Tag>}
                <Tag color={DIFFICULTY_COLORS[(action.difficulty || 1) - 1]}>
                  {DIFFICULTY_LABELS[(action.difficulty || 1) - 1]}
                </Tag>
                {action.category && <Tag>{action.category}</Tag>}
              </Space>
              <Space size={4} wrap>
                {action.source === 'custom'
                  ? <Tag color="orange">自定义</Tag>
                  : <Tag color="green">系统</Tag>
                }
              </Space>
              <Paragraph
                ellipsis={{ rows: 2 }}
                style={{ marginTop: 6, fontSize: 12, color: '#666', lineHeight: '18px' }}
              >
                {action.description || '暂无描述'}
              </Paragraph>
            </div>
          }
        />
      </Card>
    </Col>
  );

  // ── Render Detail Modal ──
  const renderDetailModal = () => (
    <Modal
      title={editMode ? '编辑动作' : (selectedAction?.name || '动作详情')}
      open={detailOpen}
      onCancel={() => { setDetailOpen(false); setEditMode(false); }}
      width={900}
      footer={
        editMode ? (
          <Space>
            <Button onClick={() => setEditMode(false)}>取消</Button>
            <Button type="primary" loading={saving} onClick={handleSave}>保存</Button>
          </Space>
        ) : (
          <Space>
            {selectedAction?.id && (
              <Button icon={<EditOutlined />} onClick={handleEdit}>编辑</Button>
            )}
            <Button onClick={() => setDetailOpen(false)}>关闭</Button>
          </Space>
        )
      }
    >
      {selectedAction && (editMode ? (
        <Form form={editForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="动作名称" name="name"><Input /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="分类" name="category"><Input /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="家族标识" name="family"><Input /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="家族名称" name="family_name"><Input /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="难度 (1-5)" name="difficulty">
                <Slider min={1} max={5} marks={{ 1: '极简', 2: '简单', 3: '中等', 4: '困难', 5: '极难' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="描述" name="description"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item label="步骤" name="steps">
            <Select mode="tags" placeholder="输入步骤后按回车" />
          </Form.Item>
          <Form.Item label="动作要点" name="cues">
            <Select mode="tags" placeholder="输入要点后按回车" />
          </Form.Item>
          <Form.Item label="目标部位" name="target_body_parts">
            <Select mode="tags" placeholder="输入部位后按回车" />
          </Form.Item>
        </Form>
      ) : (
        <div>
          {/* Media preview */}
          {selectedAction.media?.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <Space wrap>
                {selectedAction.media.filter(m => m.media_type !== 'video').map(m => (
                  <Image key={m.id} src={m.url} alt={m.original_filename} width={120} height={90} style={{ objectFit: 'cover', borderRadius: 6 }} />
                ))}
              </Space>
              {selectedAction.media.filter(m => m.media_type === 'video').map(m => (
                <div key={m.id} style={{ marginTop: 8 }}>
                  <video controls style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 6 }} src={m.url} />
                </div>
              ))}
            </div>
          )}

          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="名称">{selectedAction.name}</Descriptions.Item>
            <Descriptions.Item label="来源">
              <Tag color={selectedAction.source === 'custom' ? 'orange' : selectedAction.source === 'db' ? 'blue' : 'green'}>
                {selectedAction.source === 'custom' ? '自定义' : selectedAction.source === 'db' ? '数据库' : '系统内置'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="分类">{selectedAction.category || '-'}</Descriptions.Item>
            <Descriptions.Item label="子分类">{selectedAction.subcategory || '-'}</Descriptions.Item>
            <Descriptions.Item label="家族">{selectedAction.family_name || selectedAction.family || '-'}</Descriptions.Item>
            <Descriptions.Item label="难度">
              <Tag color={DIFFICULTY_COLORS[(selectedAction.difficulty || 1) - 1]}>
                {DIFFICULTY_LABELS[(selectedAction.difficulty || 1) - 1]}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="强度">{selectedAction.intensity || '-'}</Descriptions.Item>
            <Descriptions.Item label="标准角度">
              {selectedAction.has_standard_angles ? <Tag color="success">支持</Tag> : <Tag>不支持</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="目标部位" span={2}>
              {(selectedAction.target_body_parts || []).map((p: string) => <Tag key={p}>{p}</Tag>)}
              {(!selectedAction.target_body_parts || selectedAction.target_body_parts.length === 0) && '-'}
            </Descriptions.Item>
            <Descriptions.Item label="训练阶段" span={2}>
              {(selectedAction.phases || []).map((p: string) => <Tag key={p}>{p}</Tag>)}
              {(!selectedAction.phases || selectedAction.phases.length === 0) && '-'}
            </Descriptions.Item>
          </Descriptions>

          <Collapse style={{ marginTop: 16 }} defaultActiveKey={['desc']}>
            <Panel header="描述与步骤" key="desc">
              <Paragraph>{selectedAction.description || '暂无描述'}</Paragraph>
              {(selectedAction.steps || []).length > 0 && (
                <Timeline items={(selectedAction.steps || []).map((s: string, i: number) => ({
                  color: 'blue',
                  children: <span><Text strong>{i + 1}.</Text> {s}</span>,
                }))} />
              )}
            </Panel>
            <Panel header="动作要点" key="cues">
              {(selectedAction.cues || []).length > 0
                ? (selectedAction.cues || []).map((c: string, i: number) => <Tag key={i} style={{ marginBottom: 4 }}>{c}</Tag>)
                : <Text type="secondary">暂无</Text>
              }
            </Panel>
            <Panel header="禁忌症" key="contra">
              {selectedAction.contraindications ? (
                <Descriptions size="small" column={2}>
                  {Object.entries(selectedAction.contraindications).map(([k, v]) => (
                    <Descriptions.Item key={k} label={k}>{v}</Descriptions.Item>
                  ))}
                </Descriptions>
              ) : <Text type="secondary">无特殊禁忌</Text>}
            </Panel>
            {selectedAction.id && (
              <Panel header="媒体管理" key="media">
                <Tabs items={[
                  { key: 'thumbnail', label: '缩略图', children: (
                    <MediaUpload
                      actionId={selectedAction.id}
                      mediaType="thumbnail"
                      existingMedia={selectedAction.media || []}
                      onSuccess={handleMediaChange}
                      onDelete={handleMediaChange}
                    />
                  )},
                  { key: 'image', label: '示例图片', children: (
                    <MediaUpload
                      actionId={selectedAction.id}
                      mediaType="image"
                      existingMedia={selectedAction.media || []}
                      onSuccess={handleMediaChange}
                      onDelete={handleMediaChange}
                    />
                  )},
                  { key: 'video', label: '示例视频', children: (
                    <MediaUpload
                      actionId={selectedAction.id}
                      mediaType="video"
                      existingMedia={selectedAction.media || []}
                      onSuccess={handleMediaChange}
                      onDelete={handleMediaChange}
                    />
                  )},
                ]} />
              </Panel>
            )}
          </Collapse>
        </div>
      ))}
    </Modal>
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <BookOutlined /> 标准动作库管理
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchActions}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            添加动作
          </Button>
        </Space>
      </div>

      <Row gutter={16}>
        {/* Filter Panel */}
        <Col xs={24} md={6} lg={5}>
          <Card size="small" title={<span><FilterOutlined /> 筛选</span>}>
            <Input
              placeholder="搜索动作名称"
              prefix={<SearchOutlined />}
              allowClear
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1); }}
              style={{ marginBottom: 12 }}
            />
            <Select
              placeholder="分类"
              allowClear
              style={{ width: '100%', marginBottom: 12 }}
              value={filterCategory}
              onChange={v => { setFilterCategory(v); setPage(1); }}
              options={(data?.categories || []).map(c => ({ value: c, label: c }))}
            />
            <Select
              placeholder="动作家族"
              allowClear
              style={{ width: '100%', marginBottom: 12 }}
              value={filterFamily}
              onChange={v => { setFilterFamily(v); setPage(1); }}
              options={(data?.families || []).map(f => ({ value: f, label: f }))}
            />
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>难度</Text>
              <Select
                placeholder="全部"
                allowClear
                style={{ width: '100%' }}
                value={filterDifficulty}
                onChange={v => { setFilterDifficulty(v); setPage(1); }}
                options={[1, 2, 3, 4, 5].map(d => ({
                  value: d,
                  label: `${d} - ${DIFFICULTY_LABELS[d - 1]}`,
                }))}
              />
            </div>
            <Input
              placeholder="目标部位"
              allowClear
              value={bodyPart}
              onChange={e => { setBodyPart(e.target.value); setPage(1); }}
            />
          </Card>
        </Col>

        {/* Content */}
        <Col xs={24} md={18} lg={19}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
          ) : data && data.items.length > 0 ? (
            <>
              <Row gutter={[12, 12]}>
                {data.items.map(renderActionCard)}
              </Row>
              <div style={{ textAlign: 'center', marginTop: 24 }}>
                <Pagination
                  current={page}
                  pageSize={pageSize}
                  total={data.total}
                  showSizeChanger
                  showTotal={t => `共 ${t} 个动作`}
                  onChange={(p, ps) => { setPage(p); setPageSize(ps); }}
                />
              </div>
            </>
          ) : (
            <Empty description="暂无动作数据" />
          )}
        </Col>
      </Row>

      {renderDetailModal()}

      {/* Create Action Modal */}
      <Modal
        title="添加自定义动作"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={handleCreate}
        confirmLoading={creating}
        width={600}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item label="动作名称" name="name" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如：弹力带划船" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="分类" name="category"><Input placeholder="如：上肢拉" /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="难度" name="difficulty" initialValue={2}>
                <Slider min={1} max={5} marks={{ 1: '1', 3: '3', 5: '5' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="家族标识" name="family"><Input placeholder="如：pushup" /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="家族名称" name="family_name"><Input placeholder="如：俯卧撑" /></Form.Item>
            </Col>
          </Row>
          <Form.Item label="描述" name="description"><Input.TextArea rows={3} placeholder="动作描述..." /></Form.Item>
          <Form.Item label="步骤" name="steps">
            <Select mode="tags" placeholder="输入步骤后按回车" />
          </Form.Item>
          <Form.Item label="动作要点" name="cues">
            <Select mode="tags" placeholder="输入要点后按回车" />
          </Form.Item>
          <Form.Item label="目标部位" name="target_body_parts">
            <Select mode="tags" placeholder="输入部位后按回车" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
