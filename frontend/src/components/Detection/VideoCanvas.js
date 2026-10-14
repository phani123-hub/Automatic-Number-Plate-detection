import './DetectionOverlay.css';
import './VideoCanvas.css';
import React from 'react';

const VideoCanvas = ({ videoRef, detections = [], width, height }) => {
  const canvasRef = React.useRef();

  React.useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, width, height);
    detections.forEach(det => {
      const color = det.is_valid ? '#00FF00' : '#FFFF00';
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(det.box[0], det.box[1], det.box[2] - det.box[0], det.box[3] - det.box[1]);
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
      ctx.fillRect(det.box[0], det.box[1] - 25, 150, 25);
      ctx.fillStyle = color;
      ctx.font = 'bold 12px Arial';
      ctx.fillText(`ID:${det.track_id} Conf:${(det.confidence*100).toFixed(0)}%`, det.box[0] + 5, det.box[1] - 8);
    });
  }, [detections, width, height]);

  return (
    <canvas ref={canvasRef} width={width} height={height} className="video-canvas" />
  );
};

export default VideoCanvas;