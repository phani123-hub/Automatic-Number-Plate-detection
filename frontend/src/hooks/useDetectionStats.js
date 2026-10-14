import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * useDetectionStats Hook
 * Tracks real-time statistics during detection sessions
 * Calculates FPS, processing time, and detection metrics
 */

export const useDetectionStats = () => {
  // Main statistics state
  const [stats, setStats] = useState({
    frameCount: 0,
    detectionCount: 0,
    fps: 0,
    uniqueVehicles: 0,
    avgConfidence: 0,
    processingTime: 0,
    sessionDuration: 0,
  });

  // Internal state for calculations
  const [startTime] = useState(Date.now());
  const [totalConfidence, setTotalConfidence] = useState(0);
  const sessionIntervalRef = useRef(null);

  /**
   * Update frame count and calculate FPS
   */
  const updateFrameCount = useCallback(() => {
    setStats(prevStats => {
      const newFrameCount = prevStats.frameCount + 1;

      // Calculate session duration
      const sessionDuration = Math.floor((Date.now() - startTime) / 1000);

      return {
        ...prevStats,
        frameCount: newFrameCount,
        sessionDuration,
      };
    });
  }, [startTime]);

  /**
   * Add detection to statistics
   * @param {number} confidence - Confidence score (0-1)
   * @param {boolean} isValid - Whether plate is valid
   */
  const addDetection = useCallback((confidence = 0.8, isValid = true) => {
    setStats(prevStats => {
      const newDetectionCount = prevStats.detectionCount + 1;
      const newTotalConfidence = totalConfidence + confidence;
      const newAvgConfidence = newTotalConfidence / newDetectionCount;

      setTotalConfidence(newTotalConfidence);

      return {
        ...prevStats,
        detectionCount: newDetectionCount,
        avgConfidence: newAvgConfidence,
        uniqueVehicles: prevStats.uniqueVehicles + (isValid ? 1 : 0),
      };
    });
  }, [totalConfidence]);

  /**
   * Update processing time (in milliseconds)
   * @param {number} time - Processing time in ms
   */
  const setProcessingTime = useCallback((time) => {
    setStats(prevStats => ({
      ...prevStats,
      processingTime: time,
    }));
  }, []);

  /**
   * Update FPS directly
   * @param {number} fps - FPS value
   */
  const setFPS = useCallback((fps) => {
    setStats(prevStats => ({
      ...prevStats,
      fps: parseFloat(fps.toFixed(1)),
    }));
  }, []);

  /**
   * Update detection count
   * @param {number} count - Detection count
   */
  const setDetectionCount = useCallback((count) => {
    setStats(prevStats => ({
      ...prevStats,
      detectionCount: count,
    }));
  }, []);

  /**
   * Update unique vehicles count
   * @param {number} count - Unique vehicles count
   */
  const setUniqueVehicles = useCallback((count) => {
    setStats(prevStats => ({
      ...prevStats,
      uniqueVehicles: count,
    }));
  }, []);

  /**
   * Update average confidence
   * @param {number} confidence - Average confidence (0-1)
   */
  const setAvgConfidence = useCallback((confidence) => {
    setStats(prevStats => ({
      ...prevStats,
      avgConfidence: parseFloat((confidence * 100).toFixed(2)) / 100,
    }));
  }, []);

  /**
   * Reset all statistics
   */
  const resetStats = useCallback(() => {
    setStats({
      frameCount: 0,
      detectionCount: 0,
      fps: 0,
      uniqueVehicles: 0,
      avgConfidence: 0,
      processingTime: 0,
      sessionDuration: 0,
    });
    setTotalConfidence(0);
  }, []);

  /**
   * Get formatted stats for display
   * @returns {Object} Formatted statistics
   */
  const getFormattedStats = useCallback(() => {
    return {
      frameCount: stats.frameCount.toLocaleString(),
      detectionCount: stats.detectionCount.toLocaleString(),
      fps: stats.fps.toFixed(1),
      uniqueVehicles: stats.uniqueVehicles.toLocaleString(),
      avgConfidence: (stats.avgConfidence * 100).toFixed(2) + '%',
      processingTime: stats.processingTime.toFixed(2) + 'ms',
      sessionDuration: formatSessionDuration(stats.sessionDuration),
    };
  }, [stats]);

  /**
   * Format session duration as HH:MM:SS
   * @param {number} seconds - Total seconds
   * @returns {string} Formatted time string
   */
  const formatSessionDuration = (seconds) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  /**
   * Start session timer (optional auto-update)
   */
  const startSessionTimer = useCallback(() => {
    sessionIntervalRef.current = setInterval(() => {
      setStats(prevStats => ({
        ...prevStats,
        sessionDuration: Math.floor((Date.now() - startTime) / 1000),
      }));
    }, 1000);
  }, [startTime]);

  /**
   * Stop session timer
   */
  const stopSessionTimer = useCallback(() => {
    if (sessionIntervalRef.current) {
      clearInterval(sessionIntervalRef.current);
    }
  }, []);

  /**
   * Get efficiency score (0-100)
   * @returns {number} Efficiency score
   */
  const getEfficiencyScore = useCallback(() => {
    if (stats.frameCount === 0) return 0;
    
    const detectionRate = (stats.detectionCount / stats.frameCount) * 100;
    const validRate = stats.uniqueVehicles > 0 
      ? (stats.uniqueVehicles / stats.detectionCount) * 100 
      : 0;
    const confidenceScore = stats.avgConfidence * 100;
    
    return Math.round((detectionRate + validRate + confidenceScore) / 3);
  }, [stats]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopSessionTimer();
    };
  }, [stopSessionTimer]);

  return {
    // State
    stats,

    // Methods
    updateFrameCount,
    addDetection,
    setProcessingTime,
    setFPS,
    setDetectionCount,
    setUniqueVehicles,
    setAvgConfidence,
    resetStats,
    getFormattedStats,
    startSessionTimer,
    stopSessionTimer,
    getEfficiencyScore,

    // Internal methods
    formatSessionDuration,
  };
};

export default useDetectionStats;
