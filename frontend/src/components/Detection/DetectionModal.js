import { Modal, Container, Row, Col, Badge, Image, Alert } from 'react-bootstrap';
import { useState } from 'react';
import './Detection.css';

const DetectionModal = ({ show, detection, onHide }) => {
  const [imageError, setImageError] = useState(false);

  if (!detection) return null;

  // Safe getters for all fields
  const getPlateText = () => detection?.plate_text || detection?.text || 'Unknown';
  
  const getConfidence = () => {
    let conf = detection?.confidence_score || detection?.confidence || 0;
    if (typeof conf === 'string') conf = parseFloat(conf);
    return isNaN(conf) ? 0 : Math.min(conf * (conf > 1 ? 1 : 100), 100);
  };

  const isValid = () => detection?.is_valid_indian || detection?.is_valid || false;
  
  const getCrop = () => {
    if (!detection?.crop) return null;
    if (detection.crop.startsWith('data:image')) return detection.crop;
    return `data:image/jpeg;base64,${detection.crop}`;
  };

  const getBox = () => detection?.bbox || detection?.box || null;
  const getTrackId = () => detection?.track_id || 'Unknown';

  const renderCropImage = () => {
    const crop = getCrop();
    
    if (!crop || imageError) {
      return (
        <div
          className="bg-light rounded p-5 text-center"
          style={{ height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}
        >
          <p className="text-muted mb-2">📸 No Image Available</p>
          <small className="text-muted">
            {!detection?.crop 
              ? 'Crop data not stored in database' 
              : 'Image could not be loaded'}
          </small>
        </div>
      );
    }

    return (
      <Image
        src={crop}
        alt="plate"
        className="img-fluid rounded"
        style={{ maxHeight: '250px', objectFit: 'contain' }}
        onError={() => setImageError(true)}
      />
    );
  };

  const renderBoundingBox = () => {
    const box = getBox();
    if (!box || !Array.isArray(box) || box.length < 4) {
      return (
        <Alert variant="warning" className="mb-0">
          📐 Bounding box coordinates not available in database
        </Alert>
      );
    }

    return (
      <div className="bg-light p-3 rounded">
        <div className="row text-center">
          <div className="col">
            <small className="text-muted d-block">X1</small>
            <strong>{Math.round(box[0])}</strong>
          </div>
          <div className="col">
            <small className="text-muted d-block">Y1</small>
            <strong>{Math.round(box[1])}</strong>
          </div>
          <div className="col">
            <small className="text-muted d-block">X2</small>
            <strong>{Math.round(box[2])}</strong>
          </div>
          <div className="col">
            <small className="text-muted d-block">Y2</small>
            <strong>{Math.round(box[3])}</strong>
          </div>
        </div>
        <hr />
        <div className="row text-center">
          <div className="col">
            <small className="text-muted d-block">Width</small>
            <strong>{Math.round(box[2] - box[0])}</strong>
          </div>
          <div className="col">
            <small className="text-muted d-block">Height</small>
            <strong>{Math.round(box[3] - box[1])}</strong>
          </div>
        </div>
      </div>
    );
  };

  return (
    <Modal show={show} onHide={onHide} size="lg" centered>
      <Modal.Header closeButton className="bg-dark text-white">
        <Modal.Title>🔍 Detection Details - Track {getTrackId()}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Container fluid>
          <Row className="mb-4">
            <Col md={6}>
              <h6 className="mb-3 fw-bold">Cropped License Plate</h6>
              {renderCropImage()}
            </Col>

            <Col md={6}>
              <div className="bg-light p-3 rounded">
                <div className="mb-3">
                  <label className="fw-bold text-muted d-block mb-2">Plate Text</label>
                  <Badge bg="primary" className="px-3 py-2 fs-6">
                    {getPlateText()}
                  </Badge>
                </div>

                <div className="mb-3">
                  <label className="fw-bold text-muted d-block mb-2">Confidence Score</label>
                  <div className="progress" style={{ height: '32px' }}>
                    <div
                      className="progress-bar bg-success"
                      style={{
                        width: `${getConfidence()}%`,
                        fontSize: '14px',
                        lineHeight: '32px',
                        fontWeight: 'bold',
                      }}
                    >
                      {getConfidence().toFixed(2)}%
                    </div>
                  </div>
                </div>

                <div className="mb-3">
                  <label className="fw-bold text-muted d-block mb-2">Validity Status</label>
                  {isValid() ? (
                    <Badge bg="success" className="px-3 py-2 fs-6">
                      ✓ Valid Indian Plate
                    </Badge>
                  ) : (
                    <Badge bg="warning" className="px-3 py-2 fs-6">
                      ⚠ Invalid Format
                    </Badge>
                  )}
                </div>

                <div>
                  <label className="fw-bold text-muted d-block mb-2">Track ID</label>
                  <code className="bg-white p-2 rounded d-block">{getTrackId()}</code>
                </div>
              </div>
            </Col>
          </Row>

          <Row>
            <Col md={12}>
              <h6 className="mb-3 fw-bold">📐 Bounding Box Coordinates</h6>
              {renderBoundingBox()}
            </Col>
          </Row>
        </Container>
      </Modal.Body>
    </Modal>
  );
};

export default DetectionModal;