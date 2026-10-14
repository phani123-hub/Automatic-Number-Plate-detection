import { useState, useRef, useContext } from 'react';
import { Card, Form, Button, Alert, Badge, Spinner } from 'react-bootstrap';
import { ConfigContext } from '../../context/ConfigContext';
import { useDetectionStats } from '../../hooks/useDetectionStats';
import './Detection.css';

/**
 * RTSPStream Component - Stream from CCTV/IP Camera via RTSP
 * Connects to RTSP URL and streams with live detection
 */
const RTSPStream = () => {
  const { config } = useContext(ConfigContext);
  const { stats, updateFrameCount, addDetection, resetStats, setFPS } = useDetectionStats();

  // RTSP configuration
  const [rtspUrl, setRtspUrl] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // Streaming state
  const [isStreaming, setIsStreaming] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [fps, setFps] = useState(0);
  const [message, setMessage] = useState('Enter RTSP URL to start streaming');
  const [messageType, setMessageType] = useState('info');

  // Refs
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const fpsCounterRef = useRef({ lastTime: Date.now(), frameCount: 0 });

  /**
   * Start RTSP streaming
   */
  const handleStartStream = async () => {
    if (!rtspUrl.trim()) {
      setMessage('Please enter RTSP URL');
      setMessageType('warning');
      return;
    }

    if (!canvasRef.current) {
      setMessage('Error: Canvas not initialized');
      setMessageType('danger');
      return;
    }

    setIsStreaming(true);
    resetStats();
    setMessage('🔗 Connecting to RTSP stream...');
    setMessageType('info');

    try {
      // Prepare RTSP URL with credentials if provided
      let finalUrl = rtspUrl;
      if (username && password) {
        const urlParts = rtspUrl.replace('rtsp://', '').split('/');
        finalUrl = `rtsp://${username}:${password}@${urlParts.join('/')}`;
      } else if (username) {
        const urlParts = rtspUrl.replace('rtsp://', '').split('/');
        finalUrl = `rtsp://${username}@${urlParts.join('/')}`;
      }

      // Call backend to start streaming
      const response = await fetch('/api/detection/rtsp-stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        },
        body: JSON.stringify({
          rtsp_url: finalUrl,
          config: config
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setMessage('✅ Connected! Starting detection...');
      setMessageType('success');

      // Start receiving frames
      pollFrames();
    } catch (err) {
      console.error('RTSP connection error:', err);
      setMessage(`❌ Connection failed: ${err.message}`);
      setMessageType('danger');
      setIsStreaming(false);
    }
  };

  /**
   * Poll backend for frames
   */
  const pollFrames = async () => {
    if (!isStreaming || isPaused) {
      setTimeout(pollFrames, 100);
      return;
    }

    try {
      const response = await fetch('/api/detection/rtsp-frame', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        }
      });

      if (!response.ok) {
        if (response.status === 503) {
          // Stream not available yet
          setTimeout(pollFrames, 100);
          return;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.frame && data.detections) {
        // Draw frame and detections
        drawFrameWithDetections(data.frame, data.detections);

        // Update stats
        data.detections.forEach(det => {
          addDetection(det.confidence || 0.8, det.is_valid || false);
        });

        updateFrameCount();
        updateFPS();
      }

      // Continue polling
      setTimeout(pollFrames, 33); // ~30 FPS
    } catch (err) {
      console.error('Frame poll error:', err);
      setMessage(`❌ Stream error: ${err.message}`);
      setMessageType('danger');
      setIsStreaming(false);
    }
  };

  /**
   * Draw frame with detections on canvas
   */
  const drawFrameWithDetections = (base64Frame, detections) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;

      // Draw frame
      ctx.drawImage(img, 0, 0);

      // Draw detections
      drawDetections(ctx, detections, img.width, img.height);
    };

    img.onerror = () => {
      console.error('Failed to load frame image');
    };

    img.src = `data:image/jpeg;base64,${base64Frame}`;
  };

  /**
   * Draw detection boxes
   */
  const drawDetections = (ctx, detectionList, width, height) => {
    detectionList.forEach(detection => {
      if (!detection.box || !Array.isArray(detection.box)) return;

      const [x1, y1, x2, y2] = detection.box;
      const boxWidth = x2 - x1;
      const boxHeight = y2 - y1;

      const color = detection.is_valid ? '#00FF00' : '#FFFF00';
      const lineWidth = 3;

      // Draw rectangle
      ctx.strokeStyle = color;
      ctx.lineWidth = lineWidth;
      ctx.strokeRect(x1, y1, boxWidth, boxHeight);

      // Draw text background
      const confidence = detection.confidence ? (detection.confidence * 100).toFixed(2) : '0.00';
      const text = `${detection.text || 'Unknown'} (${confidence}%)`;

      ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
      ctx.fillRect(x1, Math.max(0, y1 - 30), 250, 30);

      // Draw text
      ctx.fillStyle = color;
      ctx.font = 'bold 16px Arial';
      ctx.fillText(text, x1 + 5, y1 - 8);

      // Draw track ID
      if (detection.track_id) {
        ctx.fillStyle = '#00FFFF';
        ctx.font = 'bold 12px Arial';
        ctx.fillText(`Track: ${detection.track_id}`, x1 + 5, Math.min(height - 5, y2 + 20));
      }
    });

    // Draw FPS
    ctx.fillStyle = '#00FF00';
    ctx.font = 'bold 14px Arial';
    ctx.fillText(`FPS: ${fps.toFixed(1)}`, 10, 30);
  };

  /**
   * Update FPS counter
   */
  const updateFPS = () => {
    const now = Date.now();
    const elapsed = (now - fpsCounterRef.current.lastTime) / 1000;

    fpsCounterRef.current.frameCount++;

    if (elapsed >= 1) {
      const currentFps = fpsCounterRef.current.frameCount / elapsed;
      setFps(currentFps);
      setFPS(currentFps);
      fpsCounterRef.current = { lastTime: now, frameCount: 0 };
    }
  };

  /**
   * Toggle pause
   */
  const togglePause = () => {
    setIsPaused(!isPaused);
    setMessage(isPaused ? '▶ Resumed' : '⏸ Paused');
    setTimeout(() => setMessage(''), 2000);
  };

  /**
   * Stop streaming
   */
  const handleStop = async () => {
    setIsStreaming(false);
    setMessage('Stopping stream...');

    try {
      await fetch('/api/detection/rtsp-stop', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        }
      });
    } catch (err) {
      console.error('Stop error:', err);
    }

    setMessage('Stream stopped');
    setMessageType('info');
  };

  /**
   * Reset
   */
  const handleReset = async () => {
    if (isStreaming) {
      await handleStop();
    }

    setRtspUrl('');
    setUsername('');
    setPassword('');
    resetStats();
    setFps(0);
    setMessage('Ready to connect');
    setMessageType('info');
  };

  return (
    <div className="rtsp-stream">
      {/* Configuration Card */}
      <Card className="mb-3">
        <Card.Header className="bg-dark text-white">
          <h6 className="mb-0">📡 RTSP Stream Configuration</h6>
        </Card.Header>
        <Card.Body>
          {/* RTSP URL Input */}
          <Form.Group className="mb-3">
            <Form.Label className="fw-bold">🔗 RTSP URL</Form.Label>
            <Form.Control
              type="text"
              placeholder="rtsp://192.168.1.100:554/stream"
              value={rtspUrl}
              onChange={(e) => setRtspUrl(e.target.value)}
              disabled={isStreaming}
            />
            <Form.Text className="text-muted">
              Example: rtsp://192.168.1.100:554/live1
            </Form.Text>
          </Form.Group>

          {/* Username Input */}
          <Form.Group className="mb-3">
            <Form.Label className="fw-bold">👤 Username (Optional)</Form.Label>
            <Form.Control
              type="text"
              placeholder="admin"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isStreaming}
            />
          </Form.Group>

          {/* Password Input */}
          <Form.Group className="mb-3">
            <Form.Label className="fw-bold">🔐 Password (Optional)</Form.Label>
            <Form.Control
              type="password"
              placeholder="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isStreaming}
            />
          </Form.Group>

          {/* Message */}
          {message && (
            <Alert variant={messageType} className="mb-3">
              {message}
            </Alert>
          )}

          {/* Action Buttons */}
          <div className="d-grid gap-2 d-md-flex justify-content-md-start">
            <Button
              variant="primary"
              size="lg"
              onClick={handleStartStream}
              disabled={isStreaming}
            >
              {isStreaming && <Spinner animation="border" size="sm" className="me-2" />}
              🟢 Start Streaming
            </Button>

            {isStreaming && (
              <>
                <Button variant="warning" size="lg" onClick={togglePause}>
                  {isPaused ? '▶ Resume' : '⏸ Pause'}
                </Button>
                <Button variant="danger" size="lg" onClick={handleStop}>
                  ⏹ Stop
                </Button>
              </>
            )}

            {!isStreaming && (
              <Button variant="secondary" size="lg" onClick={handleReset}>
                🔄 Reset
              </Button>
            )}
          </div>
        </Card.Body>
      </Card>

      {/* Canvas Display */}
      {isStreaming && (
        <Card className="mb-3">
          <Card.Header className="bg-dark text-white">
            <h6 className="mb-0">
              📹 Live RTSP Stream
              {isStreaming && !isPaused && (
                <Badge bg="success" className="ms-2">
                  <Spinner animation="grow" size="sm" className="me-1" />
                  STREAMING
                </Badge>
              )}
              {isPaused && (
                <Badge bg="warning" className="ms-2">
                  ⏸ PAUSED
                </Badge>
              )}
            </h6>
          </Card.Header>
          <Card.Body className="p-0 bg-black">
            <canvas
              ref={canvasRef}
              style={{
                width: '100%',
                height: 'auto',
                display: 'block',
                backgroundColor: '#000'
              }}
            />
          </Card.Body>
        </Card>
      )}

      {/* Statistics */}
      {isStreaming && (
        <Card>
          <Card.Header className="bg-dark text-white">
            <h6 className="mb-0">📊 Live Statistics</h6>
          </Card.Header>
          <Card.Body>
            <div className="row text-center">
              <div className="col-md-2">
                <small className="text-muted">Frames</small>
                <h5 className="text-primary">{stats.frameCount}</h5>
              </div>
              <div className="col-md-2">
                <small className="text-muted">Detections</small>
                <h5 className="text-warning">{stats.detectionCount}</h5>
              </div>
              <div className="col-md-2">
                <small className="text-muted">FPS</small>
                <h5 className="text-success">{fps.toFixed(1)}</h5>
              </div>
              <div className="col-md-2">
                <small className="text-muted">Vehicles</small>
                <h5 className="text-info">{stats.uniqueVehicles}</h5>
              </div>
              <div className="col-md-2">
                <small className="text-muted">Avg Conf</small>
                <h5 className="text-success">{(stats.avgConfidence * 100).toFixed(2)}%</h5>
              </div>
              <div className="col-md-2">
                <small className="text-muted">Process Time</small>
                <h5 className="text-info">{stats.processingTime.toFixed(2)}ms</h5>
              </div>
            </div>
          </Card.Body>
        </Card>
      )}
    </div>
  );
};

export default RTSPStream;
