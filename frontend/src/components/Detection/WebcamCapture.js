import { useState, useRef, useEffect, useContext } from 'react';
import { Form, Button, Alert, Card } from 'react-bootstrap';
import { ConfigContext } from '../../context/ConfigContext';
import './Detection.css';

const WebcamCapture = ({ sessionId, onDetectionComplete }) => {
  const { config } = useContext(ConfigContext);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'environment'
        }
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
        setIsStreaming(true);
        setError('');
        setSuccess('✓ Webcam started successfully!');
      }
    } catch (err) {
      setError('Failed to access webcam. Please check permissions.');
      console.error('Webcam error:', err);
    }
  };

  const stopWebcam = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
      setIsStreaming(false);
      setSuccess('');
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    }
  };

  useEffect(() => {
    return () => {
      stopWebcam();
    };
  }, []);

  return (
    <Card className="detection-card shadow-sm">
      <Card.Header className="bg-success text-white">
        <h5 className="mb-0">📷 Webcam Capture</h5>
      </Card.Header>
      <Card.Body>
        {error && <Alert variant="danger">{error}</Alert>}
        {success && <Alert variant="success">{success}</Alert>}

        <div className="mb-3">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{
              width: '100%',
              height: 'auto',
              backgroundColor: '#000',
              borderRadius: '8px'
            }}
          />
        </div>

        <div className="d-flex gap-2">
          <Button
            variant={isStreaming ? 'danger' : 'success'}
            onClick={isStreaming ? stopWebcam : startWebcam}
            className="w-100"
          >
            {isStreaming ? '⏹ Stop Webcam' : '▶ Start Webcam'}
          </Button>
        </div>

        {isStreaming && (
          <div className="mt-3 p-3 bg-light rounded">
            <p className="mb-0 text-muted">
              <strong>Note:</strong> Webcam detection will be available soon. Currently showing live preview.
            </p>
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default WebcamCapture;
