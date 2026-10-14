const minutesAgo = (minutes) => {
  const detectedAt = new Date(Date.now() - minutes * 60 * 1000);

  return {
    detected_at: detectedAt.toLocaleString(),
    date: detectedAt.toLocaleDateString(),
    time: detectedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  };
};

const demoRecords = [
  ['KA03MN4821', 0.98, 4, 'North Gate'],
  ['MH12AB9090', 0.96, 16, 'East Entrance'],
  ['KA03MN4821', 0.94, 29, 'North Gate'],
  ['DL8CAF2204', 0.93, 48, 'Parking Lot'],
  ['TN09CD7712', 0.91, 73, 'South Gate'],
  ['MH12AB9090', 0.89, 105, 'East Entrance'],
  ['KA51PQ6382', 0.97, 142, 'North Gate'],
  ['TS07EF1145', 0.92, 188, 'Service Road'],
  ['DL8CAF2204', 0.88, 236, 'Parking Lot'],
  ['GJ01LK5533', 0.95, 301, 'West Entrance'],
  ['TN09CD7712', 0.9, 374, 'South Gate'],
  ['AP39GH2860', 0.87, 452, 'Service Road'],
];

export const DEMO_DETECTIONS = demoRecords.map(([plate_number, confidence, minutes, source], index) => ({
  _id: `demo-detection-${index + 1}`,
  plate_number,
  confidence,
  is_valid: confidence >= 0.9,
  source,
  ...minutesAgo(minutes),
}));
