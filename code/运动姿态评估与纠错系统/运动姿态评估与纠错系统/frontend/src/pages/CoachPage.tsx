import { useEffect, useState } from 'react';
import { Card, Table, Button, Modal, Input, Tag, Space, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import axios from 'axios';

const api = axios.create({ baseURL: '/api' });
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config;
});

export default function CoachPage() {
  const [students, setStudents] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [className, setClassName] = useState('');
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [selectedClass, setSelectedClass] = useState<number | null>(null);
  const [studentId, setStudentId] = useState('');

  useEffect(() => {
    api.get('/coach/students').then(r => setStudents(r.data)).catch(() => {});
  }, []);

  const createClass = async () => {
    try {
      await api.post('/coach/classes', null, { params: { name: className } });
      message.success('班级创建成功');
      setModalOpen(false);
      setClassName('');
    } catch { message.error('创建失败'); }
  };

  const addStudent = async () => {
    if (!selectedClass || !studentId) return;
    try {
      await api.post(`/coach/classes/${classId}/students`, null, { params: { student_id: Number(studentId) } });
      message.success('学员已添加');
      setAddModalOpen(false);
      api.get('/coach/students').then(r => setStudents(r.data));
    } catch { message.error('添加失败'); }
  };

  const columns = [
    { title: '学员ID', dataIndex: 'id' },
    { title: '用户名', dataIndex: 'username' },
    { title: '手机', dataIndex: 'phone', render: (v: string) => v || '-' },
    { title: '班级', dataIndex: 'class', render: (v: string) => v ? <Tag>{v}</Tag> : '-' },
  ];

  return (
    <div>
      <Card title="学员管理" extra={<Space>
        <Button icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建班级</Button>
        <Button onClick={() => setAddModalOpen(true)}>添加学员</Button>
      </Space>}>
        <Table dataSource={students} columns={columns} rowKey="id" size="small" />
      </Card>

      <Modal title="新建班级" open={modalOpen} onOk={createClass} onCancel={() => setModalOpen(false)}>
        <Input placeholder="班级名称" value={className} onChange={e => setClassName(e.target.value)} />
      </Modal>

      <Modal title="添加学员" open={addModalOpen} onOk={addStudent} onCancel={() => setAddModalOpen(false)}>
        <Input placeholder="班级ID" style={{ marginBottom: 8 }} onChange={e => setSelectedClass(Number(e.target.value))} />
        <Input placeholder="学员ID" onChange={e => setStudentId(e.target.value)} />
      </Modal>
    </div>
  );
}
