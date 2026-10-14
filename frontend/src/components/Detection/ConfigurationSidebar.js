import { Card, Form, Badge } from 'react-bootstrap';
import './ConfigurationSidebar.css';

const ConfigurationSidebar = ({ config, onConfigChange }) => {
  const handleChange = (key, value) => {
    onConfigChange({ ...config, [key]: value });
  };

  return (
    <div className="config-sidebar">
      {/* Input Source */}
      <Card className="config-card">
        <Card.Header className="config-header">
          <h6>📹 Input Source</h6>
        </Card.Header>
        <Card.Body>
          <Form.Group className="mb-3">
            <Form.Label className="config-label">Source Type</Form.Label>
            <Form.Select
              value={config.input_source || 'webcam'}
              onChange={(e) => handleChange('input_source', e.target.value)}
            >
              <option value="webcam">Webcam</option>
              <option value="video">Video File</option>
              <option value="rtsp">RTSP Stream</option>
            </Form.Select>
          </Form.Group>

          {config.input_source === 'video' && (
            <Form.Group className="mb-3">
              <Form.Label className="config-label">Video Path</Form.Label>
              <Form.Control
                type="text"
                placeholder="data/sample_videos/test.mp4"
                value={config.video_path || ''}
                onChange={(e) => handleChange('video_path', e.target.value)}
                size="sm"
              />
            </Form.Group>
          )}

          {config.input_source === 'rtsp' && (
            <Form.Group className="mb-3">
              <Form.Label className="config-label">RTSP URL</Form.Label>
              <Form.Control
                type="text"
                placeholder="rtsp://..."
                value={config.rtsp_url || ''}
                onChange={(e) => handleChange('rtsp_url', e.target.value)}
                size="sm"
              />
            </Form.Group>
          )}
        </Card.Body>
      </Card>

      {/* Detection Settings */}
      <Card className="config-card">
        <Card.Header className="config-header">
          <h6>🎯 Detection</h6>
        </Card.Header>
        <Card.Body>
          <Form.Group className="mb-3">
            <Form.Label className="config-label">
              Confidence Threshold
              <Badge bg="info" className="ms-2">
                {(config.conf_threshold || 0.3).toFixed(2)}
              </Badge>
            </Form.Label>
            <Form.Range
              min="0"
              max="1"
              step="0.05"
              value={config.conf_threshold || 0.3}
              onChange={(e) => handleChange('conf_threshold', parseFloat(e.target.value))}
            />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label className="config-label">
              IoU Threshold
              <Badge bg="info" className="ms-2">
                {(config.iou_threshold || 0.45).toFixed(2)}
              </Badge>
            </Form.Label>
            <Form.Range
              min="0"
              max="1"
              step="0.05"
              value={config.iou_threshold || 0.45}
              onChange={(e) => handleChange('iou_threshold', parseFloat(e.target.value))}
            />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label className="config-label">Device</Form.Label>
            <Form.Select
              value={config.device || 'cpu'}
              onChange={(e) => handleChange('device', e.target.value)}
            >
              <option value="cpu">CPU</option>
              <option value="cuda">GPU (CUDA)</option>
            </Form.Select>
            <small className="text-muted d-block mt-1">
              {config.device === 'cuda' 
                ? '⚡ GPU Mode (Faster)' 
                : '🐢 CPU Mode (Slower)'}
            </small>
          </Form.Group>
        </Card.Body>
      </Card>

      {/* Preprocessing */}
      <Card className="config-card">
        <Card.Header className="config-header">
          <h6>🌙 Preprocessing</h6>
        </Card.Header>
        <Card.Body>
          <Form.Check
            type="checkbox"
            label="Enable Preprocessing"
            checked={config.enable_preprocessing !== false}
            onChange={(e) => handleChange('enable_preprocessing', e.target.checked)}
            className="mb-2"
          />

          <hr className="my-2" />

          <Form.Check
            type="checkbox"
            label="CLAHE (Contrast Enhancement)"
            checked={config.enable_clahe !== false}
            onChange={(e) => handleChange('enable_clahe', e.target.checked)}
            className="mb-2"
          />

          {config.enable_clahe !== false && (
            <Form.Group className="mb-3 ms-3">
              <Form.Label className="config-label">
                CLAHE Clip Limit
                <Badge bg="warning" className="ms-2">
                  {(config.clip_limit || 2.0).toFixed(1)}
                </Badge>
              </Form.Label>
              <Form.Range
                min="1"
                max="5"
                step="0.1"
                value={config.clip_limit || 2.0}
                onChange={(e) => handleChange('clip_limit', parseFloat(e.target.value))}
              />
            </Form.Group>
          )}

          <Form.Check
            type="checkbox"
            label="Denoising"
            checked={config.enable_denoise !== false}
            onChange={(e) => handleChange('enable_denoise', e.target.checked)}
            className="mb-2"
          />

          <Form.Check
            type="checkbox"
            label="Auto Exposure"
            checked={config.enable_exposure !== false}
            onChange={(e) => handleChange('enable_exposure', e.target.checked)}
          />
        </Card.Body>
      </Card>

      {/* OCR Settings */}
      <Card className="config-card">
        <Card.Header className="config-header">
          <h6>📝 OCR</h6>
        </Card.Header>
        <Card.Body>
          <Form.Group className="mb-3">
            <Form.Label className="config-label">Primary OCR</Form.Label>
            <Form.Select
              value={config.primary_ocr || 'easyocr'}
              onChange={(e) => handleChange('primary_ocr', e.target.value)}
            >
              <option value="easyocr">EasyOCR (Deep Learning)</option>
              <option value="tesseract">Tesseract (Traditional)</option>
            </Form.Select>
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label className="config-label">
              OCR Confidence Threshold
              <Badge bg="info" className="ms-2">
                {(config.ocr_threshold || 0.6).toFixed(2)}
              </Badge>
            </Form.Label>
            <Form.Range
              min="0"
              max="1"
              step="0.05"
              value={config.ocr_threshold || 0.6}
              onChange={(e) => handleChange('ocr_threshold', parseFloat(e.target.value))}
            />
          </Form.Group>
        </Card.Body>
      </Card>

      {/* Model Path */}
      <Card className="config-card">
        <Card.Header className="config-header">
          <h6>🤖 Model</h6>
        </Card.Header>
        <Card.Body>
          <Form.Group>
            <Form.Label className="config-label">Model Path</Form.Label>
            <Form.Control
              type="text"
              placeholder="models/yolov9c.pt"
              value={config.model_path || 'models/yolov9c.pt'}
              onChange={(e) => handleChange('model_path', e.target.value)}
              size="sm"
            />
            <small className="text-muted d-block mt-1">
              Current: YOLOv9c (License Plate Detection)
            </small>
          </Form.Group>
        </Card.Body>
      </Card>
    </div>
  );
};

export default ConfigurationSidebar;
