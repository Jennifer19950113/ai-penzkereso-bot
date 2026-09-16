const getTimestamp = () => {
  return new Date().toISOString();
};

const logger = {
  info: (message) => {
    const timestamp = getTimestamp();
    console.log(`[${timestamp}] [INFO] ${message}`);
  },
  error: (message, error = null) => {
    const timestamp = getTimestamp();
    const errorMsg = error ? ` - ${error.message}` : '';
    console.error(`[${timestamp}] [ERROR] ${message}${errorMsg}`);
  },
  warn: (message) => {
    const timestamp = getTimestamp();
    console.warn(`[${timestamp}] [WARN] ${message}`);
  }
};

module.exports = logger;
