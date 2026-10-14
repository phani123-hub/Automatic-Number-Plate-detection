import { createContext, useState, useCallback } from 'react';

/**
 * ConfigContext
 * Global configuration state management for detection settings
 * Persists configuration in localStorage
 * Provides config to all components via Context API
 */

export const ConfigContext = createContext();

// Default configuration values
const DEFAULT_CONFIG = {
  // Input Source
  input_source: 'webcam',
  video_path: '',
  rtsp_url: '',
  
  // Model Settings
  model_path: 'models/yolov9c.pt',
  
  // Detection Parameters
  conf_threshold: 0.15,
  iou_threshold: 0.45,
  
  // Device Selection
  device: 'cpu',
  
  // Preprocessing
  enable_preprocessing: true,
  enable_clahe: true,
  clip_limit: 2.0,
  enable_denoise: true,
  enable_exposure: true,
  
  // OCR Settings
  primary_ocr: 'easyocr',
  ocr_threshold: 0.6,
};

/**
 * ConfigProvider Component
 * Wraps application to provide configuration context
 * Persists settings to localStorage
 */
export const ConfigProvider = ({ children }) => {
  const [config, setConfig] = useState(() => {
    // Try to load config from localStorage
    try {
      const saved = localStorage.getItem('detectionConfig');
      return saved ? JSON.parse(saved) : DEFAULT_CONFIG;
    } catch (err) {
      console.error('Error loading config from localStorage:', err);
      return DEFAULT_CONFIG;
    }
  });

  const [isLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Update configuration
   * @param {Object} newConfig - Partial or full configuration object
   */
  const updateConfig = useCallback((newConfig) => {
    try {
      setConfig(prevConfig => {
        const updated = { ...prevConfig, ...newConfig };
        // Persist to localStorage
        localStorage.setItem('detectionConfig', JSON.stringify(updated));
        return updated;
      });
      setError(null);
    } catch (err) {
      console.error('Error updating config:', err);
      setError(err.message);
    }
  }, []);

  /**
   * Update single config value
   * @param {string} key - Configuration key
   * @param {any} value - Configuration value
   */
  const updateConfigValue = useCallback((key, value) => {
    updateConfig({ [key]: value });
  }, [updateConfig]);

  /**
   * Reset configuration to defaults
   */
  const resetConfig = useCallback(() => {
    try {
      setConfig(DEFAULT_CONFIG);
      localStorage.removeItem('detectionConfig');
      setError(null);
    } catch (err) {
      console.error('Error resetting config:', err);
      setError(err.message);
    }
  }, []);

  /**
   * Get specific config value
   * @param {string} key - Configuration key
   * @param {any} defaultValue - Default value if key not found
   * @returns {any} Configuration value
   */
  const getConfigValue = useCallback((key, defaultValue = null) => {
    return config[key] !== undefined ? config[key] : defaultValue;
  }, [config]);

  /**
   * Validate configuration
   * @returns {Object} Validation result { isValid: boolean, errors: [] }
   */
  const validateConfig = useCallback(() => {
    const errors = [];

    if (config.conf_threshold < 0 || config.conf_threshold > 1) {
      errors.push('Confidence threshold must be between 0 and 1');
    }

    if (config.iou_threshold < 0 || config.iou_threshold > 1) {
      errors.push('IoU threshold must be between 0 and 1');
    }

    if (config.clip_limit < 1 || config.clip_limit > 5) {
      errors.push('CLAHE clip limit must be between 1 and 5');
    }

    if (config.ocr_threshold < 0 || config.ocr_threshold > 1) {
      errors.push('OCR threshold must be between 0 and 1');
    }

    if (config.device !== 'cpu' && config.device !== 'cuda') {
      errors.push('Device must be either "cpu" or "cuda"');
    }

    return {
      isValid: errors.length === 0,
      errors,
    };
  }, [config]);

  /**
   * Export configuration as JSON
   * @returns {string} JSON string of configuration
   */
  const exportConfig = useCallback(() => {
    return JSON.stringify(config, null, 2);
  }, [config]);

  /**
   * Import configuration from JSON
   * @param {string} jsonString - JSON string of configuration
   */
  const importConfig = useCallback((jsonString) => {
    try {
      const importedConfig = JSON.parse(jsonString);
      const validation = validateConfig();
      if (!validation.isValid) {
        throw new Error(validation.errors.join(', '));
      }
      updateConfig(importedConfig);
      setError(null);
      return true;
    } catch (err) {
      console.error('Error importing config:', err);
      setError(err.message);
      return false;
    }
  }, [updateConfig, validateConfig]);

  // Context value
  const value = {
    // State
    config,
    isLoading,
    error,

    // Methods
    updateConfig,
    updateConfigValue,
    resetConfig,
    getConfigValue,
    validateConfig,
    exportConfig,
    importConfig,

    // Constants
    DEFAULT_CONFIG,
  };

  return (
    <ConfigContext.Provider value={value}>
      {children}
    </ConfigContext.Provider>
  );
};

export default ConfigContext;
