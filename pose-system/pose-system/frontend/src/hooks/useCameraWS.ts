import { useRef, useCallback, useEffect } from "react";
import { message } from "antd";

/**
 * Shared camera + WebSocket lifecycle hook.
 *
 * Encapsulates: getUserMedia, frame capture via canvas.toDataURL,
 * WebSocket creation/cleanup, and unmount cleanup.
 *
 * Usage:
 *   const { videoRef, canvasRef, startCamera, connectWS, cleanup, wsRef } = useCameraWS({
 *     onMessage: (data) => { ... },
 *     captureInterval: 200,
 *     frameFieldName: 'image',  // FMS uses 'image', others use 'data'
 *   });
 */
interface UseCameraWSOptions {
  /** Callback for each parsed WebSocket message */
  onMessage: (data: any) => void;
  /** Frame capture interval in ms (default: 150) */
  captureInterval?: number;
  /** JSON key for the base64 frame: 'data' (default) or 'image' (FMS) */
  frameFieldName?: "data" | "image";
  /** Whether to register beforeunload/pagehide listeners (default: false) */
  withUnloadListeners?: boolean;
  /** Called on WebSocket error */
  onError?: () => void;
  /** Called on WebSocket close */
  onClose?: (e: CloseEvent) => void;
}

export function useCameraWS(options: UseCameraWSOptions) {
  const {
    onMessage,
    captureInterval = 150,
    frameFieldName = "data",
    withUnloadListeners = false,
    onError,
    onClose,
  } = options;

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const intervalRef = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);

  // Stable callback ref — avoids stale closures in setInterval
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  // ── Camera ────────────────────────────────────────────

  const startCamera = useCallback(async (): Promise<boolean> => {
    if (!navigator.mediaDevices?.getUserMedia) {
      message.error("摄像头不可用：请使用 localhost 或 HTTPS 访问");
      return false;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      return true;
    } catch (e: any) {
      message.error("无法访问摄像头: " + (e.message || ""));
      return false;
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, []);

  // ── Frame Capture ─────────────────────────────────────

  const startFrameCapture = useCallback((): boolean => {
    clearInterval(intervalRef.current);
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video || !video.videoWidth) return false;
    const ctx = canvas.getContext("2d");
    if (!ctx) return false;

    intervalRef.current = window.setInterval(() => {
      if (!video.videoWidth) return;
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);
      const b64 = canvas.toDataURL("image/jpeg", 0.6);
      ws.send(JSON.stringify({ type: "frame", [frameFieldName]: b64 }));
    }, captureInterval);
    return true;
  }, [captureInterval, frameFieldName]);

  const stopFrameCapture = useCallback(() => {
    clearInterval(intervalRef.current);
    intervalRef.current = 0;
  }, []);

  // ── WebSocket ─────────────────────────────────────────

  const connectWS = useCallback(
    (wsPathOrUrl: string, startPayload?: object): WebSocket => {
      // Build full URL if path is relative
      let url: string;
      if (wsPathOrUrl.startsWith("ws://") || wsPathOrUrl.startsWith("wss://")) {
        url = wsPathOrUrl;
      } else {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        url = `${protocol}//${window.location.host}${wsPathOrUrl}`;
      }

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (startPayload) {
          ws.send(JSON.stringify(startPayload));
        }
        // Start frame capture after a short delay to let video stabilize
        setTimeout(() => startFrameCapture(), 300);
      };

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          onMessageRef.current(data);
        } catch (err) {
          console.error("[useCameraWS] Parse error:", err);
        }
      };

      ws.onerror = () => {
        message.error("WebSocket 连接失败");
        onError?.();
      };

      ws.onclose = (e) => {
        onCloseRef.current?.(e);
      };

      return ws;
    },
    [startFrameCapture, onError]
  );

  const sendMessage = useCallback((msg: object) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  }, []);

  // ── Cleanup ───────────────────────────────────────────

  const cleanup = useCallback(() => {
    stopFrameCapture();
    stopCamera();
    if (wsRef.current) {
      wsRef.current.onclose = null; // prevent onClose callback during intentional cleanup
      wsRef.current.close();
      wsRef.current = null;
    }
  }, [stopFrameCapture, stopCamera]);

  // Unmount cleanup
  useEffect(() => {
    return () => cleanup();
  }, [cleanup]);

  // Optional: beforeunload/pagehide listeners
  useEffect(() => {
    if (!withUnloadListeners) return;
    const handler = () => cleanup();
    window.addEventListener("beforeunload", handler);
    window.addEventListener("pagehide", handler);
    return () => {
      window.removeEventListener("beforeunload", handler);
      window.removeEventListener("pagehide", handler);
    };
  }, [withUnloadListeners, cleanup]);

  return {
    videoRef,
    canvasRef,
    wsRef,
    startCamera,
    stopCamera,
    startFrameCapture,
    stopFrameCapture,
    connectWS,
    sendMessage,
    cleanup,
  };
}
