module.exports = function override(config, env) {
  // Fix webpack-dev-server v5 compatibility
  if (config.devServer) {
    config.devServer.setupMiddlewares = undefined;
    config.devServer.onBeforeSetupMiddleware = undefined;
    config.devServer.onAfterSetupMiddleware = undefined;
  }
  
  return config;
};
