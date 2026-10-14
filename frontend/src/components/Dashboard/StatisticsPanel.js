import { Card, Row, Col } from 'react-bootstrap';
import './StatisticsPanel.css';

const StatisticsPanel = ({ stats }) => (
  <Card className="mb-3 shadow-sm">
    <Card.Header className="bg-primary text-white"><h5>📊 Detection Stats</h5></Card.Header>
    <Card.Body>
      <Row>
        {[
          { label: 'Frames', value: stats.frameCount || 0, icon: '📹' },
          { label: 'Detections', value: stats.detectionCount || 0, icon: '🎯' },
          { label: 'FPS', value: (stats.fps || 0).toFixed(1), icon: '⚡' },
          { label: 'Vehicles', value: stats.uniqueVehicles || 0, icon: '🚗' },
          { label: 'Avg Conf', value: `${(stats.avgConfidence*100).toFixed(1)}%`, icon: '📈' },
          { label: 'Proc Time', value: `${stats.processingTime || 0} ms`, icon: '⏱️' }
        ].map((item, i) => (
          <Col key={i} sm={4} className="mb-2">
            <div className="stat-card">
              <div className="stat-icon">{item.icon}</div>
              <div className="stat-value">{item.value}</div>
              <div className="stat-label">{item.label}</div>
            </div>
          </Col>
        ))}
      </Row>
    </Card.Body>
  </Card>
);

export default StatisticsPanel;