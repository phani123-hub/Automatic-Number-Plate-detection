import { useContext, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Table, Badge, Row, Col, Alert } from 'react-bootstrap';
import { AuthContext } from '../../context/AuthContext';
import { ConfigContext } from '../../context/ConfigContext';
import { detectionAPI } from '../../api/detection';
import { DEMO_DETECTIONS } from '../../data/demoDetections';
import ConfigurationSidebar from '../Detection/ConfigurationSidebar';
import SessionControls from '../Detection/SessionControls';
import LiveResultsPanel from '../Detection/LiveResultsPanel';
import VideoUpload from '../Detection/VideoUpload';
import WebcamLive from '../Detection/WebcamLive';
import RTSPStream from '../Detection/RTSPStream';
import '../Dashboard/Dashboard.css';

const NAV_ITEMS = [
  { key: 'overview', label: 'Dashboard', icon: '◫' },
  { key: 'live', label: 'Live Detection', icon: '◉' },
  { key: 'upload', label: 'Upload Video', icon: '▣' },
  { key: 'history', label: 'Detection History', icon: '▤' },
  { key: 'analytics', label: 'Analytics', icon: '◭' },
  { key: 'settings', label: 'Configuration', icon: '⚙' },
];

const normalizeHistoryItems = (payload) => {
  if (Array.isArray(payload)) return payload;
  if (payload && Array.isArray(payload.detections)) return payload.detections;
  if (payload && Array.isArray(payload.results)) return payload.results;
  if (payload && Array.isArray(payload.data)) return payload.data;
  return [];
};

const getDisplayValue = (item, keys, fallback = '—') => {
  for (const key of keys) {
    const value = item?.[key];
    if (value !== undefined && value !== null && value !== '') return value;
  }
  return fallback;
};

const formatConfidence = (value) => {
  if (value === undefined || value === null || value === '') return '—';
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return '—';
  return `${(numeric * 100).toFixed(1)}%`;
};

const formatPlate = (raw) => {
  const value = String(raw || '').trim();
  if (!value) return '—';
  return value.toUpperCase();
};

const Dashboard = ({ initialView = 'overview' }) => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  const { config, updateConfig } = useContext(ConfigContext);

  const [activeView, setActiveView] = useState(initialView);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const [liveResults, setLiveResults] = useState([]);
  const [showPreview, setShowPreview] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState('');

  useEffect(() => {
    setActiveView(initialView);
  }, [initialView]);

  useEffect(() => {
    const loadHistory = async () => {
      setHistoryLoading(true);
      setHistoryError('');

      if (user?.isDemo) {
        setHistory(DEMO_DETECTIONS);
        setHistoryLoading(false);
        return;
      }

      try {
        const response = await detectionAPI.getHistory(12, 0);
        const items = normalizeHistoryItems(response?.data || []);
        setHistory(items);
      } catch (error) {
        setHistory([]);
        setHistoryError('Unable to load detection history.');
      } finally {
        setHistoryLoading(false);
      }
    };

    loadHistory();
  }, [user]);

  const analytics = useMemo(() => {
    const values = history
      .map((item) => Number(getDisplayValue(item, ['confidence', 'conf', 'score'], 0)))
      .filter((number) => !Number.isNaN(number));

    const plateSet = new Set(
      history
        .map((item) => formatPlate(getDisplayValue(item, ['plate_number', 'plate', 'text'])))
        .filter((plate) => plate !== '—')
    );

    const totalDetections = history.length;
    const uniquePlates = plateSet.size;
    const averageConfidence = values.length ? values.reduce((sum, val) => sum + val, 0) / values.length : 0;
    const highestConfidence = values.length ? Math.max(...values) : 0;

    return {
      totalDetections,
      uniquePlates,
      averageConfidence,
      highestConfidence,
    };
  }, [history]);

  const statCards = [
    { label: 'Total Detections', value: analytics.totalDetections || '—', suffix: '', delta: '+12.4%', icon: '◎', tone: 'cyan' },
    { label: 'Unique Plates', value: analytics.uniquePlates || '—', suffix: '', delta: '+8.2%', icon: '◈', tone: 'green' },
    { label: 'Vehicles Today', value: Math.min(analytics.totalDetections || 0, 428) || '—', suffix: '', delta: '+6.9%', icon: '▣', tone: 'amber' },
    { label: 'Detection Accuracy', value: formatConfidence(analytics.averageConfidence || 0.948), suffix: '', delta: '+2.1%', icon: '▦', tone: 'violet' },
  ];

  const notifications = useMemo(() => {
    if (history.length === 0) {
      return [
        { title: 'System ready', detail: 'Awaiting detection events.', time: 'Now' },
      ];
    }

    return [
      { title: 'Detection completed', detail: `${history[0]?.plate || 'Latest plate'} detected`, time: 'Now' },
      { title: 'Processing updated', detail: `${history.length} detections synced`, time: '5m ago' },
      { title: 'Model status', detail: 'OCR pipeline ready', time: '15m ago' },
    ];
  }, [history]);

  const recentDetections = history.slice(0, 4);

  const chartBars = useMemo(() => {
    const values = history.length ? [5, 7, 9, 8, 12, 11, 6] : [2, 3, 4, 5, 3, 4, 2];
    return values.map((value, index) => ({
      label: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][index],
      value,
    }));
  }, [history]);

  const topPlates = useMemo(() => {
    const counts = {};

    history.forEach((item) => {
      const plate = formatPlate(getDisplayValue(item, ['plate_number', 'plate', 'text']));
      if (plate === '—') return;
      counts[plate] = (counts[plate] || 0) + 1;
    });

    return Object.entries(counts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
      .map(([name, count]) => ({ name, count }));
  }, [history]);

  const handleDetectionComplete = (results) => {
    if (results && results.length > 0) {
      setLiveResults((prev) => [...results, ...prev].slice(0, 50));
    }
    setShowPreview(true);
  };

  const handleNavSelect = (view) => {
    setActiveView(view);
    navigate(`/dashboard/${view}`);
  };

  const renderOverview = () => (
    <>
      <div className="page-header">
        <div>
          <p className="eyebrow">Good evening</p>
          <h1>Night Plate Detection Dashboard</h1>
          <p className="page-subtitle">Monitor and analyze vehicle plate detections in real time.</p>
        </div>
        <div className="header-actions">
          <Button variant="outline-light" className="ghost-btn">Export report</Button>
          <Button className="primary-btn">Start monitoring</Button>
        </div>
      </div>

      <Row className="stat-grid g-3">
        {statCards.map((card) => (
          <Col key={card.label} xs={12} sm={6} lg={3}>
            <Card className={`glass-card stat-card ${card.tone}`}>
              <Card.Body>
                <div className="stat-header">
                  <span className="stat-icon">{card.icon}</span>
                  <span className="stat-trend">{card.delta}</span>
                </div>
                <div className="stat-value">{card.value}</div>
                <div className="stat-label">{card.label}</div>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>

      <Row className="g-4 dashboard-grid">
        <Col lg={8}>
          <Card className="glass-card panel-card">
            <Card.Header>
              <div className="panel-header">
                <h3>Detection activity</h3>
                <Badge bg="light" text="dark">7-day view</Badge>
              </div>
            </Card.Header>
            <Card.Body>
              <div className="line-chart">
                {chartBars.map((bar) => (
                  <div key={bar.label} className="chart-col">
                    <span className="chart-bar" style={{ height: `${Math.max(18, bar.value * 12)}px` }} />
                    <small>{bar.label}</small>
                  </div>
                ))}
              </div>
            </Card.Body>
          </Card>
        </Col>

        <Col lg={4}>
          <Card className="glass-card panel-card">
            <Card.Header>
              <div className="panel-header">
                <h3>Recent detections</h3>
                <Badge bg="primary">Live</Badge>
              </div>
            </Card.Header>
            <Card.Body className="recent-list">
              {recentDetections.length === 0 ? (
                <div className="empty-inline">No recent detections</div>
              ) : (
                recentDetections.map((item) => (
                  <div key={`${item?.plate || 'plate'}-${item?._id || Math.random()}`} className="recent-item">
                    <div className="plate-badge">{formatPlate(getDisplayValue(item, ['plate_number', 'plate', 'text']))}</div>
                    <div className="recent-meta">
                      <strong>{formatConfidence(getDisplayValue(item, ['confidence', 'conf', 'score']))}</strong>
                      <span>{getDisplayValue(item, ['detected_at', 'timestamp', 'created_at'], '—')}</span>
                    </div>
                  </div>
                ))
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </>
  );

  const renderLive = () => (
    <>
      <div className="page-header compact-header">
        <div>
          <p className="eyebrow">System active</p>
          <h1>Live Detection</h1>
        </div>
        <Badge bg="success" className="status-pill">● Active</Badge>
      </div>

      <Row className="g-4">
        <Col lg={8}>
          <WebcamLive sessionId={sessionId} onDetectionComplete={handleDetectionComplete} />
        </Col>
        <Col lg={4}>
          <LiveResultsPanel results={liveResults} />
        </Col>
      </Row>

      <div className="mt-4">
        <ConfigurationSidebar config={config} onConfigChange={updateConfig} />
      </div>
    </>
  );

  const renderUpload = () => (
    <>
      <div className="page-header compact-header">
        <div>
          <p className="eyebrow">Video intake</p>
          <h1>Upload Video</h1>
        </div>
      </div>

      <div className="upload-layout">
        <VideoUpload sessionId={sessionId} onDetectionComplete={handleDetectionComplete} />
      </div>

      {showPreview && (
        <div className="mt-4 preview-strip">
          <Button variant="outline-light" className="ghost-btn" onClick={() => setShowPreview(false)}>
            Hide preview
          </Button>
        </div>
      )}
    </>
  );

  const renderHistory = () => (
    <>
      <div className="page-header compact-header">
        <div>
          <p className="eyebrow">Audit trail</p>
          <h1>Detection History</h1>
        </div>
        <Button className="primary-btn">Export CSV</Button>
      </div>

      {historyError && <Alert variant="danger">{historyError}</Alert>}

      <Card className="glass-card table-card">
        <Card.Body>
          {historyLoading ? (
            <div className="loading-box">Loading detection history…</div>
          ) : history.length === 0 ? (
            <div className="empty-state">
              <h4>No detections found</h4>
              <p>There are no license plate detections matching your current filters.</p>
            </div>
          ) : (
            <Table responsive hover className="modern-table">
              <thead>
                <tr>
                  <th>Plate Number</th>
                  <th>Confidence</th>
                  <th>Date</th>
                  <th>Time</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item, index) => {
                  const plate = formatPlate(getDisplayValue(item, ['plate_number', 'plate', 'text']));
                  const confidence = formatConfidence(getDisplayValue(item, ['confidence', 'conf', 'score']));
                  const status = item?.is_valid ? 'Verified' : 'Pending';

                  return (
                    <tr key={`${plate}-${index}`}>
                      <td><span className="plate-badge compact">{plate}</span></td>
                      <td>{confidence}</td>
                      <td>{getDisplayValue(item, ['date', 'detected_date'], '—')}</td>
                      <td>{getDisplayValue(item, ['time', 'detected_time'], '—')}</td>
                      <td>{getDisplayValue(item, ['source', 'camera', 'device'], 'CCTV')}</td>
                      <td><Badge bg={item?.is_valid ? 'success' : 'warning'}>{status}</Badge></td>
                      <td><Button variant="link" className="table-action-link">View</Button></td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>
    </>
  );

  const renderAnalytics = () => (
    <>
      <div className="page-header compact-header">
        <div>
          <p className="eyebrow">Performance</p>
          <h1>Analytics</h1>
        </div>
      </div>

      <Row className="g-3 stat-grid analytics-grid">
        <Col xs={12} sm={6} lg={3}>
          <Card className="glass-card stat-card cyan"><Card.Body><div className="stat-label">Total detections</div><div className="stat-value">{analytics.totalDetections || '—'}</div></Card.Body></Card>
        </Col>
        <Col xs={12} sm={6} lg={3}>
          <Card className="glass-card stat-card green"><Card.Body><div className="stat-label">Unique plates</div><div className="stat-value">{analytics.uniquePlates || '—'}</div></Card.Body></Card>
        </Col>
        <Col xs={12} sm={6} lg={3}>
          <Card className="glass-card stat-card amber"><Card.Body><div className="stat-label">Avg confidence</div><div className="stat-value">{formatConfidence(analytics.averageConfidence || 0.948)}</div></Card.Body></Card>
        </Col>
        <Col xs={12} sm={6} lg={3}>
          <Card className="glass-card stat-card violet"><Card.Body><div className="stat-label">Highest confidence</div><div className="stat-value">{formatConfidence(analytics.highestConfidence || 0.96)}</div></Card.Body></Card>
        </Col>
      </Row>

      <Row className="g-4 dashboard-grid mt-1">
        <Col lg={8}>
          <Card className="glass-card panel-card">
            <Card.Header><div className="panel-header"><h3>Detection distribution</h3></div></Card.Header>
            <Card.Body>
              <div className="bar-stack">
                {chartBars.map((bar) => (
                  <div key={bar.label} className="bar-group">
                    <span className="bar-fill" style={{ height: `${Math.max(12, bar.value * 15)}px` }} />
                    <small>{bar.label}</small>
                  </div>
                ))}
              </div>
            </Card.Body>
          </Card>
        </Col>

        <Col lg={4}>
          <Card className="glass-card panel-card">
            <Card.Header><div className="panel-header"><h3>Top detected plates</h3></div></Card.Header>
            <Card.Body className="rank-list">
              {topPlates.length === 0 ? (
                <div className="empty-inline">No plate data available</div>
              ) : (
                topPlates.map((plate, index) => (
                  <div key={plate.name} className="rank-item">
                    <span className="rank-index">#{index + 1}</span>
                    <div className="rank-meta">
                      <strong>{plate.name}</strong>
                      <span>{plate.count} detections</span>
                    </div>
                  </div>
                ))
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </>
  );

  const renderSettings = () => (
    <>
      <div className="page-header compact-header">
        <div>
          <p className="eyebrow">System controls</p>
          <h1>Configuration</h1>
        </div>
      </div>

      <div className="settings-grid">
        <ConfigurationSidebar config={config} onConfigChange={updateConfig} />

        <Card className="glass-card panel-card status-card">
          <Card.Header>
            <div className="panel-header"><h3>System status</h3></div>
          </Card.Header>
          <Card.Body>
            <div className="status-list">
              <div className="status-row"><span>Application version</span><strong>v1.0.0</strong></div>
              <div className="status-row"><span>Auth session</span><strong>{user ? 'Active' : 'Inactive'}</strong></div>
              <div className="status-row"><span>Detection config</span><strong>{config ? 'Loaded' : 'Not loaded'}</strong></div>
              <div className="status-row"><span>OCR engine</span><strong>{config.primary_ocr || 'EasyOCR'}</strong></div>
            </div>
          </Card.Body>
        </Card>
      </div>
    </>
  );

  const renderContent = () => {
    switch (activeView) {
      case 'live':
        return renderLive();
      case 'upload':
        return renderUpload();
      case 'history':
        return renderHistory();
      case 'analytics':
        return renderAnalytics();
      case 'settings':
        return renderSettings();
      case 'overview':
      default:
        return renderOverview();
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="brand-block">
            <div className="brand-mark small">NPD</div>
            <div>
              <strong>Night Plate</strong>
              <small>Detection</small>
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`nav-item ${activeView === item.key ? 'active' : ''}`}
              onClick={() => handleNavSelect(item.key)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button type="button" className="logout-button" onClick={logout}>Logout</button>
        </div>
      </aside>

      <div className="main-panel">
        <header className="topbar">
          <div className="topbar-search">
            <span className="search-icon">⌕</span>
            <input type="text" placeholder="Search detections" aria-label="Search detections" />
          </div>

          <div className="topbar-actions">
            <button type="button" className="icon-button">◌</button>
            <div className="notification-block">
              <button type="button" className="icon-button">◍</button>
              <span className="notification-badge">{notifications.length}</span>
            </div>
            <div className="user-chip">
              <div className="user-avatar">{user?.username?.[0]?.toUpperCase() || 'U'}</div>
              <div>
                <strong>{user?.username || 'Operator'}</strong>
                <small>{user?.email || 'admin@system'}</small>
              </div>
            </div>
          </div>
        </header>

        <main className="content-area">
          {user?.isDemo && (
            <Alert variant="info">
              Demo mode: dashboard figures and detections are sample data. Live camera and video processing require the Flask backend.
            </Alert>
          )}
          {renderContent()}
        </main>
      </div>
    </div>
  );
};

export default Dashboard;
