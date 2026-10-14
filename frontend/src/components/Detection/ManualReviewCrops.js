import { useState, useEffect } from 'react';
import { Table, Alert, Card, Image, Badge, Spinner, Button, Form } from 'react-bootstrap';
import { detectionAPI } from '../../api/detection';
import './Detection.css';

const ManualReviewCrops = ({ sessionId }) => {
  const [crops, setCrops] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [selectedCrops, setSelectedCrops] = useState([]);
  const [plateTexts, setPlateTexts] = useState({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (sessionId) {
      fetchManualReviewCrops();
    }
  }, [sessionId]);

  const fetchManualReviewCrops = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await detectionAPI.getManualReviewCrops(sessionId);
      const fetchedCrops = response.data.crops || [];
      setCrops(fetchedCrops);
      // Auto-select all crops by default
      setSelectedCrops(fetchedCrops.map((_, idx) => idx));
      // Initialize empty plate texts
      const initialTexts = {};
      fetchedCrops.forEach((_, idx) => {
        initialTexts[idx] = '';
      });
      setPlateTexts(initialTexts);
    } catch (err) {
      // Don't show error if no manual review crops exist
      if (err.response?.status !== 404) {
        setError(err.response?.data?.error || 'Failed to fetch manual review crops');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSelectCrop = (index) => {
    setSelectedCrops(prev => {
      if (prev.includes(index)) {
        return prev.filter(i => i !== index);
      } else {
        return [...prev, index];
      }
    });
  };

  const handlePlateTextChange = (index, value) => {
    setPlateTexts(prev => ({
      ...prev,
      [index]: value.toUpperCase()
    }));
  };

  const handleConfirmSave = async () => {
    if (selectedCrops.length === 0) {
      setError('Please select at least one crop to save');
      return;
    }

    // Validate that all selected crops have plate text
    const missingText = selectedCrops.some(idx => !plateTexts[idx] || plateTexts[idx].trim() === '');
    if (missingText) {
      setError('Please enter plate number for all selected crops');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const cropsToSave = selectedCrops.map(idx => ({
        track_id: crops[idx].track_id,
        plate_text: plateTexts[idx].trim(),
        confidence: crops[idx].yolo_confidence,
        frame_num: crops[idx].frame_num,
        crop_path: crops[idx].crop_path
      }));

      const response = await detectionAPI.confirmManualReview(sessionId, cropsToSave);
      setSuccess(`✓ Successfully saved ${response.data.saved_count} plate(s) to database!`);
      setSaved(true);
      
      // Don't auto-clear - let user see success message
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to save manual review crops');
    } finally {
      setLoading(false);
    }
  };

  if (loading && crops.length === 0) {
    return (
      <div className="text-center p-4">
        <Spinner animation="border" variant="warning" />
        <p className="mt-2">Loading manual review crops...</p>
      </div>
    );
  }

  if (!crops || crops.length === 0) {
    return null;
  }

  return (
    <Card className="mt-3" style={{ maxWidth: '95%', width: '100%', margin: '0 auto' }}>
      <Card.Header className="bg-danger text-white">
        <h5 className="mb-0">
          ⚠️ Manual Review Required - Low OCR Confidence ({"<"} 10%)
        </h5>
      </Card.Header>
      <Card.Body>
        {error && <Alert variant="danger">{error}</Alert>}
        {success && <Alert variant="success">{success}</Alert>}

        <Alert variant="warning">
          <strong>{crops.length} plate(s) with low OCR confidence</strong> - These plates need manual verification.
          The system detected these plates with high YOLO confidence but couldn't reliably read the text (OCR {"<"} 10%).
          Please review the crops below, enter the correct plate numbers, and save to database.
        </Alert>

        <Table striped bordered hover responsive className="mb-3">
          <thead>
            <tr>
              <th style={{ width: '50px' }}>
                <input
                  type="checkbox"
                  checked={selectedCrops.length === crops.length}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedCrops(crops.map((_, idx) => idx));
                    } else {
                      setSelectedCrops([]);
                    }
                  }}
                />
              </th>
              <th>Best Quality Crop</th>
              <th>Enter Plate Number</th>
              <th>YOLO Confidence</th>
              <th>OCR Confidence</th>
              <th>Track ID</th>
              <th>Frame</th>
            </tr>
          </thead>
          <tbody>
            {crops.map((crop, idx) => (
              <tr key={idx}>
                <td className="text-center">
                  <input
                    type="checkbox"
                    checked={selectedCrops.includes(idx)}
                    onChange={() => handleSelectCrop(idx)}
                  />
                </td>
                <td className="text-center">
                  {crop.crop_base64 ? (
                    <Image
                      src={`data:image/jpeg;base64,${crop.crop_base64}`}
                      alt="Manual Review Crop"
                      style={{ 
                        maxWidth: '250px', 
                        maxHeight: '100px',
                        border: '3px solid #dc3545',
                        borderRadius: '4px',
                        boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                      }}
                    />
                  ) : (
                    <Badge bg="secondary">No Image</Badge>
                  )}
                </td>
                <td>
                  <Form.Control
                    type="text"
                    placeholder="Enter plate number"
                    value={plateTexts[idx] || ''}
                    onChange={(e) => handlePlateTextChange(idx, e.target.value)}
                    style={{ 
                      minWidth: '180px',
                      textTransform: 'uppercase',
                      fontWeight: 'bold',
                      fontSize: '1rem'
                    }}
                    disabled={!selectedCrops.includes(idx)}
                  />
                  <small className="text-muted">e.g., MH 02 FU 9779</small>
                </td>
                <td>
                  <Badge 
                    bg={crop.yolo_confidence >= 0.7 ? 'success' : crop.yolo_confidence >= 0.5 ? 'warning' : 'danger'}
                    style={{ fontSize: '0.9rem' }}
                  >
                    {(crop.yolo_confidence * 100).toFixed(1)}%
                  </Badge>
                  <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                    Detection Quality
                  </div>
                </td>
                <td>
                  <Badge 
                    bg="danger"
                    style={{ fontSize: '0.9rem' }}
                  >
                    {(crop.ocr_confidence * 100).toFixed(1)}%
                  </Badge>
                  <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                    Text Recognition
                  </div>
                </td>
                <td>
                  <Badge bg="info">Track {crop.track_id}</Badge>
                </td>
                <td>
                  <Badge bg="secondary">Frame {crop.frame_num}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>

        <div className="d-flex justify-content-between align-items-center mb-3">
          <div>
            <Badge bg="primary" className="me-2">
              {selectedCrops.length} of {crops.length} selected
            </Badge>
          </div>
          <div>
            <Button
              variant={saved ? "secondary" : "success"}
              size="lg"
              onClick={handleConfirmSave}
              disabled={loading || selectedCrops.length === 0 || saved}
            >
              {loading ? (
                <>
                  <Spinner animation="border" size="sm" className="me-2" />
                  Saving...
                </>
              ) : saved ? (
                <>✓ Saved to Database</>
              ) : (
                <>✓ Add Selected to Database</>
              )}
            </Button>
          </div>
        </div>

        <Alert variant="info" className="mb-0">
          <strong>📝 How to use:</strong>
          <ul className="mb-0 mt-2">
            <li><strong>Review:</strong> Examine each crop image and identify the plate number</li>
            <li><strong>Enter:</strong> Type the correct plate number in the input field</li>
            <li><strong>Select:</strong> Check the crops you want to save (all selected by default)</li>
            <li><strong>Save:</strong> Click "Add Selected to Database" to save your entries</li>
            <li><strong>Note:</strong> High YOLO confidence = good detection quality | Low OCR confidence = text couldn't be auto-read</li>
          </ul>
          
          <div className="mt-3 p-2 bg-light rounded border">
            <strong>📁 Access All Crops:</strong>
            <div className="mt-2">
              <small className="text-muted">All low-confidence crops (OCR {"<"} 10%) are saved to:</small>
              <div className="mt-1">
                <code style={{ 
                  display: 'block', 
                  padding: '8px', 
                  backgroundColor: '#2d2d2d', 
                  color: '#f8f8f2',
                  borderRadius: '4px',
                  fontSize: '0.9rem'
                }}>
                  backend/data/crops/manual_review/{sessionId}/
                </code>
              </div>
              <small className="text-muted mt-2 d-block">
                • Each track has its own folder with top 3 quality crops<br/>
                • Use file explorer to view all images if needed<br/>
                • Filenames show YOLO confidence, OCR confidence, and frame number
              </small>
            </div>
          </div>
        </Alert>
      </Card.Body>
    </Card>
  );
};

export default ManualReviewCrops;
