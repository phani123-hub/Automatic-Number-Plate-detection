export const colorFromValidity = (isValid) => (isValid ? '#00FF00' :'#FFFF00');

export const formatConfidence = (conf) => `${(conf*100).toFixed(1)}%`;

export const drawBoundingBox = (ctx, box, confidence, track_id, is_valid) => {
  ctx.strokeStyle = colorFromValidity(is_valid);
  ctx.lineWidth = 2;
  ctx.strokeRect(box[0], box[1], box[2]-box[0], box[3]-box[1]);
  ctx.fillStyle = 'rgba(0,0,0,0.5)';
  ctx.fillRect(box[0], box[1]-20, 150, 20);
  ctx.fillStyle = ctx.strokeStyle;
  ctx.font = 'bold 12px Arial';
  ctx.fillText(`ID:${track_id} (${formatConfidence(confidence)})`, box[0]+5, box[1]-5);
};

export const drawAllDetections = (ctx, detections, width, height) => {
  detections.forEach(det => drawBoundingBox(ctx, det.box, det.confidence, det.track_id, det.is_valid));
};