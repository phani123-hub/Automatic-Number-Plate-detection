import api from './axios';

export const detectionAPI = {
  startSession: (sessionId) =>
    api.post('/detection/start-session', {
      session_id: sessionId,
    }),

  processFrame: (frameBase64, config, sessionId) =>
    api.post('/detection/process-frame', {
      frame_base64: frameBase64,
      config,
      session_id: sessionId,
    }),

  processVideo: (videoFile, config, sessionId) => {
    const formData = new FormData();
    formData.append('video', videoFile);
    formData.append('config', JSON.stringify(config));
    formData.append('session_id', sessionId);

    return api.post('/detection/process-video', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  getHistory: (limit = 50, skip = 0) =>
    api.get(`/detection/history?limit=${limit}&skip=${skip}`),

  getSessionDetections: (sessionId) =>
    api.get(`/detection/session/${sessionId}`),

  getPreviewDetections: (sessionId) =>
    api.get(`/detection/preview/${sessionId}`),

  confirmDetections: (sessionId, trackIds) =>
    api.post('/detection/confirm-detections', {
      session_id: sessionId,
      track_ids: trackIds,
    }),

  getManualReviewCrops: (sessionId) =>
    api.get(`/detection/manual-review/${sessionId}`),

  confirmManualReview: (sessionId, crops) =>
    api.post('/detection/confirm-manual-review', {
      session_id: sessionId,
      crops: crops,
    }),

  getStatistics: () =>
    api.get('/detection/statistics'),

  getDetection: (detectionId) =>
    api.get(`/detection/${detectionId}`),

  deleteDetection: (detectionId) =>
    api.delete(`/detection/${detectionId}`),
};

export default detectionAPI;
