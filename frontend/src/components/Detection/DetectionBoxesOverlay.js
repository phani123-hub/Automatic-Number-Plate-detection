import './DetectionOverlay.css';

export const DetectionBoxesOverlay = ({ detections, width, height }) => (
  <svg className="detection-overlay" width={width} height={height}>
    {detections.map((det, i) => {
      const color = det.is_valid ? '#00FF00' : '#FFFF00';
      return (
        <g key={i}>
          {/* Bounding Box */}
          <rect x={det.box[0]} y={det.box[1]} width={det.box[2]-det.box[0]} height={det.box[3]-det.box[1]}
                stroke={color} strokeWidth={2} fill="none" />
          {/* Label background */}
          <rect x={det.box[0]} y={det.box[1]-20} width={150} height={20} fill="rgba(0,0,0,0.5)"/>
          {/* Text labels */}
          <text x={det.box[0]+5} y={det.box[1]-5} fill={color} fontSize="12px">
            {`ID: ${det.track_id} Conf: ${(det.confidence*100).toFixed(1)}%`}
          </text>
        </g>
      );
    })}
  </svg>
);

export default DetectionBoxesOverlay;