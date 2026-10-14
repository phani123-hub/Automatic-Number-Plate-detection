import { useState, useRef, useEffect, useContext } from 'react';
import { Button, Alert, Card, Spinner } from 'react-bootstrap';
import { ConfigContext } from '../../context/ConfigContext';
import { detectionAPI } from '../../api/detection';
import './Detection.css';

const WebcamLive = ({ sessionId, onDetectionComplete }) => {
  const { config } = useContext(ConfigContext);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [isActive, setIsActive] = useState(false);
  const [error, setError] = useState('');
  const [frameCount, setFrameCount] = useState(0);
  const [detectionCount, setDetectionCount] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsActive(true);
        setError('');
        startFrameCapture();
      }
    } catch (err) {
      setError('Failed to access webcam. Check permissions.');
      console.error(err);
    }
  };

  const stopWebcam = () => {
    if (videoRef.current?.srcObject) {
      videoRef.current.srcObject.getTracks().forEach((track) => track.stop());
    }
    setIsActive(false);
    setFrameCount(0);
    setDetectionCount(0);
  };

  const startFrameCapture = () => {
    const captureInterval = setInterval(async () => {
      if (!videoRef.current || !canvasRef.current || !isActive) {
        clearInterval(captureInterval);
        return;
      }

      try {
        const ctx = canvasRef.current.getContext('2d');
        canvasRef.current.width = videoRef.current.videoWidth;
        canvasRef.current.height = videoRef.current.videoHeight;
        
        ctx.drawImage(videoRef.current, 0, 0);
        
        const frameBase64 = canvasRef.current.toDataURL('image/jpeg').split(',')[1];
        
        setFrameCount((prev) => prev + 1);
        
        // Send every 5th frame to backend (reduces server load)
        if (frameCount % 5 === 0) {
          setIsProcessing(true);
          const response = await detectionAPI.processFrame(
            frameBase64,
            config,
            sessionId
          );

          if (response.data.results?.length > 0) {
            setDetectionCount((prev) => prev + response.data.results.length);
            if (onDetectionComplete) {
              onDetectionComplete(response.data.results, null);
            }
          }
          setIsProcessing(false);
        }
      } catch (err) {
        console.error('Frame processing error:', err);
      }
    }, 200); // 5 FPS

    return () => clearInterval(captureInterval);
  };

  return (
    <Card className="detection-card shadow-sm">
      <Card.Header className="bg-success text-white">
        <h5 className="mb-0">🎥 Live Webcam</h5>
      </Card.Header>
      <Card.Body>
        {error && <Alert variant="danger">{error}</Alert>}

        <div className="webcam-container mb-3">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            className="webcam-video"
            style={{
              width: '100%',
              borderRadius: '8px',
              backgroundColor: '#000',
            }}
          />
          <canvas
            ref={canvasRef}
            style={{ display: 'none' }}
          />
        </div>

        <div className="stats-row mb-3">
          <div className="stat-item">
            <span className="stat-label">Frames:</span>
            <span className="stat-value">{frameCount}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Detections:</span>
            <span className="stat-value">{detectionCount}</span>
          </div>
          {isProcessing && (
            <div className="stat-item">
              <Spinner animation="border" size="sm" className="me-2" />
              <span>Processing...</span>
            </div>
          )}
        </div>

        <div className="d-grid gap-2">
          {!isActive ? (
            <Button variant="success" size="lg" onClick={startWebcam}>
              🎥 Start Webcam
            </Button>
          ) : (
            <Button variant="danger" size="lg" onClick={stopWebcam}>
              ⏹ Stop Webcam
            </Button>
          )}
        </div>
      </Card.Body>
    </Card>
  );
};

export default WebcamLive;
