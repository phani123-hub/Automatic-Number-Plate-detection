import { Accordion, Card } from 'react-bootstrap';
import './HelpSection.css';

const HelpSection = () => (
  <Card className="mb-3 shadow-sm">
    <Card.Header className="bg-info text-white"><h5>❓ Help & Docs</h5></Card.Header>
    <Card.Body>
      <Accordion flush>
        <Accordion.Item eventKey="howtouse">
          <Accordion.Header>📖 How to Use</Accordion.Header>
          <Accordion.Body>
            <ol>
              <li>Configure detection in the sidebar</li>
              <li>Select input (Webcam/Video/RTSP)</li>
              <li>Click "Start"</li>
              <li>Monitor live video & detection boxes</li>
              <li>Check detection logs and stats</li>
              <li>Export logs as CSV</li>
            </ol>
          </Accordion.Body>
        </Accordion.Item>
        <Accordion.Item eventKey="tips">
          <Accordion.Header>⚙️ Tips & Tricks</Accordion.Header>
          <Accordion.Body>
            <ul>
              <li>Lower confidence for more detection sensitivity</li>
              <li>Enable preprocessing for night videos</li>
              <li>Use GPU for faster detection</li>
              <li>Adjust thresholds to balance recall & precision</li>
            </ul>
          </Accordion.Body>
        </Accordion.Item>
        <Accordion.Item eventKey="faq">
          <Accordion.Header>❓ FAQ</Accordion.Header>
          <Accordion.Body>
            <p><strong>Q:</strong> How to improve detection?</p>
            <p><strong>A:</strong> Use auto exposure, auto threshold, GPU, and preprocessing.</p>
            <p><strong>Q:</strong> Why no detection?</p>
            <p><strong>A:</strong> Check input source, confidence threshold, and camera quality.</p>
          </Accordion.Body>
        </Accordion.Item>
      </Accordion>
    </Card.Body>
  </Card>
);

export default HelpSection;
