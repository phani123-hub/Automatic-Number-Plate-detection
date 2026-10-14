import { Button } from 'react-bootstrap';
import { useState, useEffect } from 'react';
import './SessionControls.css';
const SessionControls = ({ onStart, onStop, onPause, onReset, isRunning, isPaused }) => {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    let timer;
    if (isRunning && !isPaused) {
      timer = setInterval(() => setElapsed(t => t+1), 1000);
    }
    return () => clearInterval(timer);
  }, [isRunning, isPaused]);
  const formatTime = (sec) => {
    const h = String(Math.floor(sec / 3600)).padStart(2, '0');
    const m = String(Math.floor((sec%3600)/60)).padStart(2, '0');
    const s = String(sec%60).padStart(2, '0');
    return `${h}:${m}:${s}`;
  };
  return (
    <div className="session-controls p-2 mb-3 border rounded bg-light">
      <h6>⏱️ {formatTime(elapsed)}</h6>
      <Button variant="success" disabled={isRunning} onClick={onStart} className="m-1">▶ Start</Button>
      <Button variant={isPaused ? 'primary' : 'warning'} disabled={!isRunning} onClick={onPause} className="m-1">{isPaused ? '▶ Resume' : '⏸ Pause'}</Button>
      <Button variant="danger" disabled={!isRunning} onClick={onStop} className="m-1">⏹ Stop</Button>
      <Button variant="secondary" onClick={onReset} className="m-1">🔄 Reset</Button>
    </div>
  );
};
export default SessionControls;