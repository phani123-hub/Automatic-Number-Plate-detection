import { useState, useEffect, useContext } from 'react';
import { Card, Table, Form, Button, Badge, Pagination, Alert } from 'react-bootstrap';
import { AuthContext } from '../../context/AuthContext';
import { detectionAPI } from '../../api/detection';
import DetectionModal from '../Detection/DetectionModal';
import './LogsViewer.css';

/**
 * LogsViewer Component
 * Displays detection history with deduplication and modal view
 */
const LogsViewer = () => {
  const { user } = useContext(AuthContext);

  // Logs state
  const [logs, setLogs] = useState([]);
  const [filteredLogs, setFilteredLogs] = useState([]);
  const [uniqueLogs, setUniqueLogs] = useState([]);
  
  // Pagination and filtering
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchText, setSearchText] = useState('');
  const [showAll, setShowAll] = useState(false);
  
  // Modal state - THIS WAS MISSING!
  const [showModal, setShowModal] = useState(false);
  const [selectedDetection, setSelectedDetection] = useState(null);
  
  // Loading and error state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  /**
   * Fetch logs on component mount
   */
  useEffect(() => {
    fetchLogs();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  /**
   * Fetch detection logs from API
   */
  const fetchLogs = async () => {
    if (!user?._id && !user?.id) {
      setError('User not authenticated. Please login.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const userId = user._id || user.id;
      const response = await detectionAPI.getHistory(100);

      // Filter by current user
      const userDetections = response.data.detections.filter(
        det => det.user_id === userId || det.username === user.username
      );

      setLogs(userDetections);

      // Remove duplicates - keep best result per plate
      const uniqueByPlate = deduplicateByPlate(userDetections);
      setUniqueLogs(uniqueByPlate);
      setFilteredLogs(uniqueByPlate);
    } catch (err) {
      console.error('Error fetching logs:', err);
      setError('Failed to fetch detection logs. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Remove duplicate detections - keep highest confidence per plate
   */
  const deduplicateByPlate = (detections) => {
    const plateMap = {};

    detections.forEach(detection => {
      const plateText = detection.plate_text || detection.text || 'Unknown';
      const confidence = parseFloat(detection.confidence_score) || 0;

      if (!plateMap[plateText]) {
        plateMap[plateText] = detection;
      } else {
        const existingConf = parseFloat(plateMap[plateText].confidence_score) || 0;
        if (confidence > existingConf) {
          plateMap[plateText] = detection;
        }
      }
    });

    return Object.values(plateMap);
  };

  /**
   * Handle search by plate text
   */
  const handleSearch = (e) => {
    const text = e.target.value.toLowerCase();
    setSearchText(text);
    setCurrentPage(1);

    const source = showAll ? logs : uniqueLogs;
    const filtered = source.filter(log =>
      log.plate_text?.toLowerCase().includes(text) ||
      log.text?.toLowerCase().includes(text)
    );
    setFilteredLogs(filtered);
  };

  /**
   * Toggle between unique and all detections view
   */
  const handleToggleView = () => {
    setShowAll(!showAll);
    setCurrentPage(1);

    const source = !showAll ? logs : uniqueLogs;
    setFilteredLogs(source);
    setSearchText('');
  };

  /**
   * Handle View button click - OPENS MODAL WITH DETECTION
   */
  const handleViewDetection = (detection) => {
    setSelectedDetection(detection);
    setShowModal(true);
  };

  /**
   * Handle modal close
   */
  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedDetection(null);
  };

  /**
   * Export logs as CSV
   */
  const handleExport = () => {
    const csv = [
      ['Timestamp', 'Plate Text', 'Confidence', 'Valid', 'Count (if duplicates)'],
      ...filteredLogs.map(log => [
        new Date(log.timestamp).toLocaleString(),
        log.plate_text || log.text || '-',
        ((parseFloat(log.confidence_score) || 0) * 100).toFixed(2) + '%',
        (log.is_valid_indian || log.is_valid) ? 'Yes' : 'No',
        showAll ? '-' : '1 (best result)'
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `detections_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  // Calculate pagination
  const startIdx = (currentPage - 1) * pageSize;
  const endIdx = startIdx + pageSize;
  const paginatedLogs = filteredLogs.slice(startIdx, endIdx);
  const totalPages = Math.ceil(filteredLogs.length / pageSize);
  const totalDuplicates = logs.length - uniqueLogs.length;

  // Loading state
  if (loading) {
    return (
      <Card className="logs-viewer shadow-sm">
        <Card.Body className="text-center py-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="text-muted mt-3">Loading detection logs...</p>
        </Card.Body>
      </Card>
    );
  }

  return (
    <>
      <Card className="logs-viewer shadow-sm">
        <Card.Header className="bg-dark text-white d-flex justify-content-between align-items-center">
          <h5 className="mb-0">📋 Detection Logs</h5>
          <Badge bg="info">{filteredLogs.length} entries</Badge>
        </Card.Header>
        <Card.Body>
          {/* Error Message */}
          {error && <Alert variant="danger" className="mb-3">{error}</Alert>}

          {/* Statistics */}
          {!showAll && totalDuplicates > 0 && (
            <Alert variant="info" className="mb-3">
              📊 Showing <strong>{uniqueLogs.length}</strong> unique vehicles
              (Removed <strong>{totalDuplicates}</strong> duplicate detections)
            </Alert>
          )}

          {/* Controls */}
          <div className="mb-3">
            <div className="row">
              <div className="col-md-6">
                <Form.Control
                  type="text"
                  placeholder="Search by plate text..."
                  value={searchText}
                  onChange={handleSearch}
                />
              </div>
              <div className="col-md-3">
                <Form.Select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(parseInt(e.target.value));
                    setCurrentPage(1);
                  }}
                >
                  <option value="10">10 per page</option>
                  <option value="20">20 per page</option>
                  <option value="50">50 per page</option>
                </Form.Select>
              </div>
              <div className="col-md-3">
                <Button
                  variant={showAll ? 'danger' : 'info'}
                  size="sm"
                  onClick={handleToggleView}
                  className="w-100"
                >
                  {showAll ? '🔄 Unique Only' : '📊 Show All'}
                </Button>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="mt-2 d-flex gap-2">
              <Button variant="success" size="sm" onClick={() => fetchLogs()}>
                🔄 Refresh
              </Button>
              <Button variant="warning" size="sm" onClick={handleExport}>
                ⬇️ Export CSV
              </Button>
            </div>
          </div>

          {/* Logs Table */}
          <div className="table-responsive">
            <Table hover striped>
              <thead className="table-dark">
                <tr>
                  <th>Timestamp</th>
                  <th>Plate Text</th>
                  <th>Confidence</th>
                  <th>Valid</th>
                  {showAll && <th>Track ID</th>}
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {paginatedLogs.length > 0 ? (
                  paginatedLogs.map((log, idx) => (
                    <tr key={`${log._id}-${idx}`}>
                      <td className="text-nowrap">
                        <span style={{ 
                          backgroundColor: '#f8f9fa', 
                          padding: '4px 8px', 
                          borderRadius: '4px',
                          color: '#000',
                          fontWeight: '500',
                          display: 'inline-block'
                        }}>
                          {new Date(log.timestamp).toLocaleString()}
                        </span>
                      </td>
                      <td>
                        <Badge bg="primary">
                          {log.plate_text || log.text || 'Unknown'}
                        </Badge>
                      </td>
                      <td>
                        <div className="progress" style={{ height: '24px' }}>
                          <div
                            className="progress-bar bg-success"
                            style={{
                              width: `${Math.min(
                                (parseFloat(log.confidence_score) || 0) * 100,
                                100
                              )}%`,
                            }}
                          >
                            {((parseFloat(log.confidence_score) || 0) * 100).toFixed(1)}%
                          </div>
                        </div>
                      </td>
                      <td>
                        {log.is_valid_indian || log.is_valid ? (
                          <Badge bg="success">✓ Yes</Badge>
                        ) : (
                          <Badge bg="warning">✗ No</Badge>
                        )}
                      </td>
                      {showAll && (
                        <td>
                          <small>{log.track_id || 'N/A'}</small>
                        </td>
                      )}
                      <td>
                        {/* THIS WAS BROKEN - NOW FIXED! */}
                        <Button
                          variant="outline-primary"
                          size="sm"
                          onClick={() => handleViewDetection(log)}
                        >
                          View
                        </Button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={showAll ? 6 : 5} className="text-center text-muted py-4">
                      No detections found
                    </td>
                  </tr>
                )}
              </tbody>
            </Table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <Pagination className="justify-content-center mt-3">
              <Pagination.First
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
              />
              <Pagination.Prev
                onClick={() => setCurrentPage(currentPage - 1)}
                disabled={currentPage === 1}
              />
              {[...Array(Math.min(5, totalPages))].map((_, i) => (
                <Pagination.Item
                  key={i + 1}
                  active={currentPage === i + 1}
                  onClick={() => setCurrentPage(i + 1)}
                >
                  {i + 1}
                </Pagination.Item>
              ))}
              <Pagination.Next
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={currentPage === totalPages}
              />
              <Pagination.Last
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
              />
            </Pagination>
          )}

          {/* Summary */}
          <div className="mt-3 pt-3 border-top">
            <small className="text-muted">
              Showing {startIdx + 1}-{Math.min(endIdx, filteredLogs.length)} of{' '}
              {filteredLogs.length} entries
              {showAll && totalDuplicates > 0 && (
                <> | {totalDuplicates} duplicate detections hidden in unique view</>
              )}
            </small>
          </div>
        </Card.Body>
      </Card>

      {/* Detection Modal - THIS WAS MISSING! */}
      {selectedDetection && (
        <DetectionModal
          show={showModal}
          detection={selectedDetection}
          onHide={handleCloseModal}
        />
      )}
    </>
  );
};

export default LogsViewer;
