import { useState } from 'react';
import { Upload, Button, message, Image, Modal, Progress } from 'antd';
import { UploadOutlined, DeleteOutlined, EyeOutlined, VideoCameraOutlined } from '@ant-design/icons';
import type { UploadFile, RcFile } from 'antd/es/upload/interface';
import { coachApi } from '../services/api';

interface MediaUploadProps {
  actionId: number;
  mediaType: 'image' | 'video' | 'thumbnail';
  existingMedia?: Array<{
    id: number;
    media_type: string;
    file_path: string;
    url: string;
    original_filename?: string;
    file_size?: number;
  }>;
  onSuccess?: () => void;
  onDelete?: (mediaId: number) => void;
}

const MEDIA_ACCEPT: Record<string, string> = {
  image: 'image/jpg,image/jpeg,image/png,image/gif,image/webp',
  video: 'video/mp4,video/webm',
  thumbnail: 'image/jpg,image/jpeg,image/png,image/gif,image/webp',
};

const MAX_SIZES: Record<string, number> = {
  image: 10 * 1024 * 1024,
  video: 100 * 1024 * 1024,
  thumbnail: 5 * 1024 * 1024,
};

/**
 * 动作媒体上传组件
 * 支持图片缩略图、示例图片、示例视频的上传和预览
 */
export default function MediaUpload({
  actionId,
  mediaType,
  existingMedia = [],
  onSuccess,
  onDelete,
}: MediaUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewUrl, setPreviewUrl] = useState('');
  const [previewIsVideo, setPreviewIsVideo] = useState(false);

  const filteredMedia = existingMedia.filter(m => m.media_type === mediaType);

  const beforeUpload = (file: RcFile): boolean => {
    const accept = MEDIA_ACCEPT[mediaType];
    const maxSize = MAX_SIZES[mediaType];

    const allowedTypes = accept.split(',');
    const isAllowedType = allowedTypes.some(t => file.type === t.trim());
    if (!isAllowedType) {
      message.error(`不支持的文件类型，允许: ${accept}`);
      return false;
    }

    if (file.size > maxSize) {
      const sizeMB = Math.round(maxSize / 1024 / 1024);
      message.error(`文件大小不能超过 ${sizeMB}MB`);
      return false;
    }

    return true;
  };

  const handleUpload = async (file: RcFile): Promise<void> => {
    setUploading(true);
    setUploadProgress(0);
    try {
      await coachApi.uploadActionMedia(actionId, file, mediaType, (pct: number) => {
        setUploadProgress(pct);
      });
      message.success('上传成功');
      onSuccess?.();
    } catch (e: any) {
      const detail = e?.response?.data?.detail || '上传失败';
      message.error(detail);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
    // Prevent default upload behavior (we handle it manually via API)
    return undefined as any;
  };

  const handlePreview = (item: typeof filteredMedia[0]) => {
    const url = item.url || `/media/uploads/actions/${item.file_path}`;
    setPreviewUrl(url);
    setPreviewIsVideo(item.media_type === 'video');
    setPreviewVisible(true);
  };

  const handleDelete = (mediaId: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '删除后不可恢复，是否继续？',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => {
        coachApi.deleteActionMedia(mediaId).then(() => {
          message.success('已删除');
          onDelete?.(mediaId);
        }).catch(() => {
          message.error('删除失败');
        });
      },
    });
  };

  const items: UploadFile[] = filteredMedia.map(m => ({
    uid: String(m.id),
    name: m.original_filename || `media_${m.id}`,
    status: 'done' as const,
    url: m.url || `/media/uploads/actions/${m.file_path}`,
    thumbUrl: m.media_type !== 'video' ? (m.url || `/media/uploads/actions/${m.file_path}`) : undefined,
  }));

  return (
    <div>
      <Upload
        listType={mediaType === 'image' || mediaType === 'thumbnail' ? 'picture-card' : 'text'}
        fileList={items}
        beforeUpload={beforeUpload}
        customRequest={({ file }) => handleUpload(file as RcFile)}
        onRemove={(file) => {
          const mediaId = Number(file.uid);
          if (mediaId) handleDelete(mediaId);
          return false; // Prevent default remove, we handle in handleDelete
        }}
        onPreview={(file) => {
          const media = filteredMedia.find(m => m.id === Number(file.uid));
          if (media) handlePreview(media);
        }}
        itemRender={(originNode, file) => {
          if (mediaType === 'video') {
            return (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
                <VideoCameraOutlined style={{ fontSize: 18, color: 'var(--color-primary)' }} />
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {file.name}
                </span>
                <Button
                  type="link"
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={() => {
                    const media = filteredMedia.find(m => m.id === Number(file.uid));
                    if (media) handlePreview(media);
                  }}
                >
                  预览
                </Button>
                <Button
                  type="link"
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={() => {
                    const mediaId = Number(file.uid);
                    if (mediaId) handleDelete(mediaId);
                  }}
                />
              </div>
            );
          }
          return originNode;
        }}
      >
        {uploading ? (
          <div style={{ textAlign: 'center' }}>
            <Progress type="circle" percent={uploadProgress} size={40} />
          </div>
        ) : (
          <div>
            <UploadOutlined />
            <div style={{ marginTop: 8 }}>
              {mediaType === 'thumbnail' ? '上传缩略图' : mediaType === 'video' ? '上传视频' : '上传图片'}
            </div>
          </div>
        )}
      </Upload>

      <Modal
        open={previewVisible}
        footer={null}
        onCancel={() => setPreviewVisible(false)}
        width={previewIsVideo ? 720 : 'auto'}
        title={previewIsVideo ? '视频预览' : '图片预览'}
      >
        {previewIsVideo ? (
          <video
            controls
            style={{ width: '100%', maxHeight: '70vh' }}
            src={previewUrl}
          />
        ) : (
          <Image
            src={previewUrl}
            alt="预览"
            style={{ maxWidth: '100%', maxHeight: '70vh' }}
          />
        )}
      </Modal>
    </div>
  );
}
