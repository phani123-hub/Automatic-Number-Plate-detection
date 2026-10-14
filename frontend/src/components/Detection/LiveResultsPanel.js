import { Accordion, Card, Button, Image } from 'react-bootstrap';
import Badge from 'react-bootstrap/Badge';
import React from 'react';
import './LiveResultsPanel.css';

const LiveResultsPanel = ({ results, onMarkValid, onDelete }) => (
  <Card className="mb-3 shadow-sm">
    <Card.Header className="bg-secondary text-white"><h5>🎯 Live Detections ({results.length})</h5></Card.Header>
    <Card.Body>
      {results.length === 0 ? (
        <div className="text-center text-muted py-3">Waiting for detections...</div>
      ) : (
        <Accordion>
          {results.map((res, idx) => (
            <Accordion.Item eventKey={idx} key={res.track_id}>
              <Accordion.Header>
                <span>Track {res.track_id} {res.text} ({(res.confidence*100).toFixed(1)}%)</span>
                {res.is_valid && <Badge bg="success" className="ms-2">✓ Valid</Badge>}
              </Accordion.Header>
              <Accordion.Body>
                {res.crop && (
                  <Image src={`data:image/jpeg;base64,${res.crop}`} fluid rounded className="mb-2"/>
                )}
                <div className="d-grid gap-2">
                  <Button variant="success" size="sm" onClick={() => onMarkValid(res.track_id)}>✓ Mark Valid</Button>
                  <Button variant="danger" size="sm" onClick={() => onDelete(res.track_id)}>🗑️ Delete</Button>
                </div>
                <p><strong>Plate:</strong> {res.text}</p>
                <p><strong>Confidence:</strong> {(res.confidence*100).toFixed(1)}%</p>
                <p><strong>Valid:</strong> {res.is_valid ? '✓' : '✗'}</p>
              </Accordion.Body>
            </Accordion.Item>
          ))}
        </Accordion>
      )}
    </Card.Body>
  </Card>
);

export default LiveResultsPanel;