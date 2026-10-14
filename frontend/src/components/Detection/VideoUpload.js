import { useState, useRef, useContext } from 'react';
import { Form, Button, Alert, ProgressBar, Card } from 'react-bootstrap';
import { ConfigContext } from '../../context/ConfigContext';
import { detectionAPI } from '../../api/detection';
import './Detection.css';

const VideoUpload = ({ sessionId, onDetectionComplete }) => {
  const { config } = useContext(ConfigContext);
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [progress, setProgress] = useState(0);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState(null);
  const fileInputRef = useRef(null);
  const previewVideoRef = useRef(null);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!['video/mp4', 'video/x-msvideo', 'video/quicktime'].includes(file.type)) {
      setError('Please upload a valid video file (MP4, AVI, MOV)');
      return;
    }

    // Validate file size (max 100MB)
    if (file.size > 100 * 1024 * 1024) {
      setError('File size must be less than 100MB');
      return;
    }

    setSelectedFile(file);
    setVideoPreviewUrl(URL.createObjectURL(file));
    setError('');
    setSuccess('');
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a video file');
      return;
    }

    setLoading(true);
    setProgress(0);
    setError('');
    setSuccess('');

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 10, 90));
      }, 500);

      const response = await detectionAPI.processVideo(
        selectedFile,
        config,
        sessionId
      );

      clearInterval(progressInterval);
      setProgress(100);

      const { results, statistics } = response.data;
      
      setSuccess(
        `✓ Video processed successfully! ${results.length} detections found.`
      );
      
      // Call parent callback with results
      if (onDetectionComplete) {
        onDetectionComplete(results, statistics);
      }

      // Reset form
      setSelectedFile(null);
      if (videoPreviewUrl) {
        URL.revokeObjectURL(videoPreviewUrl);
        setVideoPreviewUrl(null);
      }
      if (fileInputRef.current) fileInputRef.current.value = '';
      
      setTimeout(() => {
        setProgress(0);
        setSuccess('');
      }, 3000);
    } catch (err) {
      const message =
        err.response?.data?.error || 'Video processing failed. Please try again.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="detection-card shadow-sm">
      <Card.Header className="bg-primary text-white">
        <h5 className="mb-0">📹 Upload Video</h5>
      </Card.Header>
      <Card.Body>
        {error && <Alert variant="danger">{error}</Alert>}
        {success && <Alert variant="success">{success}</Alert>}

        <Form.Group className="mb-3">
          <Form.Label>Select Video File</Form.Label>
          <Form.Control
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            accept="video/*"
            disabled={loading}
          />
          <Form.Text className="text-muted">
            Supported formats: MP4, AVI, MOV (Max 100MB)
          </Form.Text>
        </Form.Group>

        {selectedFile && (
          <div className="mb-3">
            <div className="mb-2 p-3 bg-light rounded">
              <p className="mb-1">
                <strong>Selected:</strong> {selectedFile.name}
              </p>
              <p className="mb-0 text-muted">
                Size: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
            {videoPreviewUrl && (
              <div className="video-preview-container" style={{ position: 'relative', backgroundColor: '#000', borderRadius: '8px', overflow: 'hidden' }}>
                <video
                  ref={previewVideoRef}
                  src={videoPreviewUrl}
                  autoPlay
                  loop
                  muted
                  playsInline
                  style={{ width: '100%', height: 'auto', display: 'block' }}
                />
                {loading && (
                  <div style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    color: 'white',
                    padding: '10px 20px',
                    borderRadius: '5px',
                    fontSize: '14px',
                    fontWeight: 'bold'
                  }}>
                    Processing Video...
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {loading && progress > 0 && (
          <div className="mb-3">
            <ProgressBar now={progress} label={`${progress}%`} />
          </div>
        )}

        <Button
          variant="primary"
          onClick={handleUpload}
          disabled={!selectedFile || loading}
          className="w-100"
        >
          {loading ? 'Processing Video...' : 'Upload & Process'}
        </Button>
      </Card.Body>
    </Card>
  );
};

export default VideoUpload;
