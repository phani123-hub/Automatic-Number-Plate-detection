import { useState, useEffect } from 'react';
import { Table, Button, Alert, Card, Image, Badge, Spinner } from 'react-bootstrap';
import { detectionAPI } from '../../api/detection';
import './Detection.css';

const PreviewDetections = ({ sessionId, onConfirm }) => {
  const [previews, setPreviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [selectedTracks, setSelectedTracks] = useState([]);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (sessionId) {
      fetchPreviews();
    }
  }, [sessionId]);

  const fetchPreviews = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await detectionAPI.getPreviewDetections(sessionId);
      setPreviews(response.data.previews || []);
      // Auto-select all by default
      setSelectedTracks(response.data.previews?.map(p => p.track_id) || []);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch preview detections');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectTrack = (trackId) => {
    setSelectedTracks(prev => {
      if (prev.includes(trackId)) {
        return prev.filter(id => id !== trackId);
      } else {
        return [...prev, trackId];
      }
    });
  };

  const handleConfirmSave = async () => {
    if (selectedTracks.length === 0) {
      setError('Please select at least one detection to save');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await detectionAPI.confirmDetections(sessionId, selectedTracks);
      setSuccess(`✓ Successfully saved ${response.data.saved_count} detections to database!`);
      setSaved(true);
      
      // Don't auto-clear - let user see both tables and save manual review too
      if (onConfirm) {
        onConfirm('preview');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to save detections');
    } finally {
      setLoading(false);
    }
  };

  if (loading && previews.length === 0) {
    return (
      <div className="text-center p-4">
        <Spinner animation="border" variant="primary" />
        <p className="mt-2">Loading preview detections...</p>
      </div>
    );
  }

  if (!previews || previews.length === 0) {
    return null;
  }

  return (
    <Card className="mt-3" style={{ maxWidth: '95%', width: '100%', margin: '0 auto' }}>
      <Card.Header className="bg-warning text-dark">
        <h5 className="mb-0">
          🔍 Detection Preview - Validate Before Saving
        </h5>
      </Card.Header>
      <Card.Body>
        {error && <Alert variant="danger">{error}</Alert>}
        {success && <Alert variant="success">{success}</Alert>}

        <Alert variant="info">
          <strong>Top {previews.length} detected plates</strong> - Please review and confirm before saving to database.
          Select the detections you want to save and click "Confirm & Save".
        </Alert>

        <Table striped bordered hover responsive className="mb-3">
          <thead>
            <tr>
              <th style={{ width: '50px' }}>
                <input
                  type="checkbox"
                  checked={selectedTracks.length === previews.length}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedTracks(previews.map(p => p.track_id));
                    } else {
                      setSelectedTracks([]);
                    }
                  }}
                />
              </th>
              <th>Crop Image</th>
              <th>Plate Number</th>
              <th>Confidence</th>
              <th>Track ID</th>
              <th>Frame</th>
            </tr>
          </thead>
          <tbody>
            {previews.map((preview, idx) => (
              <tr key={idx}>
                <td className="text-center">
                  <input
                    type="checkbox"
                    checked={selectedTracks.includes(preview.track_id)}
                    onChange={() => handleSelectTrack(preview.track_id)}
                  />
                </td>
                <td className="text-center">
                  {preview.crop_base64 ? (
                    <Image
                      src={`data:image/jpeg;base64,${preview.crop_base64}`}
                      alt="Plate Crop"
                      style={{ 
                        maxWidth: '200px', 
                        maxHeight: '80px',
                        border: '2px solid #ddd',
                        borderRadius: '4px'
                      }}
                    />
                  ) : (
                    <Badge bg="secondary">No Image</Badge>
                  )}
                </td>
                <td>
                  <strong>
                    {preview.plate_text === "Can't extract OCR" ? (
                      <Badge bg="danger">{preview.plate_text}</Badge>
                    ) : (
                      <Badge bg="success" style={{ fontSize: '1rem' }}>
                        {preview.plate_text}
                      </Badge>
                    )}
                  </strong>
                </td>
                <td>
                  <Badge 
                    bg={preview.confidence >= 0.7 ? 'success' : preview.confidence >= 0.5 ? 'warning' : 'danger'}
                  >
                    {(preview.confidence * 100).toFixed(1)}%
                  </Badge>
                </td>
                <td>
                  <Badge bg="info">Track {preview.track_id}</Badge>
                </td>
                <td>
                  <Badge bg="secondary">Frame {preview.frame_num}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>

        <div className="d-flex justify-content-between align-items-center">
          <div>
            <Badge bg="primary" className="me-2">
              {selectedTracks.length} of {previews.length} selected
            </Badge>
          </div>
          <div>
            <Button
              variant={saved ? "secondary" : "success"}
              size="lg"
              onClick={handleConfirmSave}
              disabled={loading || selectedTracks.length === 0 || saved}
            >
              {loading ? (
                <>
                  <Spinner animation="border" size="sm" className="me-2" />
                  Saving...
                </>
              ) : saved ? (
                <>✓ Saved to Database</>
              ) : (
                <>✓ Confirm & Save to Database</>
              )}
            </Button>
          </div>
        </div>
      </Card.Body>
    </Card>
  );
};

export default PreviewDetections;
