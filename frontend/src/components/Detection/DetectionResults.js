import { useState } from 'react';
import { Card, Table, Badge, Button, Image } from 'react-bootstrap';
import './Detection.css';

const DetectionResults = ({ results, onViewDetails }) => {
  const [sortBy, setSortBy] = useState('newest');

  if (!results || results.length === 0) {
    return (
      <Card className="detection-card shadow-sm">
        <Card.Header className="bg-info text-white">
          <h5 className="mb-0">📊 Detection Results</h5>
        </Card.Header>
        <Card.Body className="text-center text-muted">
          <p>No detections yet. Upload a video or use webcam to get started.</p>
        </Card.Body>
      </Card>
    );
  }

  const sortedResults = [...results].sort((a, b) => {
    if (sortBy === 'confidence') {
      return b.confidence - a.confidence;
    }
    return 0;
  });

  return (
    <Card className="detection-card shadow-sm">
      <Card.Header className="bg-info text-white d-flex justify-content-between align-items-center">
        <h5 className="mb-0">📊 Detection Results ({results.length})</h5>
        <select
          className="form-select form-select-sm"
          style={{ width: '150px' }}
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
        >
          <option value="newest">Newest First</option>
          <option value="confidence">Highest Confidence</option>
        </select>
      </Card.Header>
      <Card.Body>
        <div className="table-responsive">
          <Table hover className="mb-0">
            <thead>
              <tr>
                <th style={{ width: '15%' }}>Timestamp</th>
                <th style={{ width: '20%' }}>Plate Text</th>
                <th style={{ width: '15%' }}>Confidence</th>
                <th style={{ width: '10%' }}>Valid</th>
                <th style={{ width: '20%' }}>Crop Preview</th>
                <th style={{ width: '20%' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {sortedResults.map((result, idx) => (
                <tr key={`${result.track_id}-${idx}`}>
                  <td>
                    <small style={{ color: '#000' }}>
                      {result.timestamp
                        ? new Date(result.timestamp).toLocaleString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                          })
                        : 'N/A'}
                    </small>
                  </td>
                  <td>
                    <Badge bg="primary" className="px-3 py-2">
                      {result.text || 'N/A'}
                    </Badge>
                  </td>
                  <td>
                    <div className="progress" style={{ height: '24px' }}>
                      <div
                        className="progress-bar bg-success"
                        role="progressbar"
                        style={{
                          width: `${(result.confidence * 100).toFixed(0)}%`,
                        }}
                      >
                        {(result.confidence * 100).toFixed(1)}%
                      </div>
                    </div>
                  </td>
                  <td>
                    {result.is_valid ? (
                      <Badge bg="success">✓ Yes</Badge>
                    ) : (
                      <Badge bg="warning">✗ No</Badge>
                    )}
                  </td>
                  <td>
                    {result.crop && (
                      <Image
                        src={`data:image/jpeg;base64,${result.crop}`}
                        alt="plate"
                        className="crop-thumbnail"
                        style={{
                          height: '40px',
                          borderRadius: '4px',
                          cursor: 'pointer',
                        }}
                        onClick={() => onViewDetails?.(result)}
                      />
                    )}
                  </td>
                  <td>
                    <Button
                      variant="outline-primary"
                      size="sm"
                      onClick={() => onViewDetails?.(result)}
                    >
                      View
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      </Card.Body>
    </Card>
  );
};

export default DetectionResults;
